from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, DeleteView, FormView, ListView, UpdateView

from .forms import CartQuantityForm, EquipmentForm, ImportExcelForm, RequestForm, SupplyForm
from .models import Equipment, Request, RequestItem, Supply, UserProfile
from .services.importers import import_equipment_excel, import_supply_excel

CART_SESSION_KEY = "request_cart"


# =========================
# MIXINS
# =========================

class AreaFilteredMixin:
    """Filtra automáticamente por el área académica del usuario."""

    def get_user_profile(self):
        return getattr(self.request.user, "profile", None)

    def get_user_area(self):
        profile = self.get_user_profile()
        return getattr(profile, "academic_area", None)

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user

        if user.is_superuser:
            return queryset

        area = self.get_user_area()
        return queryset.filter(academic_area=area) if area else queryset.none()


class RoleRequiredMixin(UserPassesTestMixin):
    allowed_roles = set()

    def test_func(self):
        user = self.request.user

        if user.is_superuser:
            return True

        profile = getattr(user, "profile", None)
        return bool(profile and profile.role in self.allowed_roles)


class StudentRequiredMixin(RoleRequiredMixin):
    allowed_roles = {UserProfile.Roles.STUDENT}


# =========================
# CART HELPERS
# =========================


def _empty_cart():
    return {"equipment": {}, "supply": {}}


def _get_cart(request):
    cart = request.session.get(CART_SESSION_KEY)
    if not isinstance(cart, dict):
        return _empty_cart()
    cart.setdefault("equipment", {})
    cart.setdefault("supply", {})
    return cart


def _save_cart(request, cart):
    request.session[CART_SESSION_KEY] = cart
    request.session.modified = True


def _get_user_area(user):
    profile = getattr(user, "profile", None)
    return getattr(profile, "academic_area", None)


def _resource_for_user(user, resource_type, resource_id):
    model = Equipment if resource_type == "equipment" else Supply
    queryset = model.objects.select_related("academic_area")

    if not user.is_superuser:
        area = _get_user_area(user)
        queryset = queryset.filter(academic_area=area) if area else queryset.none()

    return queryset.filter(pk=resource_id).first()


def _build_cart_context(user, cart):
    equipment_ids = [int(pk) for pk in cart.get("equipment", {}).keys()]
    supply_ids = [int(pk) for pk in cart.get("supply", {}).keys()]

    equipment_qs = Equipment.objects.filter(pk__in=equipment_ids)
    supply_qs = Supply.objects.filter(pk__in=supply_ids)

    if not user.is_superuser:
        area = _get_user_area(user)
        equipment_qs = equipment_qs.filter(academic_area=area) if area else Equipment.objects.none()
        supply_qs = supply_qs.filter(academic_area=area) if area else Supply.objects.none()

    equipment_map = {str(obj.pk): obj for obj in equipment_qs}
    supply_map = {str(obj.pk): obj for obj in supply_qs}

    lines = []

    for pk, row in cart.get("equipment", {}).items():
        equipment = equipment_map.get(pk)
        if not equipment:
            continue
        quantity = int(row.get("quantity", 1))
        lines.append({
            "resource_type": "equipment",
            "resource_id": equipment.pk,
            "resource_name": str(equipment),
            "quantity": quantity,
            "stock": None,
        })

    for pk, row in cart.get("supply", {}).items():
        supply = supply_map.get(pk)
        if not supply:
            continue
        quantity = int(row.get("quantity", 1))
        lines.append({
            "resource_type": "supply",
            "resource_id": supply.pk,
            "resource_name": supply.name,
            "quantity": quantity,
            "stock": supply.total_existing,
        })

    return {
        "lines": lines,
        "total_lines": len(lines),
        "total_quantity": sum(line["quantity"] for line in lines),
    }


# =========================
# BASE VIEWS
# =========================

class BaseInventoryView(LoginRequiredMixin, RoleRequiredMixin, AreaFilteredMixin):
    template_name = "inventory/form.html"
    allowed_roles = {UserProfile.Roles.COORDINATOR, UserProfile.Roles.PANOL}

    def get_success_url(self):
        return reverse(f"inventory:{self.model._meta.model_name}_list")


class BaseImportView(LoginRequiredMixin, RoleRequiredMixin, FormView):
    template_name = "inventory/import_form.html"
    form_class = ImportExcelForm
    allowed_roles = {UserProfile.Roles.COORDINATOR, UserProfile.Roles.PANOL}
    title = "Importar archivo"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = self.title
        return context

    def process_file(self, uploaded_file):
        raise NotImplementedError("Debes implementar process_file().")

    def form_valid(self, form):
        uploaded_file = form.cleaned_data["file"]

        try:
            self.process_file(uploaded_file)
        except ValidationError as exc:
            form.add_error("file", exc)
            messages.error(self.request, "No fue posible procesar el archivo.")
            return self.form_invalid(form)
        except Exception as exc:
            form.add_error("file", f"No fue posible procesar el archivo: {exc}")
            messages.error(self.request, "No fue posible procesar el archivo.")
            return self.form_invalid(form)

        messages.success(self.request, "Archivo procesado correctamente.")
        return redirect(self.get_success_url())


# =========================
# EQUIPOS
# =========================

class EquipmentListView(LoginRequiredMixin, AreaFilteredMixin, ListView):
    model = Equipment
    template_name = "inventory/equipment_list.html"
    context_object_name = "equipments"
    paginate_by = 20

    def get_queryset(self):
        queryset = (
            super()
            .get_queryset()
            .select_related("storage_location", "academic_area")
            .prefetch_related("careers", "subjects")
        )

        q = self.request.GET.get("q", "").strip()
        if q:
            queryset = queryset.filter(
                Q(name__icontains=q)
                | Q(inventory_code__icontains=q)
                | Q(detailed_spec__icontains=q)
            )

        return queryset


class EquipmentCreateView(BaseInventoryView, CreateView):
    model = Equipment
    form_class = EquipmentForm


class EquipmentUpdateView(BaseInventoryView, UpdateView):
    model = Equipment
    form_class = EquipmentForm


class EquipmentDeleteView(BaseInventoryView, DeleteView):
    model = Equipment
    template_name = "inventory/confirm_delete.html"


class EquipmentImportView(BaseImportView):
    title = "Importar equipos"
    success_url = reverse_lazy("inventory:equipment_list")

    def process_file(self, uploaded_file):
        import_equipment_excel(uploaded_file)


# =========================
# INSUMOS
# =========================

class SupplyListView(LoginRequiredMixin, AreaFilteredMixin, ListView):
    model = Supply
    template_name = "inventory/supply_list.html"
    context_object_name = "supplies"
    paginate_by = 20

    def get_queryset(self):
        queryset = (
            super()
            .get_queryset()
            .select_related("storage_location", "academic_area")
        )

        q = self.request.GET.get("q", "").strip()
        if q:
            queryset = queryset.filter(
                Q(name__icontains=q)
                | Q(detailed_spec__icontains=q)
            )

        return queryset


class SupplyCreateView(BaseInventoryView, CreateView):
    model = Supply
    form_class = SupplyForm


class SupplyUpdateView(BaseInventoryView, UpdateView):
    model = Supply
    form_class = SupplyForm


class SupplyDeleteView(BaseInventoryView, DeleteView):
    model = Supply
    template_name = "inventory/confirm_delete.html"


class SupplyImportView(BaseImportView):
    title = "Importar insumos"
    success_url = reverse_lazy("inventory:supply_list")

    def process_file(self, uploaded_file):
        import_supply_excel(uploaded_file)


# =========================
# SOLICITUDES
# =========================

class RequestListView(LoginRequiredMixin, ListView):
    model = Request
    template_name = "inventory/request_list.html"
    context_object_name = "requests"
    paginate_by = 20

    def get_queryset(self):
        user = self.request.user
        profile = getattr(user, "profile", None)

        queryset = (
            Request.objects
            .select_related("requester", "academic_area")
            .prefetch_related("items__equipment", "items__supply")
        )

        if user.is_superuser:
            return queryset

        if not profile:
            return queryset.none()

        if profile.role == UserProfile.Roles.STUDENT:
            return queryset.filter(requester=user)

        area = getattr(profile, "academic_area", None)
        return queryset.filter(academic_area=area) if area else queryset.none()


class RequestCreateView(LoginRequiredMixin, StudentRequiredMixin, FormView):
    form_class = RequestForm
    template_name = "inventory/request_form.html"
    success_url = reverse_lazy("inventory:request_list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cart_info = _build_cart_context(self.request.user, _get_cart(self.request))
        context.update(cart_info)
        return context

    def form_valid(self, form):
        user = self.request.user
        area = _get_user_area(user)
        cart = _get_cart(self.request)
        cart_info = _build_cart_context(user, cart)

        if area is None:
            messages.error(self.request, "Tu usuario no tiene un área académica asignada.")
            return self.form_invalid(form)

        if not cart_info["lines"]:
            messages.error(self.request, "Tu carrito está vacío. Agrega al menos un recurso.")
            return self.form_invalid(form)

        with transaction.atomic():
            new_request = Request.objects.create(
                requester=user,
                academic_area=area,
                reason=form.cleaned_data["reason"],
            )

            for line in cart_info["lines"]:
                kwargs = {
                    "request": new_request,
                    "quantity": line["quantity"],
                }
                if line["resource_type"] == "equipment":
                    kwargs["equipment_id"] = line["resource_id"]
                else:
                    kwargs["supply_id"] = line["resource_id"]
                RequestItem.objects.create(**kwargs)

        _save_cart(self.request, _empty_cart())
        messages.success(self.request, "Solicitud enviada correctamente.")
        return super().form_valid(form)


@login_required
def cart_add_item(request, resource_type, pk):
    if request.method != "POST":
        return HttpResponseRedirect(reverse("inventory:request_create"))

    profile = getattr(request.user, "profile", None)
    if not (request.user.is_superuser or (profile and profile.role == UserProfile.Roles.STUDENT)):
        messages.error(request, "No tienes permisos para agregar al carrito.")
        return HttpResponseRedirect(request.META.get("HTTP_REFERER", reverse("inventory:equipment_list")))

    if resource_type not in {"equipment", "supply"}:
        messages.error(request, "Tipo de recurso inválido.")
        return HttpResponseRedirect(request.META.get("HTTP_REFERER", reverse("inventory:equipment_list")))

    resource = _resource_for_user(request.user, resource_type, pk)
    if not resource:
        messages.error(request, "No puedes agregar un recurso fuera de tu área académica.")
        return HttpResponseRedirect(request.META.get("HTTP_REFERER", reverse("inventory:equipment_list")))

    cart = _get_cart(request)
    bucket = cart[resource_type]
    key = str(resource.pk)
    current_qty = int(bucket.get(key, {}).get("quantity", 0))
    new_qty = current_qty + 1

    if resource_type == "supply" and new_qty > resource.total_existing:
        messages.error(
            request,
            f"Stock insuficiente para '{resource.name}'. Disponible: {resource.total_existing}.",
        )
    else:
        bucket[key] = {"quantity": new_qty}
        _save_cart(request, cart)
        messages.success(request, f"'{resource}' agregado al carrito.")

    return HttpResponseRedirect(request.META.get("HTTP_REFERER", reverse("inventory:request_create")))


@login_required
def cart_update_item(request, resource_type, pk):
    if request.method != "POST":
        return redirect("inventory:request_create")

    profile = getattr(request.user, "profile", None)
    if not (request.user.is_superuser or (profile and profile.role == UserProfile.Roles.STUDENT)):
        messages.error(request, "No tienes permisos para modificar el carrito.")
        return redirect("inventory:request_create")

    form = CartQuantityForm(request.POST)
    if not form.is_valid():
        messages.error(request, "La cantidad debe ser mayor a 0.")
        return redirect("inventory:request_create")

    resource = _resource_for_user(request.user, resource_type, pk)
    if not resource:
        messages.error(request, "No se encontró el recurso solicitado en tu área.")
        return redirect("inventory:request_create")

    quantity = form.cleaned_data["quantity"]
    if resource_type == "supply" and quantity > resource.total_existing:
        messages.error(
            request,
            f"Stock insuficiente para '{resource.name}'. Disponible: {resource.total_existing}.",
        )
        return redirect("inventory:request_create")

    cart = _get_cart(request)
    if str(pk) not in cart.get(resource_type, {}):
        messages.error(request, "El recurso no está en el carrito.")
        return redirect("inventory:request_create")

    cart[resource_type][str(pk)]["quantity"] = quantity
    _save_cart(request, cart)
    messages.success(request, "Cantidad actualizada.")
    return redirect("inventory:request_create")


@login_required
def cart_remove_item(request, resource_type, pk):
    if request.method != "POST":
        return redirect("inventory:request_create")

    cart = _get_cart(request)
    cart.get(resource_type, {}).pop(str(pk), None)
    _save_cart(request, cart)
    messages.success(request, "Ítem eliminado del carrito.")
    return redirect("inventory:request_create")


# =========================
# API
# =========================

@login_required
def equipment_search_api(request):
    q = request.GET.get("q", "").strip()
    user = request.user
    profile = getattr(user, "profile", None)

    queryset = Equipment.objects.select_related("storage_location", "academic_area")

    if not user.is_superuser:
        area = getattr(profile, "academic_area", None)
        queryset = queryset.filter(academic_area=area) if area else queryset.none()

    if q:
        queryset = queryset.filter(Q(name__icontains=q) | Q(inventory_code__icontains=q))

    rows = queryset.order_by("name")[:20]

    results = [
        {
            "id": equipment.id,
            "name": equipment.name,
            "inventory_code": equipment.inventory_code,
            "storage_location": equipment.storage_location.name,
            "condition": equipment.get_condition_display(),
        }
        for equipment in rows
    ]

    return JsonResponse({"results": results})


@login_required
def supply_search_api(request):
    q = request.GET.get("q", "").strip()
    user = request.user
    profile = getattr(user, "profile", None)

    queryset = Supply.objects.select_related("storage_location", "academic_area")

    if not user.is_superuser:
        area = getattr(profile, "academic_area", None)
        queryset = queryset.filter(academic_area=area) if area else queryset.none()

    if q:
        queryset = queryset.filter(Q(name__icontains=q))

    rows = queryset.order_by("name")[:20]

    results = [
        {
            "id": supply.id,
            "name": supply.name,
            "storage_location": supply.storage_location.name,
            "total_existing": supply.total_existing,
        }
        for supply in rows
    ]

    return JsonResponse({"results": results})

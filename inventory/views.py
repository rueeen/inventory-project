from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, DeleteView, FormView, ListView, UpdateView

from .forms import EquipmentForm, ImportExcelForm, RequestForm, RequestItemFormSet, SupplyForm
from .models import Equipment, Request, Supply, UserProfile
from .services.importers import import_equipment_excel, import_supply_excel


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
            form.add_error(
                "file", f"No fue posible procesar el archivo: {exc}")
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


class RequestCreateView(LoginRequiredMixin, RoleRequiredMixin, CreateView):
    model = Request
    form_class = RequestForm
    template_name = "inventory/request_form.html"
    allowed_roles = {UserProfile.Roles.STUDENT}
    success_url = reverse_lazy("inventory:request_list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_item_formset(self, form=None):
        area = getattr(getattr(self.request.user, "profile",
                       None), "academic_area", None)
        instance = form.instance if form is not None else getattr(
            self, "object", None)

        if self.request.method == "POST":
            return RequestItemFormSet(self.request.POST, instance=instance, area=area)
        return RequestItemFormSet(instance=instance, area=area)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        if "item_formset" not in context:
            context["item_formset"] = self.get_item_formset(kwargs.get("form"))

        return context

    def form_valid(self, form):
        profile = getattr(self.request.user, "profile", None)
        area = getattr(profile, "academic_area", None)
        item_formset = self.get_item_formset(form)

        if area is None:
            form.add_error(
                None, "Tu usuario no tiene un área académica asignada.")
            messages.error(
                self.request, "Tu usuario no tiene un área académica asignada.")
            return self.render_to_response(self.get_context_data(form=form, item_formset=item_formset))

        if not item_formset.is_valid():
            messages.error(self.request, "Error en los ítems de la solicitud.")
            return self.render_to_response(self.get_context_data(form=form, item_formset=item_formset))

        with transaction.atomic():
            form.instance.requester = self.request.user
            form.instance.academic_area = area
            self.object = form.save()
            item_formset.instance = self.object
            item_formset.save()

        messages.success(self.request, "Solicitud registrada correctamente.")
        return redirect(self.get_success_url())

    def form_invalid(self, form):
        messages.error(
            self.request, "Por favor, corrige los errores del formulario.")
        return self.render_to_response(self.get_context_data(form=form, item_formset=self.get_item_formset(form)))


# =========================
# API
# =========================

@login_required
def equipment_search_api(request):
    q = request.GET.get("q", "").strip()
    user = request.user
    profile = getattr(user, "profile", None)

    queryset = Equipment.objects.select_related(
        "storage_location", "academic_area")

    if not user.is_superuser:
        area = getattr(profile, "academic_area", None)
        queryset = queryset.filter(
            academic_area=area) if area else queryset.none()

    if q:
        queryset = queryset.filter(
            Q(name__icontains=q) | Q(inventory_code__icontains=q)
        )

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

    queryset = Supply.objects.select_related(
        "storage_location", "academic_area")

    if not user.is_superuser:
        area = getattr(profile, "academic_area", None)
        queryset = queryset.filter(
            academic_area=area) if area else queryset.none()

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

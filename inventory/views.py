from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db import connection
from django.db.models import Q
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView

from .forms import EquipmentForm, SupplyForm, ImportExcelForm, RequestForm, RequestItemFormSet
from .models import Equipment, Supply, Request, UserProfile
from .services.importers import import_equipment_excel, import_supply_excel


class AreaFilteredMixin:
    def filter_by_area(self, queryset):
        user = self.request.user
        if user.is_superuser:
            return queryset
        profile = getattr(user, "profile", None)
        area = getattr(profile, "academic_area", None)
        if area is None:
            return queryset.none()
        return queryset.filter(academic_area=area)


class InventoryManagerRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        if self.request.user.is_superuser:
            return True
        profile = getattr(self.request.user, "profile", None)
        return profile and profile.role in {UserProfile.ROLE_COORDINATOR, UserProfile.ROLE_PANOL}


class StudentRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        if self.request.user.is_superuser:
            return True
        profile = getattr(self.request.user, "profile", None)
        return profile and profile.role == UserProfile.ROLE_STUDENT


class EquipmentListView(LoginRequiredMixin, AreaFilteredMixin, ListView):
    model = Equipment
    template_name = "inventory/equipment_list.html"
    context_object_name = "equipments"
    paginate_by = 20

    def get_queryset(self):
        queryset = Equipment.objects.select_related(
            "storage_location",
            "academic_area"
        ).prefetch_related(
            "careers",
            "subjects"
        )

        queryset = self.filter_by_area(queryset)

        q = self.request.GET.get("q")
        if q:
            queryset = queryset.filter(
                Q(name__icontains=q) | Q(inventory_code__icontains=q)
            )

        return queryset

class EquipmentCreateView(LoginRequiredMixin, InventoryManagerRequiredMixin, CreateView):
    model = Equipment
    form_class = EquipmentForm
    template_name = "inventory/form.html"
    success_url = reverse_lazy("inventory:equipment_list")


class EquipmentUpdateView(LoginRequiredMixin, InventoryManagerRequiredMixin, UpdateView):
    model = Equipment
    form_class = EquipmentForm
    template_name = "inventory/form.html"
    success_url = reverse_lazy("inventory:equipment_list")


class EquipmentDeleteView(LoginRequiredMixin, InventoryManagerRequiredMixin, DeleteView):
    model = Equipment
    template_name = "inventory/confirm_delete.html"
    success_url = reverse_lazy("inventory:equipment_list")


class SupplyListView(LoginRequiredMixin, AreaFilteredMixin, ListView):
    model = Supply
    template_name = "inventory/supply_list.html"
    context_object_name = "supplies"
    paginate_by = 20

    def get_queryset(self):
        queryset = Supply.objects.select_related("storage_location", "academic_area")
        queryset = self.filter_by_area(queryset)
        q = self.request.GET.get("q")
        if q:
            queryset = queryset.filter(name__icontains=q)
        return queryset


class SupplyCreateView(LoginRequiredMixin, InventoryManagerRequiredMixin, CreateView):
    model = Supply
    form_class = SupplyForm
    template_name = "inventory/form.html"
    success_url = reverse_lazy("inventory:supply_list")


class SupplyUpdateView(LoginRequiredMixin, InventoryManagerRequiredMixin, UpdateView):
    model = Supply
    form_class = SupplyForm
    template_name = "inventory/form.html"
    success_url = reverse_lazy("inventory:supply_list")


class SupplyDeleteView(LoginRequiredMixin, InventoryManagerRequiredMixin, DeleteView):
    model = Supply
    template_name = "inventory/confirm_delete.html"
    success_url = reverse_lazy("inventory:supply_list")


class RequestListView(LoginRequiredMixin, AreaFilteredMixin, ListView):
    model = Request
    template_name = "inventory/request_list.html"
    context_object_name = "requests"

    LEGACY_REQUEST_COLUMNS = {
        "id",
        "created_at",
        "status",
        "academic_area_id",
        "requester_id",
        "equipment_id",
        "supply_id",
        "quantity",
    }

    def _table_columns(self, table_name):
        with connection.cursor() as cursor:
            description = connection.introspection.get_table_description(cursor, table_name)
        return {column.name for column in description}

    def _uses_legacy_request_schema(self):
        table_names = set(connection.introspection.table_names())
        if "inventory_requestitem" not in table_names:
            return True

        request_columns = self._table_columns(Request._meta.db_table)
        return self.LEGACY_REQUEST_COLUMNS.issubset(request_columns)

    def _legacy_queryset(self):
        profile = getattr(self.request.user, "profile", None)
        params = []
        where_clauses = []

        if not self.request.user.is_superuser:
            if profile.role == UserProfile.ROLE_STUDENT:
                where_clauses.append("r.requester_id = %s")
                params.append(self.request.user.id)
            else:
                where_clauses.append("r.academic_area_id = %s")
                params.append(profile.academic_area_id)

        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        query = f"""
            SELECT
                r.id,
                r.created_at,
                r.status,
                COALESCE(a.name, '') AS academic_area,
                COALESCE(e.name, s.name, '') AS resource_name,
                COALESCE(r.quantity, 0) AS quantity
            FROM inventory_request r
            INNER JOIN inventory_academicarea a ON a.id = r.academic_area_id
            LEFT JOIN inventory_equipment e ON e.id = r.equipment_id
            LEFT JOIN inventory_supply s ON s.id = r.supply_id
            {where_sql}
            ORDER BY r.created_at DESC
        """

        with connection.cursor() as cursor:
            cursor.execute(query, params)
            rows = cursor.fetchall()

        status_labels = dict(Request.STATUS_CHOICES)
        return [
            {
                "id": row[0],
                "created_at": row[1],
                "student_name": "-",
                "teacher_name": "-",
                "subject_name": "Solicitud heredada",
                "class_datetime": None,
                "academic_area": row[3],
                "items_summary": [
                    f"{row[4]} — {row[5]}"
                ] if row[4] else [],
                "status_display": status_labels.get(row[2], row[2]),
            }
            for row in rows
        ]

    def get_queryset(self):
        if self._uses_legacy_request_schema():
            return self._legacy_queryset()

        queryset = Request.objects.select_related("requester", "academic_area").prefetch_related("items__equipment", "items__supply")
        if self.request.user.is_superuser:
            filtered_queryset = queryset
        else:
            profile = self.request.user.profile
            if profile.role == UserProfile.ROLE_STUDENT:
                filtered_queryset = queryset.filter(requester=self.request.user)
            else:
                filtered_queryset = queryset.filter(academic_area=profile.academic_area)

        return [
            {
                "id": request.id,
                "created_at": request.created_at,
                "student_name": request.student_name,
                "teacher_name": request.teacher_name or "-",
                "subject_name": request.subject_name,
                "class_datetime": request.class_datetime,
                "academic_area": str(request.academic_area),
                "items_summary": [
                    f"{item.resource_name} — {item.quantity}"
                    for item in request.items.all()
                ],
                "status_display": request.get_status_display(),
            }
            for request in filtered_queryset
        ]


class RequestCreateView(LoginRequiredMixin, StudentRequiredMixin, CreateView):
    model = Request
    form_class = RequestForm
    template_name = "inventory/request_form.html"
    success_url = reverse_lazy("inventory:request_list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile = getattr(self.request.user, "profile", None)
        area = getattr(profile, "academic_area", None)
        if self.request.method == "POST":
            context["item_formset"] = RequestItemFormSet(self.request.POST, instance=self.object, area=area)
        else:
            context["item_formset"] = RequestItemFormSet(instance=self.object, area=area)
        return context

    def form_valid(self, form):
        context = self.get_context_data(form=form)
        item_formset = context["item_formset"]
        profile = self.request.user.profile
        form.instance.requester = self.request.user
        form.instance.academic_area = profile.academic_area

        if not item_formset.is_valid():
            return self.form_invalid(form)

        self.object = form.save()
        item_formset.instance = self.object
        item_formset.save()
        messages.success(self.request, "Solicitud registrada correctamente.")
        return redirect(self.success_url)

    def form_invalid(self, form):
        messages.error(self.request, "Revisa los datos de la solicitud antes de continuar.")
        return self.render_to_response(self.get_context_data(form=form))


def import_equipment_view(request):
    if not request.user.is_authenticated:
        return redirect("login")
    form = ImportExcelForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        result = import_equipment_excel(request.FILES["file"])
        messages.success(
            request,
            f"Importación completada. Creados: {result['created']}, actualizados: {result['updated']}, errores: {len(result['errors'])}"
        )
        return redirect("inventory:equipment_list")

    return render(request, "inventory/import_form.html", {
        "form": form,
        "title": "Importar equipos"
    })


def import_supply_view(request):
    if not request.user.is_authenticated:
        return redirect("login")
    form = ImportExcelForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        result = import_supply_excel(request.FILES["file"])
        messages.success(
            request,
            f"Importación completada. Creados: {result['created']}, actualizados: {result['updated']}, errores: {len(result['errors'])}"
        )
        return redirect("inventory:supply_list")

    return render(request, "inventory/import_form.html", {
        "form": form,
        "title": "Importar insumos"
    })

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView

from .forms import EquipmentForm, SupplyForm, ImportExcelForm, RequestForm
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
        queryset = Equipment.objects.select_related("storage_location", "academic_area").prefetch_related("careers", "subjects", "codes")
        queryset = self.filter_by_area(queryset)
        q = self.request.GET.get("q")
        if q:
            queryset = queryset.filter(name__icontains=q)
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

    def get_queryset(self):
        queryset = Request.objects.select_related("requester", "equipment", "supply", "academic_area")
        if self.request.user.is_superuser:
            return queryset
        profile = self.request.user.profile
        if profile.role == UserProfile.ROLE_STUDENT:
            return queryset.filter(requester=self.request.user)
        return queryset.filter(academic_area=profile.academic_area)


class RequestCreateView(LoginRequiredMixin, StudentRequiredMixin, CreateView):
    model = Request
    form_class = RequestForm
    template_name = "inventory/form.html"
    success_url = reverse_lazy("inventory:request_list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        profile = self.request.user.profile
        form.instance.requester = self.request.user
        form.instance.academic_area = profile.academic_area
        messages.success(self.request, "Solicitud registrada correctamente.")
        return super().form_valid(form)


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

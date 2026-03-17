from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView

from .forms import EquipmentForm, SupplyForm, ImportExcelForm
from .models import Equipment, Supply
from .services.importers import import_equipment_excel, import_supply_excel


class EquipmentListView(ListView):
    model = Equipment
    template_name = "inventory/equipment_list.html"
    context_object_name = "equipments"
    paginate_by = 20

    def get_queryset(self):
        queryset = Equipment.objects.select_related("storage_location").prefetch_related("careers", "subjects", "codes")
        q = self.request.GET.get("q")
        if q:
            queryset = queryset.filter(name__icontains=q)
        return queryset


class EquipmentCreateView(CreateView):
    model = Equipment
    form_class = EquipmentForm
    template_name = "inventory/form.html"
    success_url = reverse_lazy("inventory:equipment_list")


class EquipmentUpdateView(UpdateView):
    model = Equipment
    form_class = EquipmentForm
    template_name = "inventory/form.html"
    success_url = reverse_lazy("inventory:equipment_list")


class EquipmentDeleteView(DeleteView):
    model = Equipment
    template_name = "inventory/confirm_delete.html"
    success_url = reverse_lazy("inventory:equipment_list")


class SupplyListView(ListView):
    model = Supply
    template_name = "inventory/supply_list.html"
    context_object_name = "supplies"
    paginate_by = 20

    def get_queryset(self):
        queryset = Supply.objects.select_related("storage_location")
        q = self.request.GET.get("q")
        if q:
            queryset = queryset.filter(name__icontains=q)
        return queryset


class SupplyCreateView(CreateView):
    model = Supply
    form_class = SupplyForm
    template_name = "inventory/form.html"
    success_url = reverse_lazy("inventory:supply_list")


class SupplyUpdateView(UpdateView):
    model = Supply
    form_class = SupplyForm
    template_name = "inventory/form.html"
    success_url = reverse_lazy("inventory:supply_list")


class SupplyDeleteView(DeleteView):
    model = Supply
    template_name = "inventory/confirm_delete.html"
    success_url = reverse_lazy("inventory:supply_list")


def import_equipment_view(request):
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
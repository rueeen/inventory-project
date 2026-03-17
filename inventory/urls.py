from django.urls import path
from .views import (
    EquipmentListView, EquipmentCreateView, EquipmentUpdateView, EquipmentDeleteView,
    SupplyListView, SupplyCreateView, SupplyUpdateView, SupplyDeleteView,
    import_equipment_view, import_supply_view,
)

app_name = "inventory"

urlpatterns = [
    path("", EquipmentListView.as_view(), name="equipment_list"),
    path("equipos/nuevo/", EquipmentCreateView.as_view(), name="equipment_create"),
    path("equipos/<int:pk>/editar/", EquipmentUpdateView.as_view(), name="equipment_update"),
    path("equipos/<int:pk>/eliminar/", EquipmentDeleteView.as_view(), name="equipment_delete"),
    path("equipos/importar/", import_equipment_view, name="equipment_import"),

    path("insumos/", SupplyListView.as_view(), name="supply_list"),
    path("insumos/nuevo/", SupplyCreateView.as_view(), name="supply_create"),
    path("insumos/<int:pk>/editar/", SupplyUpdateView.as_view(), name="supply_update"),
    path("insumos/<int:pk>/eliminar/", SupplyDeleteView.as_view(), name="supply_delete"),
    path("insumos/importar/", import_supply_view, name="supply_import"),
]
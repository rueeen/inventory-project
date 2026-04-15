from django.contrib.auth import views as auth_views
from django.urls import path

from .forms import LoginForm
from .views import (
    EquipmentListView,
    EquipmentCreateView,
    EquipmentUpdateView,
    EquipmentDeleteView,
    SupplyListView,
    SupplyCreateView,
    SupplyUpdateView,
    SupplyDeleteView,
    RequestListView,
    RequestCreateView,
    import_equipment_view,
    import_supply_view,
)

app_name = "inventory"

urlpatterns = [
    path("", EquipmentListView.as_view(), name="equipment_list"),
    path("login/", auth_views.LoginView.as_view(template_name="inventory/login.html", authentication_form=LoginForm), name="login"),
    path("logout/", auth_views.LogoutView.as_view(next_page="inventory:login"), name="logout"),

    path("equipos/nuevo/", EquipmentCreateView.as_view(), name="equipment_create"),
    path("equipos/<int:pk>/editar/", EquipmentUpdateView.as_view(), name="equipment_update"),
    path("equipos/<int:pk>/eliminar/", EquipmentDeleteView.as_view(), name="equipment_delete"),
    path("equipos/importar/", import_equipment_view, name="equipment_import"),

    path("insumos/", SupplyListView.as_view(), name="supply_list"),
    path("insumos/nuevo/", SupplyCreateView.as_view(), name="supply_create"),
    path("insumos/<int:pk>/editar/", SupplyUpdateView.as_view(), name="supply_update"),
    path("insumos/<int:pk>/eliminar/", SupplyDeleteView.as_view(), name="supply_delete"),
    path("insumos/importar/", import_supply_view, name="supply_import"),

    path("solicitudes/", RequestListView.as_view(), name="request_list"),
    path("solicitudes/nueva/", RequestCreateView.as_view(), name="request_create"),
]

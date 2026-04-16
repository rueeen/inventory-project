from django.contrib.auth import views as auth_views
from django.urls import path

from .forms import LoginForm
from .views import (
    EquipmentCreateView,
    EquipmentDeleteView,
    EquipmentImportView,
    EquipmentListView,
    EquipmentUpdateView,
    RequestCreateView,
    RequestListView,
    SupplyCreateView,
    SupplyDeleteView,
    SupplyImportView,
    SupplyListView,
    SupplyUpdateView,
    cart_add_item,
    cart_remove_item,
    cart_update_item,
    equipment_search_api,
    supply_search_api,
)

app_name = "inventory"

urlpatterns = [
    path("", EquipmentListView.as_view(), name="equipment_list"),
    path(
        "login/",
        auth_views.LoginView.as_view(
            template_name="inventory/login.html",
            authentication_form=LoginForm,
        ),
        name="login",
    ),
    path(
        "logout/",
        auth_views.LogoutView.as_view(next_page="inventory:login"),
        name="logout",
    ),
    path("equipos/nuevo/", EquipmentCreateView.as_view(), name="equipment_create"),
    path("equipos/<int:pk>/editar/", EquipmentUpdateView.as_view(), name="equipment_update"),
    path("equipos/<int:pk>/eliminar/", EquipmentDeleteView.as_view(), name="equipment_delete"),
    path("equipos/importar/", EquipmentImportView.as_view(), name="equipment_import"),
    path("equipos/<int:pk>/agregar-carrito/", cart_add_item, {"resource_type": "equipment"}, name="cart_add_equipment"),
    path("insumos/", SupplyListView.as_view(), name="supply_list"),
    path("insumos/nuevo/", SupplyCreateView.as_view(), name="supply_create"),
    path("insumos/<int:pk>/editar/", SupplyUpdateView.as_view(), name="supply_update"),
    path("insumos/<int:pk>/eliminar/", SupplyDeleteView.as_view(), name="supply_delete"),
    path("insumos/importar/", SupplyImportView.as_view(), name="supply_import"),
    path("insumos/<int:pk>/agregar-carrito/", cart_add_item, {"resource_type": "supply"}, name="cart_add_supply"),
    path("solicitudes/", RequestListView.as_view(), name="request_list"),
    path("solicitudes/nueva/", RequestCreateView.as_view(), name="request_create"),
    path("carrito/<str:resource_type>/<int:pk>/actualizar/", cart_update_item, name="cart_update_item"),
    path("carrito/<str:resource_type>/<int:pk>/quitar/", cart_remove_item, name="cart_remove_item"),
    path("api/equipos/buscar/", equipment_search_api, name="equipment_search_api"),
    path("api/insumos/buscar/", supply_search_api, name="supply_search_api"),
]

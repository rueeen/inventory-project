from django.contrib.auth import views as auth_views
from django.urls import path

from .views import (
    equipment_list_view,
    equipment_create_view,
    equipment_update_view,
    equipment_delete_view,
    supply_list_view,
    supply_create_view,
    supply_update_view,
    supply_delete_view,
    request_list_view,
    request_create_view,
    import_equipment_view,
    login_view,
    import_supply_view,
)

app_name = "inventory"

urlpatterns = [
    path("", equipment_list_view, name="equipment_list"),
    path("login/", login_view, name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),

    path("equipos/nuevo/", equipment_create_view, name="equipment_create"),
    path("equipos/<int:pk>/editar/", equipment_update_view, name="equipment_update"),
    path("equipos/<int:pk>/eliminar/", equipment_delete_view, name="equipment_delete"),
    path("equipos/importar/", import_equipment_view, name="equipment_import"),

    path("insumos/", supply_list_view, name="supply_list"),
    path("insumos/nuevo/", supply_create_view, name="supply_create"),
    path("insumos/<int:pk>/editar/", supply_update_view, name="supply_update"),
    path("insumos/<int:pk>/eliminar/", supply_delete_view, name="supply_delete"),
    path("insumos/importar/", import_supply_view, name="supply_import"),

    path("solicitudes/", request_list_view, name="request_list"),
    path("solicitudes/nueva/", request_create_view, name="request_create"),
]

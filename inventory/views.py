from functools import wraps

from django.contrib import messages
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import redirect_to_login
from django.core.paginator import Paginator
from django.db import connection
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from .forms import EquipmentForm, SupplyForm, ImportExcelForm, LoginForm, RequestForm, RequestItemFormSet
from .models import Equipment, Supply, Request, UserProfile
from .services.importers import import_equipment_excel, import_supply_excel


def _user_area(user):
    profile = getattr(user, "profile", None)
    return getattr(profile, "academic_area", None)


def filter_queryset_by_area(user, queryset):
    if user.is_superuser:
        return queryset

    area = _user_area(user)
    if area is None:
        return queryset.none()

    return queryset.filter(academic_area=area)


def role_required(allowed_roles):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect_to_login(request.get_full_path())

            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)

            profile = getattr(request.user, "profile", None)
            if profile and profile.role in allowed_roles:
                return view_func(request, *args, **kwargs)

            messages.error(request, "No tienes permisos para acceder a esta sección.")
            return redirect("inventory:equipment_list")

        return _wrapped_view

    return decorator


def render_paginated(request, queryset, template_name, context_name, per_page=20, extra_context=None):
    paginator = Paginator(queryset, per_page)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        context_name: page_obj.object_list,
        "page_obj": page_obj,
        "is_paginated": page_obj.has_other_pages(),
        "paginator": paginator,
    }
    if extra_context:
        context.update(extra_context)

    return render(request, template_name, context)


@login_required
def equipment_list_view(request):
    queryset = Equipment.objects.select_related(
        "storage_location",
        "academic_area",
    ).prefetch_related(
        "careers",
        "subjects",
    )
    queryset = filter_queryset_by_area(request.user, queryset)

    q = request.GET.get("q")
    if q:
        queryset = queryset.filter(
            Q(name__icontains=q) | Q(inventory_code__icontains=q)
        )

    return render_paginated(request, queryset, "inventory/equipment_list.html", "equipments")


@login_required
@role_required({UserProfile.ROLE_COORDINATOR, UserProfile.ROLE_PANOL})
def equipment_create_view(request):
    form = EquipmentForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Equipo guardado correctamente.")
        return redirect("inventory:equipment_list")

    return render(request, "inventory/form.html", {"form": form})


@login_required
@role_required({UserProfile.ROLE_COORDINATOR, UserProfile.ROLE_PANOL})
def equipment_update_view(request, pk):
    equipment = get_object_or_404(Equipment, pk=pk)
    form = EquipmentForm(request.POST or None, instance=equipment)

    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Equipo actualizado correctamente.")
        return redirect("inventory:equipment_list")

    return render(request, "inventory/form.html", {"form": form, "object": equipment})


@login_required
@role_required({UserProfile.ROLE_COORDINATOR, UserProfile.ROLE_PANOL})
def equipment_delete_view(request, pk):
    equipment = get_object_or_404(Equipment, pk=pk)

    if request.method == "POST":
        equipment.delete()
        messages.success(request, "Equipo eliminado correctamente.")
        return redirect("inventory:equipment_list")

    return render(request, "inventory/confirm_delete.html", {"object": equipment})


@login_required
def supply_list_view(request):
    queryset = Supply.objects.select_related("storage_location", "academic_area")
    queryset = filter_queryset_by_area(request.user, queryset)

    q = request.GET.get("q")
    if q:
        queryset = queryset.filter(name__icontains=q)

    return render_paginated(request, queryset, "inventory/supply_list.html", "supplies")


@login_required
@role_required({UserProfile.ROLE_COORDINATOR, UserProfile.ROLE_PANOL})
def supply_create_view(request):
    form = SupplyForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Insumo guardado correctamente.")
        return redirect("inventory:supply_list")

    return render(request, "inventory/form.html", {"form": form})


@login_required
@role_required({UserProfile.ROLE_COORDINATOR, UserProfile.ROLE_PANOL})
def supply_update_view(request, pk):
    supply = get_object_or_404(Supply, pk=pk)
    form = SupplyForm(request.POST or None, instance=supply)

    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Insumo actualizado correctamente.")
        return redirect("inventory:supply_list")

    return render(request, "inventory/form.html", {"form": form, "object": supply})


@login_required
@role_required({UserProfile.ROLE_COORDINATOR, UserProfile.ROLE_PANOL})
def supply_delete_view(request, pk):
    supply = get_object_or_404(Supply, pk=pk)

    if request.method == "POST":
        supply.delete()
        messages.success(request, "Insumo eliminado correctamente.")
        return redirect("inventory:supply_list")

    return render(request, "inventory/confirm_delete.html", {"object": supply})


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


def _table_columns(table_name):
    with connection.cursor() as cursor:
        description = connection.introspection.get_table_description(cursor, table_name)
    return {column.name for column in description}


def _uses_legacy_request_schema():
    table_names = set(connection.introspection.table_names())
    if "inventory_requestitem" not in table_names:
        return True

    request_columns = _table_columns(Request._meta.db_table)
    return LEGACY_REQUEST_COLUMNS.issubset(request_columns)


def _legacy_requests_for_user(user):
    profile = getattr(user, "profile", None)
    params = []
    where_clauses = []

    if not user.is_superuser:
        if profile.role == UserProfile.ROLE_STUDENT:
            where_clauses.append("r.requester_id = %s")
            params.append(user.id)
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


def _request_items_for_user(user):
    if _uses_legacy_request_schema():
        return _legacy_requests_for_user(user)

    queryset = Request.objects.select_related("requester", "academic_area").prefetch_related("items__equipment", "items__supply")
    if user.is_superuser:
        filtered_queryset = queryset
    else:
        profile = user.profile
        if profile.role == UserProfile.ROLE_STUDENT:
            filtered_queryset = queryset.filter(requester=user)
        else:
            filtered_queryset = queryset.filter(academic_area=profile.academic_area)

    return [
        {
            "id": item.id,
            "created_at": item.created_at,
            "student_name": item.student_name,
            "teacher_name": item.teacher_name or "-",
            "subject_name": item.subject_name,
            "class_datetime": item.class_datetime,
            "academic_area": str(item.academic_area),
            "items_summary": [
                f"{request_item.resource_name} — {request_item.quantity}"
                for request_item in item.items.all()
            ],
            "status_display": item.get_status_display(),
        }
        for item in filtered_queryset
    ]


@login_required
def request_list_view(request):
    requests_data = _request_items_for_user(request.user)
    return render(request, "inventory/request_list.html", {"requests": requests_data})


@login_required
@role_required({UserProfile.ROLE_STUDENT})
def request_create_view(request):
    profile = getattr(request.user, "profile", None)
    area = getattr(profile, "academic_area", None)

    form = RequestForm(request.POST or None, user=request.user)
    if request.method == "POST":
        item_formset = RequestItemFormSet(request.POST, area=area)
    else:
        item_formset = RequestItemFormSet(area=area)

    if request.method == "POST" and form.is_valid() and item_formset.is_valid():
        request_obj = form.save(commit=False)
        request_obj.requester = request.user
        request_obj.academic_area = profile.academic_area
        request_obj.save()

        item_formset.instance = request_obj
        item_formset.save()

        messages.success(request, "Solicitud registrada correctamente.")
        return redirect("inventory:request_list")

    if request.method == "POST" and (not form.is_valid() or not item_formset.is_valid()):
        messages.error(request, "Revisa los datos de la solicitud antes de continuar.")

    return render(
        request,
        "inventory/request_form.html",
        {
            "form": form,
            "item_formset": item_formset,
            "object": None,
        },
    )




@login_required
@require_http_methods(["GET", "POST"])
def logout_view(request):
    auth_logout(request)
    return redirect("inventory:login")

@require_http_methods(["GET", "POST"])
def login_view(request):
    if request.user.is_authenticated:
        return redirect("inventory:equipment_list")

    form = LoginForm(request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        auth_login(request, form.get_user())
        return redirect("inventory:equipment_list")

    return render(request, "inventory/login.html", {"form": form})


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


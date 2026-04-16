from django.contrib import admin

from .models import (
    AcademicArea,
    Career,
    Equipment,
    Request,
    RequestItem,
    StorageLocation,
    Subject,
    Supply,
    UserProfile,
)


@admin.register(Equipment)
class EquipmentAdmin(admin.ModelAdmin):
    list_display = (
        "inventory_code",
        "name",
        "condition",
        "academic_area",
        "storage_location",
        "unit_value_uf",
        "created_at",
    )
    list_filter = (
        "condition",
        "academic_area",
        "storage_location",
        "careers",
        "subjects",
    )
    search_fields = (
        "inventory_code",
        "name",
        "detailed_spec",
        "observations",
    )
    filter_horizontal = ("careers", "subjects")
    readonly_fields = ("created_at", "updated_at")
    list_select_related = ("academic_area", "storage_location")


@admin.register(Supply)
class SupplyAdmin(admin.ModelAdmin):
    list_display = ("name", "academic_area", "storage_location", "total_existing", "created_at")
    list_filter = ("academic_area", "storage_location")
    search_fields = ("name", "detailed_spec", "observations")
    readonly_fields = ("created_at", "updated_at")
    list_select_related = ("academic_area", "storage_location")


class RequestItemInline(admin.TabularInline):
    model = RequestItem
    extra = 0
    fields = ("equipment", "supply", "quantity")


@admin.register(Request)
class RequestAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "requester",
        "academic_area",
        "total_quantity",
        "status",
        "created_at",
    )
    list_filter = ("academic_area", "status")
    search_fields = (
        "requester__username",
        "reason",
        "items__equipment__name",
        "items__equipment__inventory_code",
        "items__supply__name",
    )
    readonly_fields = ("created_at", "updated_at")
    list_select_related = ("requester", "academic_area")
    inlines = [RequestItemInline]


@admin.register(AcademicArea)
class AcademicAreaAdmin(admin.ModelAdmin):
    search_fields = ("name",)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "role", "academic_area")
    list_filter = ("role", "academic_area")
    search_fields = ("user__username", "user__first_name", "user__last_name")


@admin.register(StorageLocation)
class StorageLocationAdmin(admin.ModelAdmin):
    search_fields = ("name",)


@admin.register(Career)
class CareerAdmin(admin.ModelAdmin):
    search_fields = ("name",)


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ("code", "name")
    search_fields = ("code", "name")

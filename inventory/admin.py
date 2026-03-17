from django.contrib import admin

from .models import AcademicArea, Career, Equipment, EquipmentCode, Request, StorageLocation, Subject, Supply, UserProfile


class EquipmentCodeInline(admin.TabularInline):
    model = EquipmentCode
    extra = 1


@admin.register(Equipment)
class EquipmentAdmin(admin.ModelAdmin):
    list_display = ("name", "academic_area", "storage_location", "total_existing")
    list_filter = ("academic_area", "storage_location")
    search_fields = ("name",)
    inlines = [EquipmentCodeInline]


@admin.register(Supply)
class SupplyAdmin(admin.ModelAdmin):
    list_display = ("name", "academic_area", "storage_location", "total_existing")
    list_filter = ("academic_area", "storage_location")
    search_fields = ("name",)


@admin.register(Request)
class RequestAdmin(admin.ModelAdmin):
    list_display = ("requester", "academic_area", "equipment", "supply", "quantity", "status", "created_at")
    list_filter = ("academic_area", "status")
    search_fields = ("requester__username",)


admin.site.register(AcademicArea)
admin.site.register(UserProfile)
admin.site.register(StorageLocation)
admin.site.register(Career)
admin.site.register(Subject)

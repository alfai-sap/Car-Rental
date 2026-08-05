from django.contrib import admin
from .models import Vehicle, VehicleImage


class VehicleImageInline(admin.TabularInline):
    model = VehicleImage
    extra = 0
    fields = ['image', 'is_primary']


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ['make', 'model', 'year', 'type', 'transmission', 'fuel', 'seats', 'price_per_day', 'status']
    list_filter = ['type', 'transmission', 'fuel', 'status', 'seats']
    search_fields = ['make', 'model', 'description']
    ordering = ['-created_at']
    inlines = [VehicleImageInline]
    fieldsets = (
        ('Basic Info', {'fields': ('make', 'model', 'year', 'type', 'description')}),
        ('Specifications', {'fields': ('transmission', 'fuel', 'seats')}),
        ('Pricing & Status', {'fields': ('price_per_day', 'status')}),
    )


@admin.register(VehicleImage)
class VehicleImageAdmin(admin.ModelAdmin):
    list_display = ['vehicle', 'is_primary', 'uploaded_at']
    list_filter = ['is_primary']
    search_fields = ['vehicle__make', 'vehicle__model']

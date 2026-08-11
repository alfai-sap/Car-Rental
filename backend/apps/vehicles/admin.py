from django.contrib import admin, messages
from django.db.models.deletion import ProtectedError
from .models import Vehicle, VehicleImage, VehicleUnit


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

    def delete_model(self, request, obj):
        """Catch ProtectedError when bookings reference this vehicle."""
        try:
            obj.delete()
        except ProtectedError as e:
            ref_count = len(e.protected_objects)
            self.message_user(
                request,
                f'Cannot delete "{obj}". It is referenced by {ref_count} booking(s). '
                'Cancel or reassign those bookings first.',
                level=messages.ERROR,
            )

    def delete_queryset(self, request, queryset):
        """Catch ProtectedError for bulk deletes."""
        deleted = 0
        failed = []
        for obj in queryset:
            try:
                obj.delete()
                deleted += 1
            except ProtectedError:
                failed.append(str(obj))
        if deleted:
            self.message_user(request, f'{deleted} vehicle(s) deleted.')
        if failed:
            self.message_user(
                request,
                f'Could not delete {len(failed)} vehicle(s) — they are referenced by bookings: {", ".join(failed)}',
                level=messages.ERROR,
            )


@admin.register(VehicleImage)
class VehicleImageAdmin(admin.ModelAdmin):
    list_display = ['vehicle', 'is_primary', 'uploaded_at']
    list_filter = ['is_primary']
    search_fields = ['vehicle__make', 'vehicle__model']


@admin.register(VehicleUnit)
class VehicleUnitAdmin(admin.ModelAdmin):
    list_display = ['plate_number', 'vehicle', 'status', 'mileage', 'updated_at']
    list_filter = ['status']
    search_fields = ['plate_number', 'vehicle__make', 'vehicle__model']
    ordering = ['plate_number']
    readonly_fields = ['created_at', 'updated_at']

    def delete_model(self, request, obj):
        """Catch ProtectedError when assignment history references this unit."""
        try:
            obj.delete()
        except ProtectedError:
            self.message_user(
                request,
                f'Cannot delete unit \"{obj}\". It is referenced by booking assignment history. '
                'Remove or reassign those bookings first.',
                level=messages.ERROR,
            )

    def delete_queryset(self, request, queryset):
        deleted = 0
        failed = []
        for obj in queryset:
            try:
                obj.delete()
                deleted += 1
            except ProtectedError:
                failed.append(str(obj))
        if deleted:
            self.message_user(request, f'{deleted} unit(s) deleted.')
        if failed:
            self.message_user(
                request,
                f'Could not delete {len(failed)} unit(s) — they are referenced by assignment history.',
                level=messages.ERROR,
            )

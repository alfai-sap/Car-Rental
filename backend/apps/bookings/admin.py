from django.contrib import admin
from .models import Booking


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = [
        'booking_number', 'customer', 'vehicle', 'pickup_date', 'return_date',
        'rental_days', 'estimated_total', 'status', 'created_at',
    ]
    list_filter = ['status', 'pickup_date', 'return_date']
    search_fields = ['booking_number', 'customer__email', 'customer__first_name',
                     'customer__last_name', 'vehicle__make', 'vehicle__model']
    ordering = ['-created_at']
    readonly_fields = [
        'booking_number', 'rental_days', 'subtotal', 'estimated_total',
        'created_at', 'updated_at',
    ]
    fieldsets = (
        ('Booking Info', {
            'fields': ('booking_number', 'customer', 'vehicle', 'status', 'rejection_reason'),
        }),
        ('Dates', {
            'fields': ('pickup_date', 'return_date', 'pickup_time', 'return_time', 'rental_days'),
        }),
        ('Pricing', {
            'fields': ('subtotal', 'estimated_total'),
        }),
        ('Additional', {
            'fields': ('special_request', 'created_at', 'updated_at'),
        }),
    )
    actions = ['approve_selected', 'reject_selected']

    @admin.action(description='Approve selected bookings')
    def approve_selected(self, request, queryset):
        updated = queryset.filter(status='pending_approval').update(status='approved')
        self.message_user(request, f'{updated} booking(s) approved.')

    @admin.action(description='Reject selected bookings')
    def reject_selected(self, request, queryset):
        updated = queryset.filter(status='pending_approval').update(status='rejected', rejection_reason='Rejected by admin.')
        self.message_user(request, f'{updated} booking(s) rejected.')

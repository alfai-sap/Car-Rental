from django.contrib import admin
from apps.core import services as notify
from apps.core.services import create_audit_log
from .models import Booking, AssignmentHistory


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = [
        'booking_number', 'customer', 'vehicle', 'vehicle_unit', 'pickup_date', 'return_date',
        'rental_days', 'estimated_total', 'status', 'created_at',
    ]
    list_filter = ['status', 'pickup_date', 'return_date']
    search_fields = ['booking_number', 'customer__email', 'customer__first_name',
                     'customer__last_name', 'vehicle__make', 'vehicle__model']
    ordering = ['-created_at']
    readonly_fields = [
        'booking_number', 'rental_days', 'subtotal', 'estimated_total',
        'created_at', 'updated_at', 'handover_time', 'return_time_actual',
        # Status transitions must go through the API state machine (which
        # locks rows, maintains unit statuses, and writes audit logs).
        # Directly editing these in the admin would bypass all of that.
        'status', 'vehicle_unit', 'identity_snapshot',
    ]
    fieldsets = (
        ('Booking Info', {
            'fields': ('booking_number', 'customer', 'vehicle', 'vehicle_unit', 'status', 'rejection_reason'),
        }),
        ('Dates', {
            'fields': ('pickup_date', 'return_date', 'pickup_time', 'return_time', 'rental_days'),
        }),
        ('Pricing', {
            'fields': ('subtotal', 'estimated_total'),
        }),
        ('Return', {
            'fields': ('handover_time', 'return_time_actual', 'return_unit_status'),
        }),
        ('Identity', {
            'fields': ('identity_snapshot',),
        }),
        ('Additional', {
            'fields': ('special_request', 'created_at', 'updated_at'),
        }),
    )
    actions = ['approve_selected', 'reject_selected']

    @admin.action(description='Approve selected bookings')
    def approve_selected(self, request, queryset):
        count = 0
        for booking in queryset.filter(status='pending_approval'):
            before = {'status': booking.status}
            booking.status = 'awaiting_payment'
            booking.save()
            notify.notify_booking_approved(booking)
            create_audit_log(
                actor=request.user, action='booking_approved', booking=booking,
                summary=f'Approved booking {booking.booking_number} (bulk admin action)',
                before_state=before, after_state={'status': booking.status},
                request=request,
            )
            count += 1
        self.message_user(request, f'{count} booking(s) approved and notified. Now awaiting payment.')

    @admin.action(description='Reject selected bookings')
    def reject_selected(self, request, queryset):
        count = 0
        for booking in queryset.filter(status='pending_approval'):
            before = {'status': booking.status}
            booking.status = 'rejected'
            booking.rejection_reason = 'Rejected by admin.'
            booking.save()
            notify.notify_booking_rejected(booking)
            create_audit_log(
                actor=request.user, action='booking_rejected', booking=booking,
                summary=f'Rejected booking {booking.booking_number} (bulk admin action)',
                before_state=before, after_state={'status': booking.status},
                request=request,
            )
            count += 1
        self.message_user(request, f'{count} booking(s) rejected and notified.')


@admin.register(AssignmentHistory)
class AssignmentHistoryAdmin(admin.ModelAdmin):
    list_display = ['booking', 'previous_unit', 'new_unit', 'reason', 'changed_by', 'created_at']
    list_filter = ['created_at']
    search_fields = ['booking__booking_number', 'reason', 'changed_by__email']
    readonly_fields = ['created_at']
    ordering = ['-created_at']

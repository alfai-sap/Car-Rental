"""
Notification service — centralizes in-app notification creation and email sending
for all major rental transaction events.

Never call email-sending code directly from views. Always go through this module.
"""
import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone

from apps.core.models import Notification, AuditLog

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
#  Notification creation
# ─────────────────────────────────────────────

def create_notification(*, user, notification_type, title, message, booking=None,
                         is_admin=False, link=''):
    """Create an in-app notification and return it."""
    return Notification.objects.create(
        user=user,
        notification_type=notification_type,
        title=title,
        message=message,
        booking=booking,
        is_read=False,
        is_admin_notification=is_admin,
        link=link,
    )


def create_admin_notification(*, notification_type, title, message, booking=None, link=''):
    """Create a notification visible to all staff users."""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    notifications = []
    for admin in User.objects.filter(is_staff=True):
        n = Notification.objects.create(
            user=admin,
            notification_type=notification_type,
            title=title,
            message=message,
            booking=booking,
            is_read=False,
            is_admin_notification=True,
            link=link,
        )
        notifications.append(n)
    return notifications


# ─────────────────────────────────────────────
#  Audit log helper
# ─────────────────────────────────────────────

def create_audit_log(*, actor, action, booking=None, payment=None, summary,
                     before_state=None, after_state=None, request=None):
    """Create an immutable audit log entry for an admin action."""
    ip = None
    if request:
        x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR', '')
        if x_forwarded:
            ip = x_forwarded.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '')

    return AuditLog.objects.create(
        actor=actor,
        action=action,
        booking=booking,
        payment=payment,
        summary=summary,
        before_state=before_state or {},
        after_state=after_state or {},
        ip_address=ip,
    )


# ─────────────────────────────────────────────
#  Email helper
# ─────────────────────────────────────────────

def send_email(*, to_email, subject, template_name, context):
    """Send an HTML+plain-text email. Silently logs errors."""
    first_name = context.get('first_name', 'there')

    try:
        html_content = render_to_string(template_name, context)
    except Exception:
        html_content = None

    text_content = _build_plain_text(subject, context)

    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[to_email],
    )
    if html_content:
        msg.attach_alternative(html_content, 'text/html')
    try:
        msg.send()
    except Exception as e:
        logger.error(f"Failed to send email '{subject}' to {to_email}: {e}")


def _build_plain_text(subject, ctx):
    lines = [f"Hi {ctx.get('first_name', 'there')},", "", subject, ""]
    if ctx.get('booking_number'):
        lines.append(f"Booking: {ctx['booking_number']}")
    if ctx.get('vehicle_name'):
        lines.append(f"Vehicle: {ctx['vehicle_name']}")
    if ctx.get('pickup_date') and ctx.get('return_date'):
        lines.append(f"Dates: {ctx['pickup_date']} – {ctx['return_date']}")
    if ctx.get('estimated_total'):
        lines.append(f"Total: ₱{ctx['estimated_total']}")
    if ctx.get('booking') and ctx.get('booking').id:
        lines.append(f"View: {settings.FRONTEND_URL}/transactions/{ctx['booking'].id}")
    lines.extend(["", "– Car Rental Team"])
    return "\n".join(lines)


# ─────────────────────────────────────────────
#  Transaction event helpers
# ─────────────────────────────────────────────

def _vehicle_name(booking):
    return f"{booking.vehicle.year} {booking.vehicle.make} {booking.vehicle.model}"


def _booking_link(booking):
    return f"/transactions/{booking.id}"


def _admin_link(booking):
    return f"/admin/transactions/{booking.id}"


# ── Customer notifications ──

def notify_booking_submitted(booking):
    msg = f"Your booking request for {_vehicle_name(booking)} has been submitted and is pending owner review."
    create_notification(
        user=booking.customer, notification_type='booking_submitted',
        title='Booking Request Submitted', message=msg,
        booking=booking, link=_booking_link(booking),
    )
    # Also notify admin
    admin_msg = f"New booking request from {booking.customer.first_name} {booking.customer.last_name} for {_vehicle_name(booking)}."
    create_admin_notification(
        notification_type='booking_submitted', title='New Booking Request',
        message=admin_msg, booking=booking, link=_admin_link(booking),
    )


def notify_booking_approved(booking):
    msg = f"Your booking for {_vehicle_name(booking)} has been approved. Please complete payment to confirm."
    create_notification(
        user=booking.customer, notification_type='booking_approved',
        title='Booking Approved', message=msg,
        booking=booking, link=_booking_link(booking),
    )
    create_admin_notification(
        notification_type='booking_approved',
        title=f'Booking Approved: {booking.booking_number}',
        message=f"{booking.customer.first_name} {booking.customer.last_name}'s booking for {_vehicle_name(booking)} has been approved.",
        booking=booking, link=_admin_link(booking),
    )
    send_email(
        to_email=booking.customer.email,
        subject='Booking Approved — Payment Required',
        template_name='emails/booking_approved.html',
        context=_email_context(booking),
    )


def notify_booking_rejected(booking):
    reason = f" Reason: {booking.rejection_reason}" if booking.rejection_reason else ""
    msg = f"Your booking for {_vehicle_name(booking)} was not approved.{reason}"
    create_notification(
        user=booking.customer, notification_type='booking_rejected',
        title='Booking Rejected', message=msg,
        booking=booking, link=_booking_link(booking),
    )
    create_admin_notification(
        notification_type='booking_rejected',
        title=f'Booking Rejected: {booking.booking_number}',
        message=f"{booking.customer.first_name} {booking.customer.last_name}'s booking for {_vehicle_name(booking)} was rejected.{reason}",
        booking=booking, link=_admin_link(booking),
    )
    send_email(
        to_email=booking.customer.email,
        subject='Booking Request Declined',
        template_name='emails/booking_rejected.html',
        context={**_email_context(booking), 'rejection_reason': booking.rejection_reason},
    )


def notify_booking_cancelled(booking):
    reason = f" Reason: {booking.cancellation_reason}" if booking.cancellation_reason else ""
    msg = f"Your booking #{booking.booking_number} for {_vehicle_name(booking)} has been cancelled.{reason}"
    create_notification(
        user=booking.customer, notification_type='transaction_completed',
        title='Booking Cancelled', message=msg,
        booking=booking, link=_booking_link(booking),
    )
    create_admin_notification(
        notification_type='transaction_completed',
        title=f'Booking Cancelled: {booking.booking_number}',
        message=f"{booking.customer.first_name} {booking.customer.last_name}'s booking for {_vehicle_name(booking)} has been cancelled.{reason}",
        booking=booking, link=_admin_link(booking),
    )


def notify_payment_required(booking):
    msg = f"Payment is required for your {_vehicle_name(booking)} booking. Please pay to confirm your reservation."
    create_notification(
        user=booking.customer, notification_type='payment_required',
        title='Payment Required', message=msg,
        booking=booking, link=_booking_link(booking),
    )


def notify_payment_successful(booking):
    msg = f"Payment for your {_vehicle_name(booking)} booking has been confirmed."
    create_notification(
        user=booking.customer, notification_type='payment_successful',
        title='Payment Successful', message=msg,
        booking=booking, link=_booking_link(booking),
    )
    create_admin_notification(
        notification_type='payment_successful',
        title=f'Payment Received: {booking.booking_number}',
        message=f"Payment confirmed for {booking.customer.first_name} {booking.customer.last_name}'s booking of {_vehicle_name(booking)}.",
        booking=booking, link=_admin_link(booking),
    )
    send_email(
        to_email=booking.customer.email,
        subject='Payment Confirmed — Booking Finalized',
        template_name='emails/booking_confirmed.html',
        context=_email_context(booking),
    )


def notify_payment_failed(booking):
    msg = f"Payment for your {_vehicle_name(booking)} booking has failed. Please try again or contact support."
    create_notification(
        user=booking.customer, notification_type='payment_failed',
        title='Payment Failed', message=msg,
        booking=booking, link=_booking_link(booking),
    )


def notify_payment_expired(booking):
    msg = (
        f"Your payment for {_vehicle_name(booking)} has expired. "
        f"You can request a new payment attempt from your booking details."
    )
    create_notification(
        user=booking.customer, notification_type='payment_failed',
        title='Payment Expired — Request a New Attempt', message=msg,
        booking=booking, link=_booking_link(booking),
    )
    create_admin_notification(
        notification_type='payment_failed',
        title=f'Payment Expired: {booking.booking_number}',
        message=(
            f"Payment for {booking.customer.first_name} {booking.customer.last_name}'s "
            f"booking of {_vehicle_name(booking)} has expired."
        ),
        booking=booking, link=_admin_link(booking),
    )


def notify_repayment_requested(booking):
    msg = (
        f"{booking.customer.first_name} {booking.customer.last_name} has requested "
        f"a new payment attempt for booking {booking.booking_number}."
    )
    create_admin_notification(
        notification_type='payment_required',
        title=f'Repayment Requested: {booking.booking_number}',
        message=msg,
        booking=booking, link=_admin_link(booking),
    )


def notify_repayment_approved(booking):
    msg = f"Your request for a new payment attempt for {_vehicle_name(booking)} has been approved. Please complete payment."
    create_notification(
        user=booking.customer, notification_type='payment_required',
        title='New Payment Approved', message=msg,
        booking=booking, link=_booking_link(booking),
    )


def notify_repayment_rejected(booking):
    msg = f"Your request for a new payment attempt for {_vehicle_name(booking)} was rejected and your booking has been cancelled."
    create_notification(
        user=booking.customer, notification_type='booking_rejected',
        title='Repayment Request Rejected', message=msg,
        booking=booking, link=_booking_link(booking),
    )


def notify_booking_confirmed(booking):
    msg = f"Your booking #{booking.booking_number} for {_vehicle_name(booking)} is now confirmed."
    create_notification(
        user=booking.customer, notification_type='booking_confirmed',
        title='Booking Confirmed', message=msg,
        booking=booking, link=_booking_link(booking),
    )
    create_admin_notification(
        notification_type='booking_confirmed',
        title=f'Booking Confirmed: {booking.booking_number}',
        message=f"{booking.customer.first_name} {booking.customer.last_name}'s booking for {_vehicle_name(booking)} is confirmed.",
        booking=booking, link=_admin_link(booking),
    )


def notify_unit_assigned(booking, unit):
    msg = f"Vehicle unit {unit.plate_number} has been assigned to your booking #{booking.booking_number} for {_vehicle_name(booking)}."
    create_notification(
        user=booking.customer, notification_type='unit_assigned',
        title='Vehicle Unit Assigned', message=msg,
        booking=booking, link=_booking_link(booking),
    )
    create_admin_notification(
        notification_type='unit_assigned',
        title=f'Unit {unit.plate_number} Assigned',
        message=f"Assigned {unit.plate_number} to booking {booking.booking_number}.",
        booking=booking, link=_admin_link(booking),
    )


def notify_unit_changed(booking, previous_plate, new_plate, reason):
    msg = (f"Vehicle unit changed from {previous_plate} to {new_plate} "
           f"for booking #{booking.booking_number}. Reason: {reason}")
    create_notification(
        user=booking.customer, notification_type='unit_changed',
        title='Vehicle Unit Changed', message=msg,
        booking=booking, link=_booking_link(booking),
    )
    create_admin_notification(
        notification_type='unit_changed',
        title=f'Unit Changed for {booking.booking_number}',
        message=f"Unit changed: {previous_plate} → {new_plate}. Reason: {reason}",
        booking=booking, link=_admin_link(booking),
    )


def notify_pickup_reminder(booking):
    msg = f"Reminder: Your {_vehicle_name(booking)} rental pickup is scheduled for {booking.pickup_date}."
    create_notification(
        user=booking.customer, notification_type='pickup_reminder',
        title='Pickup Reminder', message=msg,
        booking=booking, link=_booking_link(booking),
    )


def notify_rental_activated(booking):
    msg = f"Your rental of {_vehicle_name(booking)} is now active."
    create_notification(
        user=booking.customer, notification_type='rental_activated',
        title='Rental Activated', message=msg,
        booking=booking, link=_booking_link(booking),
    )
    create_admin_notification(
        notification_type='rental_activated',
        title=f'Rental Active: {booking.booking_number}',
        message=f"Rental for {_vehicle_name(booking)} is now active (customer: {booking.customer.first_name} {booking.customer.last_name}).",
        booking=booking, link=_admin_link(booking),
    )


def notify_vehicle_returned(booking):
    msg = f"Your {_vehicle_name(booking)} has been marked as returned."
    create_notification(
        user=booking.customer, notification_type='vehicle_returned',
        title='Vehicle Returned', message=msg,
        booking=booking, link=_booking_link(booking),
    )
    create_admin_notification(
        notification_type='vehicle_returned',
        title=f'Vehicle Returned: {booking.booking_number}',
        message=f"{_vehicle_name(booking)} ({booking.booking_number}) has been returned.",
        booking=booking, link=_admin_link(booking),
    )


def notify_transaction_completed(booking):
    msg = f"Your transaction #{booking.booking_number} for {_vehicle_name(booking)} has been completed."
    create_notification(
        user=booking.customer, notification_type='transaction_completed',
        title='Transaction Completed', message=msg,
        booking=booking, link=_booking_link(booking),
    )
    create_admin_notification(
        notification_type='transaction_completed',
        title=f'Transaction Completed: {booking.booking_number}',
        message=f"{booking.customer.first_name} {booking.customer.last_name}'s rental of {_vehicle_name(booking)} has been completed.",
        booking=booking, link=_admin_link(booking),
    )


def notify_additional_payment_required(booking, amount):
    msg = f"An additional payment of ₱{amount} is required for booking #{booking.booking_number}."
    create_notification(
        user=booking.customer, notification_type='additional_payment_required',
        title='Additional Payment Required', message=msg,
        booking=booking, link=_booking_link(booking),
    )


# ── Email context ──

def _email_context(booking):
    return {
        'first_name': booking.customer.first_name or 'there',
        'booking': booking,
        'booking_number': booking.booking_number,
        'vehicle_name': _vehicle_name(booking),
        'pickup_date': booking.pickup_date,
        'return_date': booking.return_date,
        'estimated_total': booking.estimated_total,
    }

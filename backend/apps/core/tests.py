from datetime import date, timedelta
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient

from apps.core.models import Notification
from apps.bookings.models import Booking
from apps.accounts.models import IdentityDocument
from apps.vehicles.models import Vehicle, VehicleUnit

User = get_user_model()


class NotificationModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='cust@test.com', username='cust', password='Pass123!',
            first_name='Test', last_name='Customer',
        )

    def test_notification_str(self):
        n = Notification.objects.create(
            user=self.user, notification_type='booking_submitted',
            title='Booking Submitted', message='Your booking is pending.',
        )
        self.assertIn('Booking Submitted', str(n))
        self.assertIn('cust@test.com', str(n))

    def test_notification_is_unread_by_default(self):
        n = Notification.objects.create(
            user=self.user, notification_type='booking_submitted',
            title='Booking Submitted', message='Your booking is pending.',
        )
        self.assertFalse(n.is_read)

    def test_notification_can_be_marked_read(self):
        n = Notification.objects.create(
            user=self.user, notification_type='booking_submitted',
            title='Booking Submitted', message='Your booking is pending.',
        )
        n.is_read = True
        n.save()
        n.refresh_from_db()
        self.assertTrue(n.is_read)


class NotificationAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.customer = User.objects.create_user(
            email='cust@test.com', username='cust', password='Pass123!',
            first_name='Test', last_name='Customer', is_verified=True,
            phone='09123456789',
        )
        self.admin = User.objects.create_user(
            email='admin@test.com', username='admin', password='Admin123!',
            is_staff=True, is_superuser=True, is_verified=True,
        )
        self.vehicle = Vehicle.objects.create(
            make='Toyota', model='Vios', year=2024, type='sedan',
            price_per_day=2500.00,
        )
        VehicleUnit.objects.create(
            vehicle=self.vehicle, plate_number='ABC-1234', status='available',
        )
        # Add driver's license for the customer so bookings can be created
        IdentityDocument.objects.create(
            user=self.customer, document_type='drivers_license',
            document_number='D01-12-345678',
        )

    def _login(self, user):
        # Use force_authenticate to avoid login rate-limit in tests
        self.client.force_authenticate(user=user)

    def _create_booking(self, customer=None):
        cust = customer or self.customer
        return Booking.objects.create(
            customer=cust,
            vehicle=self.vehicle,
            pickup_date=date.today() + timedelta(days=2),
            return_date=date.today() + timedelta(days=5),
            pickup_time='09:00',
            return_time='17:00',
            rental_days=4,
            subtotal=10000.00,
            estimated_total=10000.00,
            status='pending_approval',
        )

    # ── Notification retrieval ──

    def test_get_notifications_requires_auth(self):
        response = self.client.get('/api/notifications/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_notifications_empty(self):
        self._login(self.customer)
        response = self.client.get('/api/notifications/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 0)
        self.assertEqual(response.data['unread_count'], 0)
        self.assertEqual(len(response.data['notifications']), 0)

    def test_get_notifications_shows_only_own(self):
        self._login(self.customer)
        Notification.objects.create(
            user=self.customer, notification_type='booking_submitted',
            title='My Notification', message='Customer note.',
        )
        other = User.objects.create_user(
            email='other@test.com', username='other', password='Pass123!',
        )
        Notification.objects.create(
            user=other, notification_type='booking_submitted',
            title='Other Notification', message='Should not see this.',
        )
        response = self.client.get('/api/notifications/')
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['notifications'][0]['title'], 'My Notification')

    def test_get_notifications_returns_booking_number(self):
        self._login(self.customer)
        booking = self._create_booking()
        Notification.objects.create(
            user=self.customer, notification_type='booking_submitted',
            title='Booking Submitted', message='Your booking is pending.',
            booking=booking,
        )
        response = self.client.get('/api/notifications/')
        self.assertEqual(response.data['count'], 1)
        self.assertIsNotNone(response.data['notifications'][0]['booking_id'])
        self.assertEqual(response.data['notifications'][0]['booking_number'], booking.booking_number)

    def test_unread_count_is_accurate(self):
        self._login(self.customer)
        Notification.objects.create(
            user=self.customer, notification_type='booking_submitted',
            title='Unread 1', message='Msg.', is_read=False,
        )
        Notification.objects.create(
            user=self.customer, notification_type='booking_approved',
            title='Unread 2', message='Msg.', is_read=False,
        )
        Notification.objects.create(
            user=self.customer, notification_type='booking_confirmed',
            title='Read 1', message='Msg.', is_read=True,
        )
        response = self.client.get('/api/notifications/')
        self.assertEqual(response.data['count'], 3)
        self.assertEqual(response.data['unread_count'], 2)

    # ── Mark as read ──

    def test_mark_all_read(self):
        self._login(self.customer)
        Notification.objects.create(
            user=self.customer, notification_type='booking_submitted',
            title='Unread 1', message='Msg.',
        )
        Notification.objects.create(
            user=self.customer, notification_type='booking_approved',
            title='Unread 2', message='Msg.',
        )
        response = self.client.post('/api/notifications/', {'mark_all': True}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Notification.objects.filter(user=self.customer, is_read=False).count(), 0)

    def test_mark_single_notification_read(self):
        self._login(self.customer)
        n = Notification.objects.create(
            user=self.customer, notification_type='booking_submitted',
            title='Unread', message='Msg.',
        )
        response = self.client.post('/api/notifications/', {
            'notification_id': n.id,
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        n.refresh_from_db()
        self.assertTrue(n.is_read)

    def test_mark_all_read_requires_auth(self):
        response = self.client.post('/api/notifications/', {'mark_all': True}, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # ── Booking transition notifications ──

    def test_booking_submitted_creates_customer_notification(self):
        self._login(self.customer)
        response = self.client.post('/api/bookings/', {
            'vehicle': self.vehicle.id,
            'pickup_date': (date.today() + timedelta(days=2)).isoformat(),
            'return_date': (date.today() + timedelta(days=5)).isoformat(),
            'pickup_time': '09:00',
            'return_time': '17:00',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            Notification.objects.filter(
                user=self.customer, notification_type='booking_submitted',
            ).exists()
        )

    def test_booking_submitted_creates_admin_notification(self):
        self._login(self.customer)
        self.client.post('/api/bookings/', {
            'vehicle': self.vehicle.id,
            'pickup_date': (date.today() + timedelta(days=2)).isoformat(),
            'return_date': (date.today() + timedelta(days=5)).isoformat(),
            'pickup_time': '09:00',
            'return_time': '17:00',
        }, format='json')
        self.assertTrue(
            Notification.objects.filter(
                user=self.admin, notification_type='booking_submitted',
                is_admin_notification=True,
            ).exists()
        )

    def test_booking_approved_creates_notifications(self):
        booking = self._create_booking()
        self._login(self.admin)
        self.client.post(f'/api/bookings/{booking.id}/approve/')
        self.assertTrue(
            Notification.objects.filter(
                user=self.customer, notification_type='booking_approved',
            ).exists()
        )
        self.assertTrue(
            Notification.objects.filter(
                user=self.admin, notification_type='booking_approved',
                is_admin_notification=True,
            ).exists()
        )

    def test_booking_rejected_creates_notifications(self):
        booking = self._create_booking()
        self._login(self.admin)
        self.client.post(f'/api/bookings/{booking.id}/reject/', {
            'rejection_reason': 'Vehicle not available.',
        }, format='json')
        self.assertTrue(
            Notification.objects.filter(
                user=self.customer, notification_type='booking_rejected',
            ).exists()
        )
        self.assertTrue(
            Notification.objects.filter(
                user=self.admin, notification_type='booking_rejected',
                is_admin_notification=True,
            ).exists()
        )

    def test_booking_cancelled_creates_notifications(self):
        booking = self._create_booking()
        self._login(self.customer)
        self.client.post(f'/api/bookings/{booking.id}/cancel/')
        self.assertTrue(
            Notification.objects.filter(
                user=self.customer, notification_type='transaction_completed',
            ).exists()
        )
        self.assertTrue(
            Notification.objects.filter(
                user=self.admin, notification_type='transaction_completed',
                is_admin_notification=True,
            ).exists()
        )

    def test_booking_confirmed_creates_notifications(self):
        booking = self._create_booking()
        booking.status = 'awaiting_payment'
        booking.save()
        self._login(self.admin)
        self.client.post(f'/api/bookings/{booking.id}/confirm/')
        self.assertTrue(
            Notification.objects.filter(
                user=self.customer, notification_type='payment_successful',
            ).exists()
        )
        self.assertTrue(
            Notification.objects.filter(
                user=self.admin, notification_type='payment_successful',
                is_admin_notification=True,
            ).exists()
        )

    def test_mark_waiting_creates_pickup_reminder(self):
        booking = self._create_booking()
        booking.status = 'confirmed'
        booking.save()
        self._login(self.admin)
        self.client.post(f'/api/bookings/{booking.id}/mark-waiting/')
        self.assertTrue(
            Notification.objects.filter(
                user=self.customer, notification_type='pickup_reminder',
            ).exists()
        )

    def test_mark_active_creates_rental_notifications(self):
        booking = self._create_booking()
        booking.status = 'confirmed'
        booking.vehicle_unit = VehicleUnit.objects.first()
        booking.save()
        self._login(self.admin)
        self.client.post(f'/api/bookings/{booking.id}/mark-active/')
        self.assertTrue(
            Notification.objects.filter(
                user=self.customer, notification_type='rental_activated',
            ).exists()
        )
        self.assertTrue(
            Notification.objects.filter(
                user=self.admin, notification_type='rental_activated',
                is_admin_notification=True,
            ).exists()
        )

    def test_mark_complete_creates_notifications(self):
        booking = self._create_booking()
        booking.status = 'active'
        booking.vehicle_unit = VehicleUnit.objects.first()
        booking.vehicle_unit.status = 'active_rental'
        booking.vehicle_unit.save()
        booking.save()
        self._login(self.admin)
        self.client.post(f'/api/bookings/{booking.id}/mark-complete/', {
            'return_unit_status': 'available',
        }, format='json')
        self.assertTrue(
            Notification.objects.filter(
                user=self.customer, notification_type='vehicle_returned',
            ).exists()
        )
        self.assertTrue(
            Notification.objects.filter(
                user=self.admin, notification_type='vehicle_returned',
                is_admin_notification=True,
            ).exists()
        )
        self.assertTrue(
            Notification.objects.filter(
                user=self.customer, notification_type='transaction_completed',
            ).exists()
        )

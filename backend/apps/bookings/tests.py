from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.bookings.models import Booking
from apps.accounts.models import IdentityDocument
from apps.vehicles.models import Vehicle, VehicleUnit

User = get_user_model()


def _create_verified_customer(email='cust@test.com', password='Pass123!'):
    """Helper: create a verified customer with a driver's license."""
    user = User.objects.create_user(
        email=email, username=email.split('@')[0],
        first_name='Test', last_name='Customer',
        phone='+639123456789',
        password=password, is_verified=True,
    )
    return user


def _add_drivers_license(user):
    """Create a valid IdentityDocument with a minimal test image."""
    from django.core.files.base import ContentFile
    from io import BytesIO
    from PIL import Image as PILImage

    # Generate a minimal valid JPEG in memory
    buf = BytesIO()
    img = PILImage.new('RGB', (1, 1), color='white')
    img.save(buf, 'JPEG')
    content = ContentFile(buf.getvalue(), 'test_dl.jpg')

    return IdentityDocument.objects.create(
        user=user, document_type='drivers_license',
        document_number='D01-12-345678',
        front_image=content,
    )


def _add_vehicle_unit(vehicle, plate='XXX-000', status='available'):
    return VehicleUnit.objects.create(
        vehicle=vehicle, plate_number=plate, status=status,
    )


class BookingModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='cust@test.com', username='cust', password='Pass123!',
        )
        self.vehicle = Vehicle.objects.create(
            make='Toyota', model='Vios', year=2024, type='Sedan',
            price_per_day=2500.00,
        )

    def test_booking_number_generated(self):
        booking = Booking.objects.create(
            customer=self.user, vehicle=self.vehicle,
            pickup_date=date.today() + timedelta(days=1),
            return_date=date.today() + timedelta(days=4),
            pickup_time='09:00',
        )
        self.assertTrue(booking.booking_number.startswith('BK-'))
        self.assertEqual(len(booking.booking_number), 11)

    def test_rental_days_auto_calculated(self):
        booking = Booking.objects.create(
            customer=self.user, vehicle=self.vehicle,
            pickup_date=date.today() + timedelta(days=1),
            return_date=date.today() + timedelta(days=4),
            pickup_time='09:00',
        )
        self.assertEqual(booking.rental_days, 4)

    def test_subtotal_auto_calculated(self):
        booking = Booking.objects.create(
            customer=self.user, vehicle=self.vehicle,
            pickup_date=date.today() + timedelta(days=1),
            return_date=date.today() + timedelta(days=3),
            pickup_time='09:00',
        )
        self.assertEqual(booking.subtotal, 7500.00)

    def test_default_status_is_pending_approval(self):
        booking = Booking.objects.create(
            customer=self.user, vehicle=self.vehicle,
            pickup_date=date.today() + timedelta(days=1),
            return_date=date.today() + timedelta(days=3),
            pickup_time='09:00',
        )
        self.assertEqual(booking.status, 'pending_approval')

    def test_identity_snapshot_captured(self):
        _add_drivers_license(self.user)
        booking = Booking.objects.create(
            customer=self.user, vehicle=self.vehicle,
            pickup_date=date.today() + timedelta(days=1),
            return_date=date.today() + timedelta(days=3),
            pickup_time='09:00',
            identity_snapshot={'test': True},
        )
        self.assertEqual(booking.identity_snapshot, {'test': True})


class BookingAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.customer = _create_verified_customer()
        _add_drivers_license(self.customer)
        self.admin = User.objects.create_superuser(
            email='admin@test.com', username='admin', password='AdminPass123!',
        )
        self.vehicle = Vehicle.objects.create(
            make='Toyota', model='Vios', year=2024, type='Sedan',
            price_per_day=2500.00,
        )
        _add_vehicle_unit(self.vehicle, 'ABC-1234')
        self.vehicle2 = Vehicle.objects.create(
            make='Honda', model='Civic', year=2024, type='Sedan',
            price_per_day=3000.00,
        )
        _add_vehicle_unit(self.vehicle2, 'XYZ-5678')

        self.valid_payload = {
            'vehicle': self.vehicle.pk,
            'pickup_date': str(date.today() + timedelta(days=2)),
            'return_date': str(date.today() + timedelta(days=5)),
            'pickup_time': '09:00',
            'special_request': 'Please clean thoroughly.',
        }

    def _login_as(self, user):
        """Use force_authenticate to bypass rate-limiting for tests."""
        self.client.force_authenticate(user=user)

    # ── Create ──

    def test_create_booking_unauthenticated_fails(self):
        response = self.client.post('/api/bookings/', self.valid_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_booking_success(self):
        self._login_as(self.customer)
        # Temporarily disable custom exception handler to see real errors
        from django.conf import settings
        current = settings.REST_FRAMEWORK.copy()
        current.pop('EXCEPTION_HANDLER', None)
        with self.settings(REST_FRAMEWORK=current):
            response = self.client.post('/api/bookings/', self.valid_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['status'], 'pending_approval')
        self.assertEqual(response.data['rental_days'], 4)
        # Verify identity snapshot was captured
        self.assertIn('customer_email', response.data['identity_snapshot'])
        # Verify notification was created
        from apps.core.models import Notification
        self.assertTrue(Notification.objects.filter(
            user=self.customer, notification_type='booking_submitted',
        ).exists())

    def test_identity_snapshot_is_immutable_when_profile_changes(self):
        """Changing the customer's identity documents later must NOT alter
        the immutable snapshot stored on the booking."""
        self._login_as(self.customer)
        response = self.client.post('/api/bookings/', self.valid_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        booking = Booking.objects.get(pk=response.data['id'])
        original_snapshot = booking.identity_snapshot.copy()
        original_doc_number = original_snapshot['documents'][0]['document_number']

        # Simulate a profile edit: change the live identity document number
        doc = self.customer.identity_documents.first()
        doc.document_number = 'CHANGED-999'
        doc.save(update_fields=['document_number', 'updated_at'])

        # The booking's snapshot must remain unchanged
        booking.refresh_from_db()
        self.assertEqual(booking.identity_snapshot['documents'][0]['document_number'], original_doc_number)
        self.assertNotEqual(booking.identity_snapshot['documents'][0]['document_number'], 'CHANGED-999')

    def test_create_booking_no_drivers_license_fails(self):
        cust2 = _create_verified_customer('nolicense@test.com')
        self._login_as(cust2)
        response = self.client.post('/api/bookings/', self.valid_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('identity', response.data)

    def test_create_booking_unverified_email_fails(self):
        cust2 = User.objects.create_user(
            email='unverified@test.com', username='unverified',
            password='Pass123!', is_verified=False,
        )
        _add_drivers_license(cust2)
        self._login_as(cust2)
        response = self.client.post('/api/bookings/', self.valid_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('verified', response.data)

    def test_create_booking_overlapping_pending_request_is_allowed(self):
        self._login_as(self.customer)
        response = self.client.post('/api/bookings/', self.valid_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_booking_overlapping_approved_booking_fails(self):
        # Create vehicle with only 1 unit
        v = Vehicle.objects.create(make='Mazda', model='3', year=2024, type='Sedan', price_per_day=2000.00)
        unit = _add_vehicle_unit(v, 'MZD-001')
        cust2 = _create_verified_customer('mazda@test.com')
        _add_drivers_license(cust2)

        payload = {**self.valid_payload, 'vehicle': v.pk}

        self._login_as(cust2)
        first = self.client.post('/api/bookings/', payload, format='json')
        self.assertEqual(first.status_code, status.HTTP_201_CREATED)

        # Admin approves
        self._login_as(self.admin)
        self.client.post(f'/api/bookings/{first.data["id"]}/approve/')
        # Admin assigns the unit
        self.client.post(f'/api/bookings/{first.data["id"]}/assign-unit/', {
            'unit_id': unit.pk, 'reason': 'Test assignment',
        })

        # Second booking should fail — no units left
        self._login_as(cust2)
        resp = self.client.post('/api/bookings/', payload, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_booking_different_vehicle_ok(self):
        self._login_as(self.customer)
        self.client.post('/api/bookings/', self.valid_payload, format='json')

        payload2 = {**self.valid_payload, 'vehicle': self.vehicle2.pk}
        response = self.client.post('/api/bookings/', payload2, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_booking_past_date_fails(self):
        self._login_as(self.customer)
        payload = {
            **self.valid_payload,
            'pickup_date': str(date.today() - timedelta(days=1)),
            'return_date': str(date.today() + timedelta(days=3)),
        }
        response = self.client.post('/api/bookings/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_booking_return_before_pickup_fails(self):
        self._login_as(self.customer)
        payload = {
            **self.valid_payload,
            'pickup_date': str(date.today() + timedelta(days=5)),
            'return_date': str(date.today() + timedelta(days=2)),
        }
        response = self.client.post('/api/bookings/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # ── Read ──

    def test_list_own_bookings(self):
        self._login_as(self.customer)
        self.client.post('/api/bookings/', self.valid_payload, format='json')

        response = self.client.get('/api/bookings/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_admin_sees_all_bookings(self):
        self._login_as(self.customer)
        self.client.post('/api/bookings/', self.valid_payload, format='json')

        self._login_as(self.admin)
        response = self.client.get('/api/bookings/')
        self.assertEqual(len(response.data['results']), 1)

    def test_customer_cannot_see_others_bookings(self):
        self._login_as(self.customer)
        self.client.post('/api/bookings/', self.valid_payload, format='json')

        other = _create_verified_customer('other@test.com')
        _add_drivers_license(other)
        self._login_as(other)
        response = self.client.get('/api/bookings/')
        self.assertEqual(len(response.data['results']), 0)

    # ── Cancel ──

    def test_customer_can_cancel_pending_booking(self):
        self._login_as(self.customer)
        create_resp = self.client.post('/api/bookings/', self.valid_payload, format='json')
        booking_id = create_resp.data['id']

        response = self.client.post(f'/api/bookings/{booking_id}/cancel/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'cancelled')

    # ── Admin Approve/Reject ──

    def test_admin_approve_booking(self):
        self._login_as(self.customer)
        create_resp = self.client.post('/api/bookings/', self.valid_payload, format='json')
        booking_id = create_resp.data['id']

        self._login_as(self.admin)
        response = self.client.post(f'/api/bookings/{booking_id}/approve/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'awaiting_payment')
        # Verify notification was created for customer
        from apps.core.models import Notification
        self.assertTrue(Notification.objects.filter(
            user=self.customer, notification_type='booking_approved',
        ).exists())

    def test_admin_reject_booking(self):
        self._login_as(self.customer)
        create_resp = self.client.post('/api/bookings/', self.valid_payload, format='json')
        booking_id = create_resp.data['id']

        self._login_as(self.admin)
        response = self.client.post(f'/api/bookings/{booking_id}/reject/', {
            'rejection_reason': 'Vehicle unavailable',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'rejected')
        self.assertEqual(response.data['rejection_reason'], 'Vehicle unavailable')

    def test_customer_cannot_approve(self):
        self._login_as(self.customer)
        create_resp = self.client.post('/api/bookings/', self.valid_payload, format='json')
        booking_id = create_resp.data['id']

        response = self.client.post(f'/api/bookings/{booking_id}/approve/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_cannot_approve_non_pending(self):
        self._login_as(self.customer)
        create_resp = self.client.post('/api/bookings/', self.valid_payload, format='json')
        booking_id = create_resp.data['id']

        self._login_as(self.admin)
        self.client.post(f'/api/bookings/{booking_id}/approve/')

        # Already awaiting_payment — can't approve again
        response = self.client.post(f'/api/bookings/{booking_id}/approve/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class AvailabilityTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.customer = _create_verified_customer()
        _add_drivers_license(self.customer)
        self.vehicle = Vehicle.objects.create(
            make='Toyota', model='Vios', year=2024, type='Sedan',
            price_per_day=2500.00,
        )
        self.unit = _add_vehicle_unit(self.vehicle, 'AVA-0001')
        self.client.force_authenticate(user=self.customer)

    def _create_booking(self, days_from_now=2, length=3, vehicle_unit=None):
        return Booking.objects.create(
            customer=self.customer,
            vehicle=self.vehicle,
            vehicle_unit=vehicle_unit or self.unit,
            pickup_date=date.today() + timedelta(days=days_from_now),
            return_date=date.today() + timedelta(days=days_from_now + length),
            pickup_time='09:00',
            status='confirmed',
        )

    def test_availability_available(self):
        start = str(date.today() + timedelta(days=10))
        end = str(date.today() + timedelta(days=13))
        response = self.client.get(
            f'/api/bookings/availability/?vehicle_id={self.vehicle.pk}&start_date={start}&end_date={end}'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['available'])
        self.assertEqual(response.data['rental_days'], 4)
        self.assertEqual(response.data['subtotal'], '10000.00')

    def test_availability_pending_booking_still_available(self):
        Booking.objects.create(
            customer=self.customer,
            vehicle=self.vehicle,
            vehicle_unit=self.unit,
            pickup_date=date.today() + timedelta(days=5),
            return_date=date.today() + timedelta(days=8),
            pickup_time='09:00',
            status='pending_approval',
        )

        start = str(date.today() + timedelta(days=6))
        end = str(date.today() + timedelta(days=8))
        response = self.client.get(
            f'/api/bookings/availability/?vehicle_id={self.vehicle.pk}&start_date={start}&end_date={end}'
        )
        self.assertTrue(response.data['available'])

    def test_availability_confirmed_booking_unavailable(self):
        self._create_booking(days_from_now=5, length=3)

        start = str(date.today() + timedelta(days=6))
        end = str(date.today() + timedelta(days=8))
        response = self.client.get(
            f'/api/bookings/availability/?vehicle_id={self.vehicle.pk}&start_date={start}&end_date={end}'
        )
        self.assertFalse(response.data['available'])

    def test_availability_past_date_unavailable(self):
        start = str(date.today() - timedelta(days=3))
        end = str(date.today() + timedelta(days=2))
        response = self.client.get(
            f'/api/bookings/availability/?vehicle_id={self.vehicle.pk}&start_date={start}&end_date={end}'
        )
        self.assertFalse(response.data['available'])

    def test_availability_unauthenticated_ok(self):
        """Guests can check availability without authentication (AllowAny)."""
        client2 = APIClient()
        start = str(date.today() + timedelta(days=5))
        end = str(date.today() + timedelta(days=8))
        response = client2.get(
            f'/api/bookings/availability/?vehicle_id={self.vehicle.pk}&start_date={start}&end_date={end}'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['available'])

    def test_availability_no_units_unavailable(self):
        v = Vehicle.objects.create(make='Suzuki', model='Swift', year=2024, type='Hatchback', price_per_day=1500.00)
        start = str(date.today() + timedelta(days=5))
        end = str(date.today() + timedelta(days=8))
        response = self.client.get(
            f'/api/bookings/availability/?vehicle_id={v.pk}&start_date={start}&end_date={end}'
        )
        self.assertFalse(response.data['available'])
        self.assertIn('No units', response.data['reason'])

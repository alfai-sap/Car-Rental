from datetime import date, timedelta
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from apps.bookings.models import Booking
from apps.vehicles.models import Vehicle

User = get_user_model()


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
        self.assertEqual(booking.rental_days, 4)  # inclusive: 1,2,3,4 = 4 days

    def test_subtotal_auto_calculated(self):
        booking = Booking.objects.create(
            customer=self.user, vehicle=self.vehicle,
            pickup_date=date.today() + timedelta(days=1),
            return_date=date.today() + timedelta(days=3),
            pickup_time='09:00',
        )
        self.assertEqual(booking.subtotal, 7500.00)  # 2500 * 3 days

    def test_default_status_is_pending_approval(self):
        booking = Booking.objects.create(
            customer=self.user, vehicle=self.vehicle,
            pickup_date=date.today() + timedelta(days=1),
            return_date=date.today() + timedelta(days=3),
            pickup_time='09:00',
        )
        self.assertEqual(booking.status, 'pending_approval')


class BookingAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.customer = User.objects.create_user(
            email='cust@test.com', username='cust', password='Pass123!',
        )
        self.admin = User.objects.create_superuser(
            email='admin@test.com', username='admin', password='AdminPass123!',
        )
        self.vehicle = Vehicle.objects.create(
            make='Toyota', model='Vios', year=2024, type='Sedan',
            price_per_day=2500.00,
        )
        self.vehicle2 = Vehicle.objects.create(
            make='Honda', model='Civic', year=2024, type='Sedan',
            price_per_day=3000.00,
        )

        self.valid_payload = {
            'vehicle': None,  # set in each test
            'pickup_date': str(date.today() + timedelta(days=2)),
            'return_date': str(date.today() + timedelta(days=5)),
            'pickup_time': '09:00',
            'special_request': 'Please clean thoroughly.',
        }
        self.valid_payload['vehicle'] = self.vehicle.pk

    def _login(self, email, password):
        resp = self.client.post('/api/auth/login/', {
            'email': email, 'password': password,
        }, format='json')
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {resp.data['access']}")

    # ── Create ──

    def test_create_booking_unauthenticated_fails(self):
        response = self.client.post('/api/bookings/', self.valid_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_booking_success(self):
        self._login('cust@test.com', 'Pass123!')
        response = self.client.post('/api/bookings/', self.valid_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['status'], 'pending_approval')
        self.assertEqual(response.data['rental_days'], 4)  # inclusive: days 2,3,4,5 = 4

    def test_create_booking_overlapping_fails(self):
        self._login('cust@test.com', 'Pass123!')
        self.client.post('/api/bookings/', self.valid_payload, format='json')

        # Overlapping — move start 1 day forward into the booked range
        response = self.client.post('/api/bookings/', self.valid_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_booking_different_vehicle_ok(self):
        self._login('cust@test.com', 'Pass123!')
        self.client.post('/api/bookings/', self.valid_payload, format='json')

        # Same dates, different vehicle
        payload2 = {**self.valid_payload, 'vehicle': self.vehicle2.pk}
        response = self.client.post('/api/bookings/', payload2, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_booking_past_date_fails(self):
        self._login('cust@test.com', 'Pass123!')
        payload = {
            **self.valid_payload,
            'pickup_date': str(date.today() - timedelta(days=1)),
            'return_date': str(date.today() + timedelta(days=3)),
        }
        response = self.client.post('/api/bookings/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_booking_return_before_pickup_fails(self):
        self._login('cust@test.com', 'Pass123!')
        payload = {
            **self.valid_payload,
            'pickup_date': str(date.today() + timedelta(days=5)),
            'return_date': str(date.today() + timedelta(days=2)),
        }
        response = self.client.post('/api/bookings/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # ── Read ──

    def test_list_own_bookings(self):
        self._login('cust@test.com', 'Pass123!')
        self.client.post('/api/bookings/', self.valid_payload, format='json')

        response = self.client.get('/api/bookings/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_admin_sees_all_bookings(self):
        self._login('cust@test.com', 'Pass123!')
        self.client.post('/api/bookings/', self.valid_payload, format='json')

        self._login('admin@test.com', 'AdminPass123!')
        response = self.client.get('/api/bookings/')
        self.assertEqual(len(response.data['results']), 1)

    def test_customer_cannot_see_others_bookings(self):
        self._login('cust@test.com', 'Pass123!')
        self.client.post('/api/bookings/', self.valid_payload, format='json')

        other = User.objects.create_user(email='other@test.com', username='other', password='Pass123!')
        self._login('other@test.com', 'Pass123!')
        response = self.client.get('/api/bookings/')
        self.assertEqual(len(response.data['results']), 0)

    # ── Cancel ──

    def test_customer_can_cancel_pending_booking(self):
        self._login('cust@test.com', 'Pass123!')
        create_resp = self.client.post('/api/bookings/', self.valid_payload, format='json')
        booking_id = create_resp.data['id']

        response = self.client.post(f'/api/bookings/{booking_id}/cancel/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'cancelled')

    # ── Admin Approve/Reject ──

    def test_admin_approve_booking(self):
        self._login('cust@test.com', 'Pass123!')
        create_resp = self.client.post('/api/bookings/', self.valid_payload, format='json')
        booking_id = create_resp.data['id']

        self._login('admin@test.com', 'AdminPass123!')
        response = self.client.post(f'/api/bookings/{booking_id}/approve/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'approved')

    def test_admin_reject_booking(self):
        self._login('cust@test.com', 'Pass123!')
        create_resp = self.client.post('/api/bookings/', self.valid_payload, format='json')
        booking_id = create_resp.data['id']

        self._login('admin@test.com', 'AdminPass123!')
        response = self.client.post(f'/api/bookings/{booking_id}/reject/', {
            'rejection_reason': 'Vehicle unavailable',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'rejected')
        self.assertEqual(response.data['rejection_reason'], 'Vehicle unavailable')

    def test_customer_cannot_approve(self):
        self._login('cust@test.com', 'Pass123!')
        create_resp = self.client.post('/api/bookings/', self.valid_payload, format='json')
        booking_id = create_resp.data['id']

        response = self.client.post(f'/api/bookings/{booking_id}/approve/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_cannot_approve_non_pending(self):
        self._login('cust@test.com', 'Pass123!')
        create_resp = self.client.post('/api/bookings/', self.valid_payload, format='json')
        booking_id = create_resp.data['id']

        self._login('admin@test.com', 'AdminPass123!')
        self.client.post(f'/api/bookings/{booking_id}/approve/')

        # Already approved — can't approve again
        response = self.client.post(f'/api/bookings/{booking_id}/approve/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class AvailabilityTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.customer = User.objects.create_user(
            email='cust@test.com', username='cust', password='Pass123!',
        )
        self.vehicle = Vehicle.objects.create(
            make='Toyota', model='Vios', year=2024, type='Sedan',
            price_per_day=2500.00,
        )
        self._login()

    def _login(self):
        resp = self.client.post('/api/auth/login/', {
            'email': 'cust@test.com', 'password': 'Pass123!',
        }, format='json')
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {resp.data['access']}")

    def _create_booking(self, days_from_now=2, length=3):
        return Booking.objects.create(
            customer=self.customer,
            vehicle=self.vehicle,
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
        self.assertEqual(response.data['rental_days'], 4)  # inclusive: 10,11,12,13
        self.assertEqual(response.data['subtotal'], '10000.00')  # 2500 * 4

    def test_availability_overlapping_unavailable(self):
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

    def test_availability_unauthenticated_fails(self):
        client2 = APIClient()
        start = str(date.today() + timedelta(days=5))
        end = str(date.today() + timedelta(days=8))
        response = client2.get(
            f'/api/bookings/availability/?vehicle_id={self.vehicle.pk}&start_date={start}&end_date={end}'
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

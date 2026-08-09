from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.bookings.models import Booking
from apps.payments.models import Invoice, Payment
from apps.vehicles.models import Vehicle

User = get_user_model()


class PaymentAPITests(TestCase):
	def setUp(self):
		self.client = APIClient()
		self.customer = User.objects.create_user(
			email='customer@example.com',
			username='customer',
			password='StrongPass123!',
		)
		self.admin = User.objects.create_user(
			email='admin@example.com',
			username='admin',
			password='AdminPass123!',
			is_staff=True,
		)
		self.vehicle = Vehicle.objects.create(
			make='Toyota',
			model='Vios',
			year=2024,
			type='Sedan',
			transmission='automatic',
			fuel='gasoline',
			seats=5,
			price_per_day=1500,
			status='available',
		)
		self.booking = Booking.objects.create(
			customer=self.customer,
			vehicle=self.vehicle,
			pickup_date=timezone.now().date() + timedelta(days=2),
			return_date=timezone.now().date() + timedelta(days=4),
			pickup_time='09:00',
			return_time='17:00',
			rental_days=3,
			subtotal=4500,
			estimated_total=4500,
			status='approved',
		)

	def _login(self, user):
		self.client.force_authenticate(user=user)

	def test_create_session_creates_invoice_and_payment_record(self):
		self._login(self.customer)

		response = self.client.post('/api/payments/create-session/', {'booking_id': self.booking.id}, format='json')

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(response.data['payment']['payment_status'], 'pending')
		self.assertIsNone(response.data['checkout_url'])
		self.assertTrue(Invoice.objects.filter(booking=self.booking).exists())
		self.assertEqual(Payment.objects.filter(booking=self.booking).count(), 1)

	def test_payment_history_restricted_to_owner(self):
		self._login(self.customer)
		self.client.post('/api/payments/create-session/', {'booking_id': self.booking.id}, format='json')

		response = self.client.get('/api/payments/history/')
		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(len(response.data), 1)

	def test_payment_detail_authorization(self):
		self._login(self.customer)
		create_resp = self.client.post('/api/payments/create-session/', {'booking_id': self.booking.id}, format='json')
		payment_id = create_resp.data['payment']['id']

		self._login(self.admin)
		response = self.client.get(f'/api/payments/{payment_id}/')
		self.assertEqual(response.status_code, status.HTTP_200_OK)

	def test_webhook_returns_service_unavailable_without_provider(self):
		self._login(self.customer)
		self.client.post('/api/payments/create-session/', {'booking_id': self.booking.id}, format='json')

		response = self.client.post('/api/payments/webhook/', {
			'payment_number': Payment.objects.first().payment_number,
			'status': 'paid',
		}, format='json')

		self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)

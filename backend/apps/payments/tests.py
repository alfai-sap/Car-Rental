import hashlib
import hmac
import json
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.bookings.models import Booking
from apps.core.models import Notification
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

	def test_invoice_records_booking_discount(self):
		"""Regression: the invoice must carry the booking's discount snapshot,
		not a hardcoded zero, so the customer is charged the discounted total."""
		self.booking.discount_amount = 450
		self.booking.discount_percent = 10
		self.booking.estimated_total = 4050
		self.booking.save(update_fields=['discount_amount', 'discount_percent', 'estimated_total', 'updated_at'])

		self._login(self.customer)
		response = self.client.post('/api/payments/create-session/', {'booking_id': self.booking.id}, format='json')
		self.assertEqual(response.status_code, status.HTTP_200_OK)

		invoice = Invoice.objects.get(booking=self.booking)
		self.assertEqual(invoice.subtotal, 4500)
		self.assertEqual(invoice.discount, 450)
		self.assertEqual(invoice.total, 4050)

		payment = Payment.objects.filter(booking=self.booking).latest('id')
		self.assertEqual(payment.amount, 4050)

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

	def _signed_webhook(self, event_data):
		"""Build a signed PayMongo webhook payload using the test secret.

		Signs the body exactly as DRF's JSONRenderer will serialize it
		(compact separators), so the server-side HMAC matches.
		"""
		ts = int(timezone.now().timestamp())
		expiry = ts + 60
		body = json.dumps(event_data, separators=(',', ':')).encode()
		signed = f'{ts}.{expiry}.{body.decode()}'.encode()
		li = hmac.new(b'test-webhook-secret', signed, hashlib.sha256).hexdigest()
		return event_data, {'HTTP_PAYMONGO_SIGNATURE': f't={ts},te={expiry},li={li}'}

	def test_webhook_payment_for_cancelled_booking_notifies_support(self):
		"""A payment landing on a cancelled booking must NOT send a
		'Booking Finalized' email — it should alert support instead."""
		invoice = Invoice.objects.create(
			booking=self.booking,
			subtotal=self.booking.estimated_total,
			discount=0,
			total=self.booking.estimated_total,
			invoice_status=Invoice.STATUS_PENDING,
		)
		payment = Payment.objects.create(
			booking=self.booking,
			invoice=invoice,
			provider=Payment.PROVIDER_PAYMONGO,
			provider_reference='pay_123',
			amount=invoice.total,
			currency='PHP',
			payment_status=Payment.STATUS_PENDING,
		)

		# Cancel the booking after the customer is redirected to PayMongo.
		self.booking.status = 'cancelled'
		self.booking.save(update_fields=['status', 'updated_at'])

		event_data = {
			'data': {
				'id': 'evt_123',
				'attributes': {
					'type': 'payment.paid',
					'data': {
						'id': 'pay_123',
						'attributes': {
							'amount': int(payment.invoice.total * 100),
							'currency': 'PHP',
							'source': {'type': 'gcash'},
						},
					},
				},
			},
		}
		event_data, headers = self._signed_webhook(event_data)
		mail.outbox = []
		with override_settings(
			PAYMENT_PROVIDER='paymongo',
			PAYMONGO_PUBLIC_KEY='pk_test',
			PAYMONGO_SECRET_KEY='sk_test',
			PAYMONGO_WEBHOOK_SECRET='test-webhook-secret',
		):
			response = self.client.post(
				'/api/payments/webhook/',
				event_data,
				format='json',
				**headers,
			)

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.booking.refresh_from_db()
		# The cancelled booking must never be resurrected.
		self.assertEqual(self.booking.status, 'cancelled')
		# No "Booking Finalized" email is sent.
		self.assertEqual(len(mail.outbox), 0)
		# The customer is alerted and staff are notified to review.
		self.assertTrue(Notification.objects.filter(
			user=self.customer, title='Payment Received — Booking Not Active',
		).exists())
		self.assertTrue(Notification.objects.filter(
			is_admin_notification=True,
			title__startswith='Payment Received for Inactive Booking:',
		).exists())

	def test_pending_payment_checkout_is_reused(self):
		"""A still-pending payment keeps its live checkout URL on re-attempt."""
		self._login(self.customer)
		first = self.client.post('/api/payments/create-session/', {'booking_id': self.booking.id}, format='json')
		self.assertEqual(first.status_code, status.HTTP_200_OK)

		# Simulate a live checkout URL on the pending payment (gateway disabled
		# in tests, so checkout_url is normally None).
		payment = Payment.objects.get(booking=self.booking)
		payment.checkout_url = 'https://paymongo.com/checkout/live'
		payment.save(update_fields=['checkout_url', 'updated_at'])

		second = self.client.post('/api/payments/create-session/', {'booking_id': self.booking.id}, format='json')
		self.assertEqual(second.status_code, status.HTTP_200_OK)
		# No new Payment record is created for a reused pending checkout.
		self.assertEqual(Payment.objects.filter(booking=self.booking).count(), 1)
		self.assertEqual(second.data['checkout_url'], 'https://paymongo.com/checkout/live')

	def test_expired_payment_gets_fresh_session(self):
		"""An expired payment must NOT reuse its dead checkout URL.

		Regression: after a payment expires, retrying checkout must produce a
		brand-new payment/session instead of the expired one's dead URL.
		"""
		self._login(self.customer)
		first = self.client.post('/api/payments/create-session/', {'booking_id': self.booking.id}, format='json')
		self.assertEqual(first.status_code, status.HTTP_200_OK)

		# Mark the original payment as expired (with a stale checkout URL).
		payment = Payment.objects.get(booking=self.booking)
		payment.payment_status = Payment.STATUS_EXPIRED
		payment.checkout_url = 'https://paymongo.com/checkout/dead'
		payment.save(update_fields=['payment_status', 'checkout_url', 'updated_at'])

		second = self.client.post('/api/payments/create-session/', {'booking_id': self.booking.id}, format='json')
		self.assertEqual(second.status_code, status.HTTP_200_OK)
		# A fresh pending Payment record must be created.
		self.assertEqual(Payment.objects.filter(booking=self.booking).count(), 2)
		new_payment = Payment.objects.filter(booking=self.booking).latest('id')
		self.assertEqual(new_payment.payment_status, Payment.STATUS_PENDING)
		# The new session must not carry over the expired checkout URL.
		self.assertNotEqual(second.data['payment']['id'], payment.id)

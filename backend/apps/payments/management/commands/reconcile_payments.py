"""
Reconcile pending PayMongo payments against the gateway.

Webhooks are the primary signal for payment state changes, but they can be
missed (network failure, app downtime, replay windows).  This command queries
PayMongo directly for every still-pending payment and applies the result,
catching any `payment.paid` event that was never delivered.

Usage:
    python manage.py reconcile_payments

Schedule it periodically (e.g. every few minutes via cron) in production.
"""
from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.payments.models import Payment
from apps.payments.paymongo import PayMongoError, retrieve_payment
from apps.payments.views import PaymentAmountMismatchError, finalize_paid_payment, payment_gateway_enabled


class Command(BaseCommand):
    help = 'Reconcile pending PayMongo payments by querying the gateway.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--older-than-minutes',
            type=int,
            default=5,
            help='Only reconcile payments created more than N minutes ago '
                 '(default: 5). Gives the webhook time to arrive first.',
        )

    def handle(self, *args, **options):
        if not payment_gateway_enabled():
            self.stdout.write(self.style.WARNING(
                'Payment gateway is not configured. Nothing to reconcile.'
            ))
            return

        cutoff = timezone.now() - timedelta(minutes=options['older_than_minutes'])
        pending = Payment.objects.filter(
            provider=Payment.PROVIDER_PAYMONGO,
            payment_status=Payment.STATUS_PENDING,
            provider_reference__gt='',
            created_at__lt=cutoff,
        ).select_related('booking', 'invoice', 'booking__vehicle_unit')

        if not pending.exists():
            self.stdout.write('No pending payments to reconcile.')
            return

        self.stdout.write(f'Reconciling {pending.count()} pending payment(s)...')

        updated = 0
        for payment in pending:
            try:
                attrs = retrieve_payment(payment.provider_reference)
            except PayMongoError as exc:
                # Non-200 or unreachable gateway — log and continue.  A future
                # run will retry this payment.
                self.stderr.write(
                    f'  {payment.payment_number}: retrieval failed ({exc})'
                )
                continue

            status = (attrs.get('status') or '').lower()
            amount_cents = attrs.get('amount')
            currency = (attrs.get('currency') or '').upper()
            payment_method = attrs.get('source', {}).get('type', '')

            if status == 'paid':
                try:
                    finalize_paid_payment(
                        payment,
                        amount_cents=amount_cents,
                        currency=currency,
                        payment_method=payment_method,
                    )
                except PaymentAmountMismatchError as exc:
                    # Do not silently resolve a mismatched payment.  Leave it
                    # pending and surface it for a human to review.
                    self.stderr.write(
                        self.style.ERROR(
                            f'  {payment.payment_number}: amount mismatch ({exc}); '
                            f'left pending for manual review.'
                        )
                    )
                    continue
                updated += 1
                self.stdout.write(self.style.SUCCESS(
                    f'  {payment.payment_number}: reconciled as paid'
                ))
            elif status == 'failed':
                payment.payment_status = Payment.STATUS_FAILED
                payment.save(update_fields=['payment_status', 'updated_at'])
                updated += 1
                self.stdout.write(f'  {payment.payment_number}: reconciled as failed')
            elif status == 'expired':
                payment.payment_status = Payment.STATUS_EXPIRED
                payment.save(update_fields=['payment_status', 'updated_at'])
                updated += 1
                self.stdout.write(f'  {payment.payment_number}: reconciled as expired')
            else:
                self.stdout.write(
                    f'  {payment.payment_number}: gateway status "{status}" — no local change'
                )

        self.stdout.write(self.style.SUCCESS(f'Reconciliation complete ({updated} payment(s) updated).'))

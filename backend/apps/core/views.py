from decimal import Decimal

from django.db import connections, models, transaction
from django.db.models import Q
from django.db.utils import OperationalError
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters as drf_filters

from apps.core.models import AuditLog, RentalDiscountPolicy, DiscountTier
from apps.core.ids import encode_id


@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    db_status = 'ok'
    try:
        connections['default'].cursor()
    except OperationalError:
        db_status = 'unreachable'

    return Response({
        'status': 'ok' if db_status == 'ok' else 'degraded',
        'database': db_status,
    })


class AuditLogListView(APIView):
    """Paginated, filterable list of all audit log entries.

    Staff-only. Supports:
      - ?action=booking_approved,payment_confirmed,...  (comma-separated)
      - ?booking=123  (filter by booking ID)
      - ?actor=5   (filter by admin user ID)
      - ?search=ABC-123  (search booking number, admin email, summary)
      - ?page=1&page_size=20  (pagination)
    """
    permission_classes = [IsAuthenticated]

    ACTION_FILTERS = [
        'booking_approved', 'booking_rejected', 'payment_confirmed',
        'rental_activated', 'rental_completed', 'unit_assigned',
        'unit_changed', 'booking_cancelled', 'booking_marked_waiting',
    ]

    def get(self, request):
        if not request.user.is_staff:
            return Response({'detail': 'Not authorized.'}, status=status.HTTP_403_FORBIDDEN)

        qs = AuditLog.objects.select_related(
            'actor', 'booking', 'payment',
        ).order_by('-created_at')

        # ── Filters ──
        action_param = request.query_params.get('action', '')
        if action_param:
            actions = [a.strip() for a in action_param.split(',') if a.strip() in self.ACTION_FILTERS]
            if actions:
                qs = qs.filter(action__in=actions)

        booking_id = request.query_params.get('booking', '')
        if booking_id and booking_id.isdigit():
            qs = qs.filter(booking_id=int(booking_id))

        actor_id = request.query_params.get('actor', '')
        if actor_id and actor_id.isdigit():
            qs = qs.filter(actor_id=int(actor_id))

        search = request.query_params.get('search', '').strip()
        if search:
            qs = qs.filter(
                Q(summary__icontains=search)
                | Q(actor__email__icontains=search)
                | Q(booking__booking_number__icontains=search)
            )

        # ── Pagination ──
        try:
            page = int(request.query_params.get('page', 1))
        except (ValueError, TypeError):
            page = 1
        page = max(1, page)

        try:
            page_size = int(request.query_params.get('page_size', 20))
        except (ValueError, TypeError):
            page_size = 20
        page_size = max(1, min(page_size, 100))

        total = qs.count()
        total_pages = max(1, (total + page_size - 1) // page_size)
        offset = (page - 1) * page_size
        logs = qs[offset:offset + page_size]

        # ── Action stats for summary bar ──
        from django.db.models import Count
        stats_qs = qs.values('action').annotate(count=Count('id'))
        action_stats = {item['action']: item['count'] for item in stats_qs}

        data = []
        for log in logs:
            data.append({
                'id': log.id,
                'action': log.action,
                'action_display': log.get_action_display(),
                'summary': log.summary,
                'actor': {
                    'id': log.actor_id,
                    'name': f'{log.actor.first_name} {log.actor.last_name}'.strip() or log.actor.email,
                    'email': log.actor.email,
                },
                'booking': {
                    'id': log.booking_id,
                    'hash_id': encode_id('booking', log.booking_id) if log.booking_id else None,
                    'booking_number': log.booking.booking_number if log.booking else None,
                } if log.booking_id else None,
                'payment': {
                    'id': log.payment_id,
                    'payment_number': log.payment.payment_number if log.payment else None,
                } if log.payment_id else None,
                'before_state': log.before_state,
                'after_state': log.after_state,
                'ip_address': log.ip_address,
                'created_at': log.created_at.isoformat(),
            })

        return Response({
            'count': total,
            'page': page,
            'page_size': page_size,
            'total_pages': total_pages,
            'action_stats': action_stats,
            'results': data,
        })


class RentalDiscountPolicyView(APIView):
    """Admin CRUD for the global rental discount policy.

    Staff-only.  The fleet-wide default policy (with its duration tiers) is
    managed here.  A policy marked `is_default` becomes the policy all
    vehicles follow unless a vehicle has an explicit override.
    """
    permission_classes = [IsAuthenticated]

    def _serialize_policy(self, policy):
        return {
            'id': policy.id,
            'name': policy.name,
            'description': policy.description,
            'is_default': policy.is_default,
            'tiers': [
                {
                    'id': tier.id,
                    'min_days': tier.min_days,
                    'discount_percent': str(tier.discount_percent),
                }
                for tier in policy.tiers.all()
            ],
            'created_at': policy.created_at.isoformat(),
            'updated_at': policy.updated_at.isoformat(),
        }

    def get(self, request):
        if not request.user.is_staff:
            return Response({'detail': 'Not authorized.'}, status=status.HTTP_403_FORBIDDEN)

        policies = RentalDiscountPolicy.objects.prefetch_related('tiers').all()
        return Response({
            'default_policy_id': (
                RentalDiscountPolicy.get_default().id
                if RentalDiscountPolicy.get_default() else None
            ),
            'policies': [self._serialize_policy(p) for p in policies],
        })

    def post(self, request):
        """Create or update a policy, replacing its tiers atomically."""
        if not request.user.is_staff:
            return Response({'detail': 'Not authorized.'}, status=status.HTTP_403_FORBIDDEN)

        policy_id = request.data.get('id')
        name = (request.data.get('name') or '').strip()
        description = (request.data.get('description') or '').strip()
        is_default = bool(request.data.get('is_default', False))
        tiers_data = request.data.get('tiers') or []

        if not name:
            return Response({'name': 'Policy name is required.'}, status=status.HTTP_400_BAD_REQUEST)

        # Validate and normalize tiers
        normalized_tiers = []
        seen_min_days = set()
        for tier in tiers_data:
            try:
                min_days = int(tier.get('min_days', 1))
                percent = Decimal(str(tier.get('discount_percent', 0)))
            except (TypeError, ValueError):
                return Response(
                    {'tiers': 'Each tier requires a valid min_days and discount_percent.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if min_days < 1:
                return Response({'tiers': 'min_days must be at least 1.'}, status=status.HTTP_400_BAD_REQUEST)
            if percent < 0 or percent > 100:
                return Response({'tiers': 'discount_percent must be between 0 and 100.'}, status=status.HTTP_400_BAD_REQUEST)
            if min_days in seen_min_days:
                return Response({'tiers': f'Duplicate min_days value: {min_days}.'}, status=status.HTTP_400_BAD_REQUEST)
            seen_min_days.add(min_days)
            normalized_tiers.append({'min_days': min_days, 'discount_percent': percent})

        if not normalized_tiers:
            return Response({'tiers': 'At least one tier is required.'}, status=status.HTTP_400_BAD_REQUEST)

        # Ensure a 0% base tier exists for short rentals
        if not any(t['min_days'] == 1 for t in normalized_tiers):
            normalized_tiers.insert(0, {'min_days': 1, 'discount_percent': Decimal('0')})

        with transaction.atomic():
            if policy_id:
                policy = get_object_or_404(RentalDiscountPolicy, pk=policy_id)
                policy.name = name
                policy.description = description
                policy.is_default = is_default
                policy.save()
            else:
                policy = RentalDiscountPolicy.objects.create(
                    name=name,
                    description=description,
                    is_default=is_default,
                )

            # Replace tiers
            policy.tiers.all().delete()
            DiscountTier.objects.bulk_create([
                DiscountTier(
                    policy=policy,
                    min_days=t['min_days'],
                    discount_percent=t['discount_percent'],
                )
                for t in normalized_tiers
            ])

        return Response(self._serialize_policy(policy), status=status.HTTP_201_CREATED if not policy_id else status.HTTP_200_OK)

    def delete(self, request):
        """Delete a policy by id (cannot delete the default policy)."""
        if not request.user.is_staff:
            return Response({'detail': 'Not authorized.'}, status=status.HTTP_403_FORBIDDEN)

        policy_id = request.data.get('id')
        if not policy_id:
            return Response({'id': 'Policy id is required.'}, status=status.HTTP_400_BAD_REQUEST)

        policy = get_object_or_404(RentalDiscountPolicy, pk=policy_id)
        if policy.is_default:
            return Response(
                {'detail': 'The default policy cannot be deleted. Mark another policy as default first.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        policy.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class PublicDiscountPolicyView(APIView):
    """Public read-only view of the active global discount policy.

    Used by the customer-facing pricing UI so discounts are transparent.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        default = RentalDiscountPolicy.get_default()
        if not default:
            return Response({'configured': False})

        return Response({
            'configured': True,
            'name': default.name,
            'tiers': [
                {
                    'min_days': tier.min_days,
                    'discount_percent': str(tier.discount_percent),
                }
                for tier in default.tiers.all()
            ],
        })


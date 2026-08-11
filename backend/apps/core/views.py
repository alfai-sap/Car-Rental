from django.db import connections, models
from django.db.models import Q
from django.db.utils import OperationalError
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters as drf_filters

from apps.core.models import AuditLog


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


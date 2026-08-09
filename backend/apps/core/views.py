from django.db import connections
from django.db.utils import OperationalError
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


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


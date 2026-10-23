from django.db import connection
from django.db.utils import OperationalError
from drf_spectacular.utils import extend_schema

from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView


class HealthView(APIView):
    """Readiness probe: verifica la API y la conexion a la base de datos."""

    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = []  # los health checks no gastan rate limit

    @extend_schema(exclude=True)
    def get(self, request):
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
        except OperationalError:
            return Response(
                {"status": "error", "database": "down"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response({"status": "ok", "database": "up"})

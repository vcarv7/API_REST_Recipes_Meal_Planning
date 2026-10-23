import hashlib
import json
from datetime import timedelta

from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response

from apps.core.models import IdempotencyRecord

# Una reserva "processing" mas vieja que esto se considera abandonada (el
# worker murio entre reservar y completar): se reclama y se permite reintentar.
PROCESSING_TIMEOUT_SECONDS = 120


class IdempotentCreateMixin:
    """POST idempotente mediante el header ``Idempotency-Key``.

    Reserva la key ANTES de crear (claim-then-execute): si dos requests
    simultaneos usan la misma key, solo uno crea; el otro recibe 409 con
    Retry-After y, al reintentar, el replay de la respuesta original.

    Sin header: comportamiento normal. Misma key con payload distinto: 422.
    """

    def create(self, request, *args, **kwargs):
        key = request.headers.get("Idempotency-Key")
        if not key or len(key) > 255:
            return super().create(request, *args, **kwargs)

        fingerprint = hashlib.sha256(
            json.dumps(
                {"path": request.path, "body": request.data},
                sort_keys=True,
                default=str,
            ).encode()
        ).hexdigest()

        record = IdempotencyRecord.objects.filter(user=request.user, key=key).first()
        resolved = self._resolve_existing(record, fingerprint)
        if resolved is not None:
            return resolved

        try:
            with transaction.atomic():
                reservation = IdempotencyRecord.objects.create(
                    user=request.user,
                    key=key,
                    fingerprint=fingerprint,
                    state=IdempotencyRecord.State.PROCESSING,
                )
        except IntegrityError:
            # Otro request gano la carrera entre la lectura y la reserva.
            record = IdempotencyRecord.objects.filter(user=request.user, key=key).first()
            resolved = self._resolve_existing(record, fingerprint)
            if resolved is not None:
                return resolved
            return self._in_progress_response()

        try:
            response = super().create(request, *args, **kwargs)
        except Exception:
            reservation.delete()
            raise

        if response.status_code >= 500:
            reservation.delete()
            return response

        reservation.status_code = response.status_code
        reservation.response_body = response.data
        reservation.state = IdempotencyRecord.State.COMPLETED
        reservation.save(update_fields=["status_code", "response_body", "state"])
        return response

    def _resolve_existing(self, record, fingerprint):
        """Resuelve un recibo existente: replay, 422, 409 o None (reclamar)."""
        if record is None:
            return None
        if record.fingerprint != fingerprint:
            return Response(
                {"detail": "Idempotency-Key reutilizada con un payload distinto."},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        if record.state == IdempotencyRecord.State.COMPLETED:
            response = Response(record.response_body, status=record.status_code)
            response["Idempotent-Replayed"] = "true"
            return response
        if record.created_at < timezone.now() - timedelta(seconds=PROCESSING_TIMEOUT_SECONDS):
            record.delete()  # reserva abandonada: se reclama
            return None
        return self._in_progress_response()

    def _in_progress_response(self):
        response = Response(
            {"detail": "Una peticion con esta Idempotency-Key sigue en proceso."},
            status=status.HTTP_409_CONFLICT,
        )
        response["Retry-After"] = "1"
        return response

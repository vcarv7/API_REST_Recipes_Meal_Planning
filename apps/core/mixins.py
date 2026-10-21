import hashlib
import json

from django.db import IntegrityError, transaction
from rest_framework import status
from rest_framework.response import Response

from apps.core.models import IdempotencyRecord


class IdempotentCreateMixin:
    """POST idempotente mediante el header ``Idempotency-Key``.

    Sin header: comportamiento normal. Con un header repetido: replay de la
    respuesta original; misma key con payload distinto: 422.
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
        if record is not None:
            if record.fingerprint != fingerprint:
                return Response(
                    {"detail": "Idempotency-Key reutilizada con un payload distinto."},
                    status=status.HTTP_422_UNPROCESSABLE_ENTITY,
                )
            response = Response(record.response_body, status=record.status_code)
            response["Idempotent-Replayed"] = "true"
            return response

        response = super().create(request, *args, **kwargs)
        if response.status_code < 500:
            try:
                with transaction.atomic():
                    IdempotencyRecord.objects.create(
                        user=request.user,
                        key=key,
                        fingerprint=fingerprint,
                        status_code=response.status_code,
                        response_body=response.data,
                    )
            except IntegrityError:
                pass  # otro request con la misma key gano la carrera
        return response

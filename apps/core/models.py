from django.conf import settings
from django.db import models


class IdempotencyRecord(models.Model):
    class State(models.TextChoices):
        PROCESSING = "processing", "Processing"
        COMPLETED = "completed", "Completed"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    key = models.CharField(max_length=255)
    fingerprint = models.CharField(max_length=64)
    state = models.CharField(
        max_length=20,
        choices=State.choices,
        default=State.COMPLETED,
    )
    status_code = models.PositiveSmallIntegerField(null=True, blank=True)
    response_body = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "key"],
                name="unique_idempotency_key_per_user",
            )
        ]

    def __str__(self):
        return f"{self.user}:{self.key}"

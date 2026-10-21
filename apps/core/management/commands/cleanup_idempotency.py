from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.core.models import IdempotencyRecord


class Command(BaseCommand):
    help = "Elimina registros de idempotencia con mas de 24 horas."

    def handle(self, *args, **options):
        cutoff = timezone.now() - timedelta(hours=24)
        deleted, _ = IdempotencyRecord.objects.filter(created_at__lt=cutoff).delete()
        self.stdout.write(self.style.SUCCESS(f"Registros eliminados: {deleted}"))

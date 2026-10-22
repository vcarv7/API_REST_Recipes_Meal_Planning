import hashlib
import json
from datetime import date, timedelta

from django.core.management import call_command
from django.utils import timezone
from rest_framework.test import APIClient, APITestCase

from apps.core.models import IdempotencyRecord
from apps.recipes.models import Recipe
from apps.user.models import User


class IdempotencyTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="idem_user",
            password="super-secret-123",
            country="Venezuela",
            date_birth=date(1990, 1, 1),
        )

    def setUp(self):
        self.client.force_authenticate(self.user)

    def _payload(self, name="Tortilla"):
        return {
            "name": name,
            "instructions": "Batir y cuajar.",
            "prep_time": 0.5,
            "servings": 4,
        }

    def test_same_key_replays_creation(self):
        first = self.client.post(
            "/api/recipes/", self._payload(), format="json", HTTP_IDEMPOTENCY_KEY="key-1"
        )
        self.assertEqual(first.status_code, 201)
        second = self.client.post(
            "/api/recipes/", self._payload(), format="json", HTTP_IDEMPOTENCY_KEY="key-1"
        )
        self.assertEqual(second.status_code, 201)
        self.assertEqual(second["Idempotent-Replayed"], "true")
        self.assertEqual(first.data["id"], second.data["id"])
        self.assertEqual(Recipe.objects.count(), 1)

    def test_same_key_with_different_payload_is_422(self):
        self.client.post(
            "/api/recipes/",
            self._payload("Receta A"),
            format="json",
            HTTP_IDEMPOTENCY_KEY="key-2",
        )
        response = self.client.post(
            "/api/recipes/",
            self._payload("Receta B"),
            format="json",
            HTTP_IDEMPOTENCY_KEY="key-2",
        )
        self.assertEqual(response.status_code, 422)

    def test_without_key_creates_twice(self):
        self.client.post("/api/recipes/", self._payload(), format="json")
        self.client.post("/api/recipes/", self._payload(), format="json")
        self.assertEqual(Recipe.objects.count(), 2)

    def test_key_is_scoped_per_user(self):
        other = User.objects.create_user(
            username="idem_other",
            password="super-secret-123",
            country="Venezuela",
            date_birth=date(1991, 2, 2),
        )
        self.client.post(
            "/api/recipes/",
            self._payload("Receta A"),
            format="json",
            HTTP_IDEMPOTENCY_KEY="shared",
        )
        client = APIClient()
        client.force_authenticate(other)
        response = client.post(
            "/api/recipes/",
            self._payload("Receta B"),
            format="json",
            HTTP_IDEMPOTENCY_KEY="shared",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Recipe.objects.count(), 2)

    def test_plan_creation_is_idempotent(self):
        first = self.client.post(
            "/api/plans/", {}, format="json", HTTP_IDEMPOTENCY_KEY="plan-key"
        )
        second = self.client.post(
            "/api/plans/", {}, format="json", HTTP_IDEMPOTENCY_KEY="plan-key"
        )
        self.assertEqual(first.status_code, 201)
        self.assertEqual(first.data["id"], second.data["id"])

    def test_cleanup_command_removes_old_records(self):
        self.client.post(
            "/api/recipes/", self._payload(), format="json", HTTP_IDEMPOTENCY_KEY="old-key"
        )
        record = IdempotencyRecord.objects.get(key="old-key")
        IdempotencyRecord.objects.filter(pk=record.pk).update(
            created_at=timezone.now() - timedelta(hours=25)
        )
        call_command("cleanup_idempotency")
        self.assertEqual(IdempotencyRecord.objects.count(), 0)


class IdempotencyRaceTests(APITestCase):
    """Carrera concurrente simulada por estado de la reserva en la BD."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="race_user",
            password="super-secret-123",
            country="Venezuela",
            date_birth=date(1990, 1, 1),
        )

    def setUp(self):
        self.client.force_authenticate(self.user)

    def _payload(self, name="Tortilla"):
        return {
            "name": name,
            "instructions": "Batir y cuajar.",
            "prep_time": 0.5,
            "servings": 4,
        }

    def _create_processing_record(self, key, payload, age_seconds=0):
        fingerprint = hashlib.sha256(
            json.dumps(
                {"path": "/api/recipes/", "body": payload},
                sort_keys=True,
                default=str,
            ).encode()
        ).hexdigest()
        record = IdempotencyRecord.objects.create(
            user=self.user,
            key=key,
            fingerprint=fingerprint,
            state=IdempotencyRecord.State.PROCESSING,
        )
        if age_seconds:
            IdempotencyRecord.objects.filter(pk=record.pk).update(
                created_at=timezone.now() - timedelta(seconds=age_seconds)
            )
        return record

    def test_duplicate_while_processing_gets_409(self):
        payload = self._payload()
        self._create_processing_record("race-key", payload)
        response = self.client.post(
            "/api/recipes/", payload, format="json", HTTP_IDEMPOTENCY_KEY="race-key"
        )
        self.assertEqual(response.status_code, 409)
        self.assertIn("Retry-After", response.headers)
        self.assertEqual(Recipe.objects.count(), 0)

    def test_processing_record_with_different_payload_is_422(self):
        payload = self._payload()
        self._create_processing_record("race-key-2", payload)
        response = self.client.post(
            "/api/recipes/",
            self._payload("Otra"),
            format="json",
            HTTP_IDEMPOTENCY_KEY="race-key-2",
        )
        self.assertEqual(response.status_code, 422)

    def test_completed_reservation_replays(self):
        payload = self._payload()
        record = self._create_processing_record("race-key-3", payload)
        IdempotencyRecord.objects.filter(pk=record.pk).update(
            state=IdempotencyRecord.State.COMPLETED,
            status_code=201,
            response_body={"id": 999, "name": payload["name"]},
        )
        response = self.client.post(
            "/api/recipes/", payload, format="json", HTTP_IDEMPOTENCY_KEY="race-key-3"
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["id"], 999)
        self.assertEqual(response["Idempotent-Replayed"], "true")
        self.assertEqual(Recipe.objects.count(), 0)

    def test_stale_processing_reservation_is_reclaimed(self):
        payload = self._payload("Reclamada")
        self._create_processing_record("race-key-4", payload, age_seconds=600)
        response = self.client.post(
            "/api/recipes/", payload, format="json", HTTP_IDEMPOTENCY_KEY="race-key-4"
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Recipe.objects.count(), 1)
        record = IdempotencyRecord.objects.get(key="race-key-4")
        self.assertEqual(record.state, IdempotencyRecord.State.COMPLETED)

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

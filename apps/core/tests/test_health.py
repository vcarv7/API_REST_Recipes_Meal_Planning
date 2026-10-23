from unittest.mock import patch

from django.db.utils import OperationalError
from django.test import TestCase


class HealthTests(TestCase):
    def test_health_is_ok(self):
        response = self.client.get("/health/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok", "database": "up"})

    def test_health_without_trailing_slash(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)

    def test_health_ignores_throttling(self):
        for _ in range(30):
            response = self.client.get("/health/")
        self.assertEqual(response.status_code, 200)

    @patch("apps.core.views.connection")
    def test_health_reports_503_when_database_is_down(self, mock_connection):
        mock_connection.cursor.side_effect = OperationalError("db down")
        response = self.client.get("/health/")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["database"], "down")

from datetime import date

from rest_framework.test import APIClient, APITestCase

from apps.plan.models import Plan
from apps.user.models import User


class TokenAuthTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="jwt_user",
            password="super-secret-123",
            country="Venezuela",
            date_birth=date(1990, 1, 1),
        )

    def _obtain(self):
        return self.client.post(
            "/api/auth/token/",
            {"username": "jwt_user", "password": "super-secret-123"},
            format="json",
        )

    def test_login_returns_access_and_refresh(self):
        response = self._obtain()
        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_login_with_wrong_password_is_401(self):
        response = self.client.post(
            "/api/auth/token/",
            {"username": "jwt_user", "password": "wrong-password"},
            format="json",
        )
        self.assertEqual(response.status_code, 401)

    def test_inactive_user_cannot_login(self):
        self.user.is_active = False
        self.user.save()
        response = self._obtain()
        self.assertEqual(response.status_code, 401)

    def test_refresh_returns_new_access(self):
        refresh = self._obtain().data["refresh"]
        response = self.client.post(
            "/api/auth/token/refresh/", {"refresh": refresh}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data)

    def test_garbage_refresh_is_401(self):
        response = self.client.post(
            "/api/auth/token/refresh/", {"refresh": "garbage"}, format="json"
        )
        self.assertEqual(response.status_code, 401)

    def test_access_token_cannot_be_used_as_refresh(self):
        access = self._obtain().data["access"]
        response = self.client.post(
            "/api/auth/token/refresh/", {"refresh": access}, format="json"
        )
        self.assertEqual(response.status_code, 401)

    def test_verify_valid_token(self):
        access = self._obtain().data["access"]
        response = self.client.post(
            "/api/auth/token/verify/", {"token": access}, format="json"
        )
        self.assertEqual(response.status_code, 200)

    def test_verify_invalid_token_is_401(self):
        response = self.client.post(
            "/api/auth/token/verify/", {"token": "garbage"}, format="json"
        )
        self.assertEqual(response.status_code, 401)

    def test_bearer_token_authenticates_and_scopes_by_owner(self):
        other = User.objects.create_user(
            username="other_jwt",
            password="other-secret-123",
            country="Venezuela",
            date_birth=date(1991, 2, 2),
        )
        Plan.objects.create(user=other)
        access = self._obtain().data["access"]
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        response = client.get("/api/plans/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 0)

    def test_garbage_bearer_is_401(self):
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION="Bearer not-a-real-token")
        response = client.get("/api/plans/")
        self.assertEqual(response.status_code, 401)

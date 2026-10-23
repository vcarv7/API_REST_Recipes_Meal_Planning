from datetime import date

from django.core.cache import cache

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

    def setUp(self):
        cache.clear()

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


class RegisterApiTests(APITestCase):
    def setUp(self):
        cache.clear()

    def test_register_creates_user_with_hashed_password(self):
        response = self.client.post(
            "/api/auth/register/",
            {
                "username": "new_cook",
                "password": "super-secret-123",
                "email": "cook@example.com",
                "country": "Venezuela",
                "date_birth": "1995-05-05",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        user = User.objects.get(username="new_cook")
        self.assertTrue(user.check_password("super-secret-123"))
        self.assertNotIn("password", response.data)

    def test_register_rejects_duplicate_username(self):
        User.objects.create_user(
            username="dup_cook",
            password="super-secret-123",
            country="Venezuela",
            date_birth=date(1990, 1, 1),
        )
        response = self.client.post(
            "/api/auth/register/",
            {
                "username": "dup_cook",
                "password": "super-secret-123",
                "country": "Venezuela",
                "date_birth": "1995-05-05",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("username", response.data)

    def test_register_rejects_weak_password(self):
        response = self.client.post(
            "/api/auth/register/",
            {
                "username": "weak_cook",
                "password": "123",
                "country": "Venezuela",
                "date_birth": "1995-05-05",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("password", response.data)

    def test_register_requires_country_and_date_birth(self):
        response = self.client.post(
            "/api/auth/register/",
            {"username": "bare_cook", "password": "super-secret-123"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("country", response.data)
        self.assertIn("date_birth", response.data)

    def test_register_rejects_duplicate_email(self):
        User.objects.create_user(
            username="email_owner",
            password="super-secret-123",
            email="cook@example.com",
            country="Venezuela",
            date_birth=date(1990, 1, 1),
        )
        response = self.client.post(
            "/api/auth/register/",
            {
                "username": "email_dup",
                "password": "super-secret-123",
                "email": "cook@example.com",
                "country": "Venezuela",
                "date_birth": "1995-05-05",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("email", response.data)

    def test_register_rejects_duplicate_email_case_insensitive(self):
        User.objects.create_user(
            username="email_owner2",
            password="super-secret-123",
            email="cook@example.com",
            country="Venezuela",
            date_birth=date(1990, 1, 1),
        )
        response = self.client.post(
            "/api/auth/register/",
            {
                "username": "email_dup2",
                "password": "super-secret-123",
                "email": "COOK@Example.COM",
                "country": "Venezuela",
                "date_birth": "1995-05-05",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("email", response.data)

    def test_register_without_email_is_allowed(self):
        first = self.client.post(
            "/api/auth/register/",
            {
                "username": "no_mail_1",
                "password": "super-secret-123",
                "country": "Venezuela",
                "date_birth": "1995-05-05",
            },
            format="json",
        )
        second = self.client.post(
            "/api/auth/register/",
            {
                "username": "no_mail_2",
                "password": "super-secret-123",
                "country": "Venezuela",
                "date_birth": "1995-05-05",
            },
            format="json",
        )
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 201)
        self.assertIsNone(User.objects.get(username="no_mail_1").email)
        self.assertIsNone(User.objects.get(username="no_mail_2").email)

    def test_register_normalizes_email(self):
        response = self.client.post(
            "/api/auth/register/",
            {
                "username": "norm_mail",
                "password": "super-secret-123",
                "email": "Cook@Example.COM",
                "country": "Venezuela",
                "date_birth": "1995-05-05",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(User.objects.get(username="norm_mail").email, "cook@example.com")

    def test_register_with_empty_email_is_allowed(self):
        response = self.client.post(
            "/api/auth/register/",
            {
                "username": "empty_mail",
                "password": "super-secret-123",
                "email": "",
                "country": "Venezuela",
                "date_birth": "1995-05-05",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertIsNone(User.objects.get(username="empty_mail").email)


class LogoutBlacklistTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="logout_user",
            password="super-secret-123",
            country="Venezuela",
            date_birth=date(1990, 1, 1),
        )

    def setUp(self):
        cache.clear()

    def _login(self):
        return self.client.post(
            "/api/auth/token/",
            {"username": "logout_user", "password": "super-secret-123"},
            format="json",
        )

    def test_logout_blacklists_refresh(self):
        refresh = self._login().data["refresh"]
        response = self.client.post(
            "/api/auth/token/blacklist/", {"refresh": refresh}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        response = self.client.post(
            "/api/auth/token/refresh/", {"refresh": refresh}, format="json"
        )
        self.assertEqual(response.status_code, 401)

    def test_rotation_blacklists_previous_refresh(self):
        old_refresh = self._login().data["refresh"]
        rotated = self.client.post(
            "/api/auth/token/refresh/", {"refresh": old_refresh}, format="json"
        )
        self.assertEqual(rotated.status_code, 200)
        self.assertIn("refresh", rotated.data)
        reuse = self.client.post(
            "/api/auth/token/refresh/", {"refresh": old_refresh}, format="json"
        )
        self.assertEqual(reuse.status_code, 401)

    def test_access_survives_logout_until_expiry(self):
        login = self._login()
        access, refresh = login.data["access"], login.data["refresh"]
        self.client.post("/api/auth/token/blacklist/", {"refresh": refresh}, format="json")
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        response = client.get("/api/plans/")
        self.assertEqual(response.status_code, 200)


class ThrottleTests(APITestCase):
    def setUp(self):
        cache.clear()

    def test_login_is_rate_limited(self):
        User.objects.create_user(
            username="throttle_user",
            password="super-secret-123",
            country="Venezuela",
            date_birth=date(1990, 1, 1),
        )
        payload = {"username": "throttle_user", "password": "wrong-password"}
        for _ in range(10):
            response = self.client.post("/api/auth/token/", payload, format="json")
            self.assertEqual(response.status_code, 401)
        response = self.client.post("/api/auth/token/", payload, format="json")
        self.assertEqual(response.status_code, 429)
        self.assertIn("Retry-After", response.headers)

    def test_register_is_rate_limited(self):
        for index in range(10):
            response = self.client.post(
                "/api/auth/register/",
                {
                    "username": f"rate_reg_{index}",
                    "password": "super-secret-123",
                    "country": "Venezuela",
                    "date_birth": "1990-01-01",
                },
                format="json",
            )
            self.assertEqual(response.status_code, 201)
        response = self.client.post(
            "/api/auth/register/",
            {
                "username": "rate_reg_extra",
                "password": "super-secret-123",
                "country": "Venezuela",
                "date_birth": "1990-01-01",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 429)

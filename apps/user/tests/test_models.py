from datetime import date

from django.test import TestCase

from apps.user.models import User


class UserModelTests(TestCase):
    def test_create_user_persists_extra_fields(self):
        user = User.objects.create_user(
            username="cook",
            password="secret-123",
            country="Venezuela",
            date_birth=date(1990, 1, 1),
        )
        self.assertEqual(user.country, "Venezuela")
        self.assertEqual(user.date_birth, date(1990, 1, 1))
        self.assertTrue(user.check_password("secret-123"))
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_create_superuser_sets_flags(self):
        user = User.objects.create_superuser(
            username="root",
            password="secret-123",
            country="Venezuela",
            date_birth=date(1990, 1, 1),
        )
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)

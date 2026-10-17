from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from apps.user.models import User


class RegisterSerializer(serializers.ModelSerializer):
    """Creates a user with a validated, hashed password."""

    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ["id", "username", "password", "email", "country", "date_birth"]

    def validate_password(self, value):
        validate_password(value)
        return value

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)

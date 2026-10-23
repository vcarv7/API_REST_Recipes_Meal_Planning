from rest_framework import generics, permissions
from rest_framework.throttling import ScopedRateThrottle
from rest_framework_simplejwt.views import TokenObtainPairView

from apps.user.serializers import RegisterSerializer


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "register"


class ThrottledTokenObtainPairView(TokenObtainPairView):
    """Login con rate limit por scope (anti fuerza bruta)."""

    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

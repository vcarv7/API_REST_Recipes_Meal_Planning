from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from apps.plan.models import Plan
from apps.plan.serializers import PlanSerializer


class PlanViewSet(viewsets.ModelViewSet):
    serializer_class = PlanSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Plan.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

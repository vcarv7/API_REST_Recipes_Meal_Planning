from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.plan.models import Plan, PlanMeal
from apps.plan.serializers import PlanMealSerializer, PlanSerializer


class PlanViewSet(viewsets.ModelViewSet):
    serializer_class = PlanSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Plan.objects.filter(user=self.request.user).prefetch_related("meals__recipe")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=["get", "post"], url_path="meals")
    def meals(self, request, pk=None):
        plan = self.get_object()
        if request.method == "POST":
            serializer = PlanMealSerializer(
                data=request.data,
                context={**self.get_serializer_context(), "plan": plan},
            )
            serializer.is_valid(raise_exception=True)
            serializer.save(plan=plan)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        queryset = plan.meals.select_related("recipe")
        return Response(PlanMealSerializer(queryset, many=True).data)


class PlanMealView(
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = PlanMealSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return PlanMeal.objects.filter(plan__user=self.request.user).select_related("recipe")

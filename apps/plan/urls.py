from rest_framework.routers import DefaultRouter

from apps.plan.views import PlanMealView, PlanViewSet

router = DefaultRouter()
router.register("plans", PlanViewSet, basename="plan")
router.register("plan-meals", PlanMealView, basename="plan-meal")

urlpatterns = router.urls

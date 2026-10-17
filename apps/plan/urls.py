from rest_framework.routers import DefaultRouter

from apps.plan.views import PlanViewSet

router = DefaultRouter()
router.register("plans", PlanViewSet, basename="plan")

urlpatterns = router.urls

from rest_framework.routers import DefaultRouter

from apps.recipes.views import IngredientViewSet, RecipeViewSet

router = DefaultRouter()
router.register("recipes", RecipeViewSet)
router.register("ingredients", IngredientViewSet)

urlpatterns = router.urls

from rest_framework.routers import DefaultRouter

from apps.recipes.views import IngredientViewSet, RecipeIngredientView, RecipeViewSet

router = DefaultRouter()
router.register("recipes", RecipeViewSet)
router.register("ingredients", IngredientViewSet)
router.register("recipe-ingredients", RecipeIngredientView, basename="recipe-ingredient")

urlpatterns = router.urls

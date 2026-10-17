from rest_framework import viewsets

from apps.recipes.models import Ingredient, Recipe
from apps.recipes.serializers import IngredientSerializer, RecipeSerializer


class IngredientViewSet(viewsets.ModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.prefetch_related("recipe_ingredients__ingredient")
    serializer_class = RecipeSerializer

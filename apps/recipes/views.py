from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.recipes.models import Ingredient, Recipe, Recipe_Ingredient
from apps.recipes.serializers import (
    IngredientSerializer,
    RecipeIngredientSerializer,
    RecipeSerializer,
)


class IngredientViewSet(viewsets.ModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.prefetch_related("recipe_ingredients__ingredient")
    serializer_class = RecipeSerializer

    @action(detail=True, methods=["get", "post"], url_path="recipe-ingredients")
    def recipe_ingredients(self, request, pk=None):
        recipe = self.get_object()
        if request.method == "POST":
            serializer = RecipeIngredientSerializer(
                data=request.data,
                context={**self.get_serializer_context(), "recipe": recipe},
            )
            serializer.is_valid(raise_exception=True)
            serializer.save(recipe=recipe)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        lines = recipe.recipe_ingredients.select_related("ingredient")
        return Response(RecipeIngredientSerializer(lines, many=True).data)


class RecipeIngredientView(
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Recipe_Ingredient.objects.select_related("ingredient")
    serializer_class = RecipeIngredientSerializer

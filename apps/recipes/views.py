from django.db.models import ProtectedError

from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from apps.recipes.models import Ingredient, Recipe, RecipeIngredient
from apps.recipes.serializers import (
    IngredientSerializer,
    RecipeIngredientSerializer,
    RecipeSerializer,
)


class IngredientViewSet(viewsets.ModelViewSet):
    queryset = Ingredient.objects.order_by("name", "id")
    serializer_class = IngredientSerializer


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.prefetch_related("recipe_ingredients__ingredient").order_by("name", "id")
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
        queryset = recipe.recipe_ingredients.select_related("ingredient").order_by("id")
        page = self.paginate_queryset(queryset)
        serializer = RecipeIngredientSerializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        try:
            return super().destroy(request, *args, **kwargs)
        except ProtectedError:
            raise ValidationError(
                {"detail": "No se puede borrar: la receta está en uso en uno o más planes."}
            )


class RecipeIngredientView(
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    queryset = RecipeIngredient.objects.select_related("ingredient")
    serializer_class = RecipeIngredientSerializer

from django.db.models import ProtectedError

from drf_spectacular.utils import extend_schema

from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response

from apps.core.mixins import IdempotentCreateMixin
from apps.recipes.models import Ingredient, Recipe, RecipeIngredient
from apps.recipes.permissions import IsOwnerOrReadOnly
from apps.recipes.serializers import (
    IngredientSerializer,
    RecipeIngredientSerializer,
    RecipeSerializer,
)


class IngredientViewSet(IdempotentCreateMixin, viewsets.ModelViewSet):
    queryset = Ingredient.objects.order_by("name", "id")
    serializer_class = IngredientSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]


class RecipeViewSet(IdempotentCreateMixin, viewsets.ModelViewSet):
    queryset = Recipe.objects.prefetch_related("recipe_ingredients__ingredient").order_by("name", "id")
    serializer_class = RecipeSerializer
    permission_classes = [IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @extend_schema(
        methods=["POST"],
        request=RecipeIngredientSerializer,
        responses={201: RecipeIngredientSerializer},
    )
    @extend_schema(
        methods=["GET"],
        responses=RecipeIngredientSerializer(many=True),
    )
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
    permission_classes = [IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]

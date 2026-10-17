from rest_framework import serializers

from apps.recipes.models import Ingredient, Recipe, Recipe_Ingredient


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = ["id", "name", "unit"]


class RecipeIngredientSerializer(serializers.ModelSerializer):
    """Through row between Recipe and Ingredient.

    Reads nest full ingredient detail; writes expect ``ingredient_id``.
    The parent recipe is not a field: it comes from the URL in the view layer.
    """

    ingredient = IngredientSerializer(read_only=True)
    ingredient_id = serializers.PrimaryKeyRelatedField(
        queryset=Ingredient.objects.all(),
        source="ingredient",
        write_only=True,
    )
    quantity = serializers.IntegerField(min_value=1)

    class Meta:
        model = Recipe_Ingredient
        fields = ["id", "ingredient", "ingredient_id", "quantity"]


class RecipeSerializer(serializers.ModelSerializer):
    """Recipe with its ingredient lines inlined as read-only nested data."""

    recipe_ingredients = RecipeIngredientSerializer(many=True, read_only=True)

    class Meta:
        model = Recipe
        fields = [
            "id",
            "name",
            "instructions",
            "prep_time",
            "servings",
            "recipe_ingredients",
        ]

from rest_framework import serializers

from apps.recipes.models import Ingredient, Recipe, RecipeIngredient


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
        model = RecipeIngredient
        fields = ["id", "ingredient", "ingredient_id", "quantity"]

    def validate(self, attrs):
        recipe = self.context.get("recipe") if self.instance is None else self.instance.recipe
        ingredient = attrs.get("ingredient") or (self.instance.ingredient if self.instance else None)
        if recipe is None or ingredient is None:
            return attrs
        duplicates = RecipeIngredient.objects.filter(recipe=recipe, ingredient=ingredient)
        if self.instance is not None:
            duplicates = duplicates.exclude(pk=self.instance.pk)
        if duplicates.exists():
            raise serializers.ValidationError(
                {"ingredient_id": "Este ingrediente ya forma parte de la receta."}
            )
        return attrs


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


class RecipeSummarySerializer(serializers.ModelSerializer):
    """Slim recipe representation for nesting in other resources."""

    class Meta:
        model = Recipe
        fields = ["id", "name", "prep_time", "servings"]

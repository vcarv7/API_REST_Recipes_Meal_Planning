from rest_framework import serializers

from apps.plan.models import Plan, PlanMeal
from apps.recipes.models import Recipe
from apps.recipes.serializers import RecipeSummarySerializer


class PlanMealSerializer(serializers.ModelSerializer):
    """Planned recipe inside a plan (one dish of a meal).

    Reads nest a recipe summary; writes expect ``recipe_id``.
    The parent plan is not a field: it comes from the URL in the view layer.
    """

    recipe = RecipeSummarySerializer(read_only=True)
    recipe_id = serializers.PrimaryKeyRelatedField(
        queryset=Recipe.objects.all(),
        source="recipe",
        write_only=True,
    )

    class Meta:
        model = PlanMeal
        fields = ["id", "recipe", "recipe_id", "date", "meal_type"]

    def validate(self, attrs):
        plan = self.context.get("plan") if self.instance is None else self.instance.plan
        date_value = attrs.get("date") or (self.instance.date if self.instance else None)
        if plan is None or date_value is None:
            return attrs
        if date_value < plan.start_date.date() or (plan.end_date and date_value > plan.end_date):
            raise serializers.ValidationError(
                {"date": "La fecha debe estar dentro del rango del plan."}
            )
        recipe = attrs.get("recipe") or (self.instance.recipe if self.instance else None)
        meal_type = attrs.get("meal_type") or (self.instance.meal_type if self.instance else None)
        if recipe is None or meal_type is None:
            return attrs
        duplicates = PlanMeal.objects.filter(
            plan=plan, date=date_value, meal_type=meal_type, recipe=recipe
        )
        if self.instance is not None:
            duplicates = duplicates.exclude(pk=self.instance.pk)
        if duplicates.exists():
            raise serializers.ValidationError(
                {"recipe_id": "Esta receta ya está planificada en esa comida."}
            )
        return attrs


class PlanSerializer(serializers.ModelSerializer):
    """Plan owned by the requesting user.

    ``user`` is not a field: the view injects it from ``request.user``.
    ``start_date`` defaults to now and ``end_date`` to start + 7 days.
    """

    meals = PlanMealSerializer(many=True, read_only=True)

    class Meta:
        model = Plan
        fields = ["id", "start_date", "end_date", "meals"]

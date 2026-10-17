from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.recipes.models import Ingredient, Recipe, Recipe_Ingredient


class RecipeModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.recipe = Recipe.objects.create(
            name="Tortilla", instructions="Batir y cuajar.", prep_time=0.5, servings=4
        )
        cls.egg = Ingredient.objects.create(name="Huevo", unit="unidades")

    def test_duplicate_recipe_ingredient_is_rejected(self):
        Recipe_Ingredient.objects.create(recipe=self.recipe, ingredient=self.egg, quantity=4)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Recipe_Ingredient.objects.create(
                    recipe=self.recipe, ingredient=self.egg, quantity=2
                )

    def test_same_ingredient_in_another_recipe_is_allowed(self):
        omelette = Recipe.objects.create(
            name="Omelette", instructions="Cuajar huevos.", prep_time=0.2, servings=2
        )
        Recipe_Ingredient.objects.create(recipe=self.recipe, ingredient=self.egg, quantity=4)
        Recipe_Ingredient.objects.create(recipe=omelette, ingredient=self.egg, quantity=2)
        self.assertEqual(Recipe_Ingredient.objects.count(), 2)

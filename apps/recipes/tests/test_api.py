from rest_framework.test import APITestCase

from apps.recipes.models import Ingredient, Recipe, Recipe_Ingredient


class IngredientApiTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.egg = Ingredient.objects.create(name="Huevo", unit="unidades")
        cls.potato = Ingredient.objects.create(name="Patata", unit="g")

    def test_create_ingredient(self):
        response = self.client.post(
            "/api/ingredients/", {"name": "Cebolla", "unit": "unidades"}, format="json"
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["name"], "Cebolla")
        self.assertEqual(Ingredient.objects.count(), 3)

    def test_list_ingredients(self):
        response = self.client.get("/api/ingredients/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)

    def test_update_ingredient(self):
        response = self.client.patch(
            f"/api/ingredients/{self.potato.pk}/", {"unit": "kg"}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.potato.refresh_from_db()
        self.assertEqual(self.potato.unit, "kg")

    def test_delete_ingredient(self):
        response = self.client.delete(f"/api/ingredients/{self.potato.pk}/")
        self.assertEqual(response.status_code, 204)
        self.assertEqual(self.client.get(f"/api/ingredients/{self.potato.pk}/").status_code, 404)


class RecipeApiTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.recipe = Recipe.objects.create(
            name="Tortilla", instructions="Batir y cuajar.", prep_time=0.5, servings=4
        )
        cls.egg = Ingredient.objects.create(name="Huevo", unit="unidades")
        cls.potato = Ingredient.objects.create(name="Patata", unit="g")

    def test_create_recipe(self):
        response = self.client.post(
            "/api/recipes/",
            {"name": "Sopa", "instructions": "Hervir verduras.", "prep_time": 1.0, "servings": 6},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["recipe_ingredients"], [])

    def test_recipe_detail_includes_nested_lines(self):
        Recipe_Ingredient.objects.create(recipe=self.recipe, ingredient=self.egg, quantity=4)
        response = self.client.get(f"/api/recipes/{self.recipe.pk}/")
        self.assertEqual(response.status_code, 200)
        lines = response.data["recipe_ingredients"]
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]["ingredient"]["name"], "Huevo")
        self.assertEqual(lines[0]["quantity"], 4)

    def test_recipe_detail_query_count(self):
        third = Ingredient.objects.create(name="Cebolla", unit="unidades")
        Recipe_Ingredient.objects.create(recipe=self.recipe, ingredient=self.egg, quantity=4)
        Recipe_Ingredient.objects.create(recipe=self.recipe, ingredient=self.potato, quantity=500)
        Recipe_Ingredient.objects.create(recipe=self.recipe, ingredient=third, quantity=1)
        with self.assertNumQueries(3):
            response = self.client.get(f"/api/recipes/{self.recipe.pk}/")
        self.assertEqual(response.status_code, 200)

    def test_delete_recipe_cascades_lines(self):
        Recipe_Ingredient.objects.create(recipe=self.recipe, ingredient=self.egg, quantity=4)
        response = self.client.delete(f"/api/recipes/{self.recipe.pk}/")
        self.assertEqual(response.status_code, 204)
        self.assertEqual(Recipe_Ingredient.objects.count(), 0)

    def test_create_line_via_nested_endpoint(self):
        response = self.client.post(
            f"/api/recipes/{self.recipe.pk}/recipe-ingredients/",
            {"ingredient_id": self.egg.pk, "quantity": 4},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["ingredient"]["name"], "Huevo")
        self.assertEqual(response.data["quantity"], 4)

    def test_duplicate_line_is_rejected(self):
        Recipe_Ingredient.objects.create(recipe=self.recipe, ingredient=self.egg, quantity=4)
        response = self.client.post(
            f"/api/recipes/{self.recipe.pk}/recipe-ingredients/",
            {"ingredient_id": self.egg.pk, "quantity": 2},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("ingredient_id", response.data)

    def test_line_for_missing_recipe_returns_404(self):
        response = self.client.post(
            "/api/recipes/999999/recipe-ingredients/",
            {"ingredient_id": self.egg.pk, "quantity": 1},
            format="json",
        )
        self.assertEqual(response.status_code, 404)

    def test_line_with_unknown_ingredient_returns_400(self):
        response = self.client.post(
            f"/api/recipes/{self.recipe.pk}/recipe-ingredients/",
            {"ingredient_id": 999999, "quantity": 1},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("ingredient_id", response.data)

    def test_update_line_quantity(self):
        line = Recipe_Ingredient.objects.create(
            recipe=self.recipe, ingredient=self.egg, quantity=4
        )
        response = self.client.patch(
            f"/api/recipe-ingredients/{line.pk}/", {"quantity": 5}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        line.refresh_from_db()
        self.assertEqual(line.quantity, 5)

    def test_update_line_to_duplicate_is_rejected(self):
        line = Recipe_Ingredient.objects.create(
            recipe=self.recipe, ingredient=self.egg, quantity=4
        )
        Recipe_Ingredient.objects.create(recipe=self.recipe, ingredient=self.potato, quantity=500)
        response = self.client.patch(
            f"/api/recipe-ingredients/{line.pk}/", {"ingredient_id": self.potato.pk}, format="json"
        )
        self.assertEqual(response.status_code, 400)

    def test_delete_line(self):
        line = Recipe_Ingredient.objects.create(
            recipe=self.recipe, ingredient=self.egg, quantity=4
        )
        response = self.client.delete(f"/api/recipe-ingredients/{line.pk}/")
        self.assertEqual(response.status_code, 204)
        self.assertEqual(Recipe_Ingredient.objects.count(), 0)

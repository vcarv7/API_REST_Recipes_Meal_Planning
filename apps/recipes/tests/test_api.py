from datetime import date

from rest_framework.test import APIClient, APITestCase

from apps.recipes.models import Ingredient, Recipe, RecipeIngredient
from apps.user.models import User


class IngredientApiTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="ing_writer",
            password="super-secret-123",
            country="Venezuela",
            date_birth=date(1990, 1, 1),
        )
        cls.egg = Ingredient.objects.create(name="Huevo", unit="unidades")
        cls.potato = Ingredient.objects.create(name="Patata", unit="g")

    def test_anonymous_read_is_public(self):
        response = APIClient().get("/api/ingredients/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 2)

    def test_anonymous_write_is_401(self):
        response = APIClient().post(
            "/api/ingredients/", {"name": "Cebolla", "unit": "unidades"}, format="json"
        )
        self.assertEqual(response.status_code, 401)

    def test_create_ingredient(self):
        self.client.force_authenticate(self.user)
        response = self.client.post(
            "/api/ingredients/", {"name": "Cebolla", "unit": "unidades"}, format="json"
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["name"], "Cebolla")
        self.assertEqual(Ingredient.objects.count(), 3)

    def test_list_ingredients(self):
        response = self.client.get("/api/ingredients/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 2)
        self.assertEqual(len(response.data["results"]), 2)

    def test_update_ingredient(self):
        self.client.force_authenticate(self.user)
        response = self.client.patch(
            f"/api/ingredients/{self.potato.pk}/", {"unit": "kg"}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.potato.refresh_from_db()
        self.assertEqual(self.potato.unit, "kg")

    def test_delete_ingredient(self):
        self.client.force_authenticate(self.user)
        response = self.client.delete(f"/api/ingredients/{self.potato.pk}/")
        self.assertEqual(response.status_code, 204)
        self.assertEqual(self.client.get(f"/api/ingredients/{self.potato.pk}/").status_code, 404)

    def test_ingredient_list_is_paginated(self):
        for index in range(10):
            Ingredient.objects.create(name=f"Extra {index}", unit="unidades")
        first = self.client.get("/api/ingredients/")
        self.assertEqual(first.data["count"], 12)
        self.assertEqual(len(first.data["results"]), 10)
        self.assertIsNotNone(first.data["next"])
        second = self.client.get("/api/ingredients/?page=2")
        self.assertEqual(len(second.data["results"]), 2)
        self.assertIsNone(second.data["next"])


class RecipeApiTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user(
            username="recipe_owner",
            password="super-secret-123",
            country="Venezuela",
            date_birth=date(1990, 1, 1),
        )
        cls.other = User.objects.create_user(
            username="recipe_other",
            password="super-secret-123",
            country="Venezuela",
            date_birth=date(1991, 2, 2),
        )
        cls.recipe = Recipe.objects.create(
            name="Tortilla",
            instructions="Batir y cuajar.",
            prep_time=0.5,
            servings=4,
            created_by=cls.owner,
        )
        cls.egg = Ingredient.objects.create(name="Huevo", unit="unidades")
        cls.potato = Ingredient.objects.create(name="Patata", unit="g")

    def test_anonymous_read_is_public(self):
        response = APIClient().get(f"/api/recipes/{self.recipe.pk}/")
        self.assertEqual(response.status_code, 200)

    def test_anonymous_write_is_401(self):
        response = APIClient().post(
            "/api/recipes/",
            {"name": "Sopa", "instructions": "Hervir verduras.", "prep_time": 1.0},
            format="json",
        )
        self.assertEqual(response.status_code, 401)

    def test_create_recipe(self):
        self.client.force_authenticate(self.owner)
        response = self.client.post(
            "/api/recipes/",
            {"name": "Sopa", "instructions": "Hervir verduras.", "prep_time": 1.0, "servings": 6},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["recipe_ingredients"], [])

    def test_create_sets_owner_and_ignores_payload(self):
        self.client.force_authenticate(self.owner)
        response = self.client.post(
            "/api/recipes/",
            {
                "name": "Sopa",
                "instructions": "Hervir verduras.",
                "prep_time": 1.0,
                "created_by": self.other.pk,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Recipe.objects.get(pk=response.data["id"]).created_by, self.owner)
        self.assertEqual(response.data["created_by"], self.owner.pk)

    def test_non_owner_cannot_update_or_delete(self):
        client = APIClient()
        client.force_authenticate(self.other)
        response = client.patch(f"/api/recipes/{self.recipe.pk}/", {"servings": 6}, format="json")
        self.assertEqual(response.status_code, 403)
        response = client.delete(f"/api/recipes/{self.recipe.pk}/")
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Recipe.objects.filter(pk=self.recipe.pk).exists())

    def test_non_owner_can_read(self):
        client = APIClient()
        client.force_authenticate(self.other)
        response = client.get(f"/api/recipes/{self.recipe.pk}/")
        self.assertEqual(response.status_code, 200)

    def test_owner_can_update(self):
        self.client.force_authenticate(self.owner)
        response = self.client.patch(
            f"/api/recipes/{self.recipe.pk}/", {"servings": 6}, format="json"
        )
        self.assertEqual(response.status_code, 200)

    def test_staff_can_edit_orphan_recipe(self):
        orphan = Recipe.objects.create(
            name="Huerfana", instructions="Sin autor.", prep_time=0.3, servings=1
        )
        staff = User.objects.create_superuser(
            username="recipe_staff",
            password="super-secret-123",
            country="Venezuela",
            date_birth=date(1989, 3, 3),
        )
        client = APIClient()
        client.force_authenticate(self.other)
        response = client.patch(f"/api/recipes/{orphan.pk}/", {"servings": 2}, format="json")
        self.assertEqual(response.status_code, 403)
        staff_client = APIClient()
        staff_client.force_authenticate(staff)
        response = staff_client.patch(
            f"/api/recipes/{orphan.pk}/", {"servings": 2}, format="json"
        )
        self.assertEqual(response.status_code, 200)

    def test_recipe_detail_includes_nested_lines(self):
        RecipeIngredient.objects.create(recipe=self.recipe, ingredient=self.egg, quantity=4)
        response = self.client.get(f"/api/recipes/{self.recipe.pk}/")
        self.assertEqual(response.status_code, 200)
        lines = response.data["recipe_ingredients"]
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]["ingredient"]["name"], "Huevo")
        self.assertEqual(lines[0]["quantity"], 4)

    def test_recipe_detail_query_count(self):
        third = Ingredient.objects.create(name="Cebolla", unit="unidades")
        RecipeIngredient.objects.create(recipe=self.recipe, ingredient=self.egg, quantity=4)
        RecipeIngredient.objects.create(recipe=self.recipe, ingredient=self.potato, quantity=500)
        RecipeIngredient.objects.create(recipe=self.recipe, ingredient=third, quantity=1)
        with self.assertNumQueries(3):
            response = self.client.get(f"/api/recipes/{self.recipe.pk}/")
        self.assertEqual(response.status_code, 200)

    def test_delete_recipe_cascades_lines(self):
        RecipeIngredient.objects.create(recipe=self.recipe, ingredient=self.egg, quantity=4)
        self.client.force_authenticate(self.owner)
        response = self.client.delete(f"/api/recipes/{self.recipe.pk}/")
        self.assertEqual(response.status_code, 204)
        self.assertEqual(RecipeIngredient.objects.count(), 0)

    def test_create_line_via_nested_endpoint(self):
        self.client.force_authenticate(self.owner)
        response = self.client.post(
            f"/api/recipes/{self.recipe.pk}/recipe-ingredients/",
            {"ingredient_id": self.egg.pk, "quantity": 4},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["ingredient"]["name"], "Huevo")

    def test_duplicate_line_is_rejected(self):
        RecipeIngredient.objects.create(recipe=self.recipe, ingredient=self.egg, quantity=4)
        self.client.force_authenticate(self.owner)
        response = self.client.post(
            f"/api/recipes/{self.recipe.pk}/recipe-ingredients/",
            {"ingredient_id": self.egg.pk, "quantity": 2},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("ingredient_id", response.data)

    def test_line_for_missing_recipe_returns_404(self):
        self.client.force_authenticate(self.owner)
        response = self.client.post(
            "/api/recipes/999999/recipe-ingredients/",
            {"ingredient_id": self.egg.pk, "quantity": 1},
            format="json",
        )
        self.assertEqual(response.status_code, 404)

    def test_line_with_unknown_ingredient_returns_400(self):
        self.client.force_authenticate(self.owner)
        response = self.client.post(
            f"/api/recipes/{self.recipe.pk}/recipe-ingredients/",
            {"ingredient_id": 999999, "quantity": 1},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("ingredient_id", response.data)

    def test_update_line_quantity(self):
        line = RecipeIngredient.objects.create(recipe=self.recipe, ingredient=self.egg, quantity=4)
        self.client.force_authenticate(self.owner)
        response = self.client.patch(
            f"/api/recipe-ingredients/{line.pk}/", {"quantity": 5}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        line.refresh_from_db()
        self.assertEqual(line.quantity, 5)

    def test_update_line_to_duplicate_is_rejected(self):
        line = RecipeIngredient.objects.create(recipe=self.recipe, ingredient=self.egg, quantity=4)
        RecipeIngredient.objects.create(recipe=self.recipe, ingredient=self.potato, quantity=500)
        self.client.force_authenticate(self.owner)
        response = self.client.patch(
            f"/api/recipe-ingredients/{line.pk}/", {"ingredient_id": self.potato.pk}, format="json"
        )
        self.assertEqual(response.status_code, 400)

    def test_delete_line(self):
        line = RecipeIngredient.objects.create(recipe=self.recipe, ingredient=self.egg, quantity=4)
        self.client.force_authenticate(self.owner)
        response = self.client.delete(f"/api/recipe-ingredients/{line.pk}/")
        self.assertEqual(response.status_code, 204)
        self.assertEqual(RecipeIngredient.objects.count(), 0)

    def test_recipe_lines_list_is_paginated(self):
        for index in range(11):
            extra = Ingredient.objects.create(name=f"Extra {index}", unit="unidades")
            RecipeIngredient.objects.create(recipe=self.recipe, ingredient=extra, quantity=1)
        first = self.client.get(f"/api/recipes/{self.recipe.pk}/recipe-ingredients/")
        self.assertEqual(first.data["count"], 11)
        self.assertEqual(len(first.data["results"]), 10)
        second = self.client.get(f"/api/recipes/{self.recipe.pk}/recipe-ingredients/?page=2")
        self.assertEqual(len(second.data["results"]), 1)
        self.assertIsNone(second.data["next"])

    def test_non_owner_cannot_touch_lines(self):
        line = RecipeIngredient.objects.create(recipe=self.recipe, ingredient=self.egg, quantity=4)
        client = APIClient()
        client.force_authenticate(self.other)
        response = client.post(
            f"/api/recipes/{self.recipe.pk}/recipe-ingredients/",
            {"ingredient_id": self.potato.pk, "quantity": 1},
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        response = client.patch(
            f"/api/recipe-ingredients/{line.pk}/", {"quantity": 9}, format="json"
        )
        self.assertEqual(response.status_code, 403)
        response = client.delete(f"/api/recipe-ingredients/{line.pk}/")
        self.assertEqual(response.status_code, 403)

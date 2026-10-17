from datetime import date, timedelta

from rest_framework.test import APIClient, APITestCase

from apps.plan.models import Plan, PlanMeal
from apps.recipes.models import Recipe
from apps.user.models import User


class PlanApiTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user_a = User.objects.create_user(
            username="plan_api_a", password="x", country="Venezuela", date_birth=date(1990, 1, 1)
        )
        cls.user_b = User.objects.create_user(
            username="plan_api_b", password="x", country="Venezuela", date_birth=date(1991, 2, 2)
        )
        cls.recipe = Recipe.objects.create(
            name="Tortilla", instructions="Batir y cuajar.", prep_time=0.5, servings=4
        )

    def setUp(self):
        self.client.force_authenticate(self.user_a)

    def test_anonymous_access_is_unauthorized(self):
        response = APIClient().get("/api/plans/")
        self.assertEqual(response.status_code, 401)

    def test_create_plan_without_body_uses_defaults(self):
        response = self.client.post("/api/plans/", {}, format="json")
        self.assertEqual(response.status_code, 201)
        plan = Plan.objects.get(pk=response.data["id"])
        self.assertEqual(plan.end_date, plan.start_date.date() + timedelta(days=7))

    def test_create_plan_with_explicit_start_computes_end(self):
        response = self.client.post(
            "/api/plans/", {"start_date": "2026-11-02T10:00:00Z"}, format="json"
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["end_date"], "2026-11-09")

    def test_payload_user_is_ignored(self):
        response = self.client.post("/api/plans/", {"user": self.user_b.pk}, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Plan.objects.get(pk=response.data["id"]).user, self.user_a)

    def test_list_shows_only_own_plans(self):
        Plan.objects.create(user=self.user_a)
        Plan.objects.create(user=self.user_a)
        Plan.objects.create(user=self.user_b)
        response = self.client.get("/api/plans/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 2)

    def test_foreign_plan_detail_is_404(self):
        foreign = Plan.objects.create(user=self.user_b)
        response = self.client.get(f"/api/plans/{foreign.pk}/")
        self.assertEqual(response.status_code, 404)

    def test_foreign_plan_delete_is_404(self):
        foreign = Plan.objects.create(user=self.user_b)
        response = self.client.delete(f"/api/plans/{foreign.pk}/")
        self.assertEqual(response.status_code, 404)
        self.assertTrue(Plan.objects.filter(pk=foreign.pk).exists())

    def test_patch_own_plan(self):
        plan = Plan.objects.create(user=self.user_a)
        response = self.client.patch(
            f"/api/plans/{plan.pk}/", {"end_date": "2027-01-15"}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["end_date"], "2027-01-15")

    def test_plan_detail_query_count(self):
        plan = Plan.objects.create(user=self.user_a)
        PlanMeal.objects.create(
            plan=plan, recipe=self.recipe, date=plan.end_date, meal_type="lunch"
        )
        with self.assertNumQueries(3):
            response = self.client.get(f"/api/plans/{plan.pk}/")
        self.assertEqual(response.status_code, 200)


class PlanMealApiTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user_a = User.objects.create_user(
            username="meal_api_a", password="x", country="Venezuela", date_birth=date(1990, 1, 1)
        )
        cls.user_b = User.objects.create_user(
            username="meal_api_b", password="x", country="Venezuela", date_birth=date(1991, 2, 2)
        )
        cls.recipe = Recipe.objects.create(
            name="Tortilla", instructions="Batir y cuajar.", prep_time=0.5, servings=4
        )

    def setUp(self):
        self.client.force_authenticate(self.user_a)
        self.plan = Plan.objects.create(user=self.user_a)

    def _meal_payload(self, **overrides):
        payload = {
            "recipe_id": self.recipe.pk,
            "date": str(self.plan.end_date),
            "meal_type": "lunch",
        }
        payload.update(overrides)
        return payload

    def test_create_meal_via_nested_endpoint(self):
        response = self.client.post(
            f"/api/plans/{self.plan.pk}/meals/", self._meal_payload(), format="json"
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["recipe"]["name"], "Tortilla")
        self.assertEqual(response.data["meal_type"], "lunch")

    def test_duplicate_meal_is_rejected(self):
        PlanMeal.objects.create(
            plan=self.plan, recipe=self.recipe, date=self.plan.end_date, meal_type="lunch"
        )
        response = self.client.post(
            f"/api/plans/{self.plan.pk}/meals/", self._meal_payload(), format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("recipe_id", response.data)

    def test_same_recipe_in_different_slot_is_allowed(self):
        first = self.client.post(
            f"/api/plans/{self.plan.pk}/meals/", self._meal_payload(), format="json"
        )
        second = self.client.post(
            f"/api/plans/{self.plan.pk}/meals/",
            self._meal_payload(meal_type="dinner"),
            format="json",
        )
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 201)

    def test_meal_out_of_range_date_is_rejected(self):
        beyond = self.plan.end_date + timedelta(days=1)
        response = self.client.post(
            f"/api/plans/{self.plan.pk}/meals/",
            self._meal_payload(date=str(beyond)),
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("date", response.data)

    def test_meal_before_start_is_rejected(self):
        before = self.plan.start_date.date() - timedelta(days=1)
        response = self.client.post(
            f"/api/plans/{self.plan.pk}/meals/",
            self._meal_payload(date=str(before)),
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("date", response.data)

    def test_meal_with_invalid_type_is_rejected(self):
        response = self.client.post(
            f"/api/plans/{self.plan.pk}/meals/",
            self._meal_payload(meal_type="brunch"),
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("meal_type", response.data)

    def test_meal_on_foreign_plan_is_404(self):
        foreign = Plan.objects.create(user=self.user_b)
        response = self.client.post(
            f"/api/plans/{foreign.pk}/meals/", self._meal_payload(), format="json"
        )
        self.assertEqual(response.status_code, 404)

    def test_foreign_meal_detail_is_404(self):
        foreign = Plan.objects.create(user=self.user_b)
        meal = PlanMeal.objects.create(
            plan=foreign, recipe=self.recipe, date=foreign.end_date, meal_type="lunch"
        )
        response = self.client.get(f"/api/plan-meals/{meal.pk}/")
        self.assertEqual(response.status_code, 404)

    def test_foreign_meal_delete_is_404(self):
        foreign = Plan.objects.create(user=self.user_b)
        meal = PlanMeal.objects.create(
            plan=foreign, recipe=self.recipe, date=foreign.end_date, meal_type="lunch"
        )
        response = self.client.delete(f"/api/plan-meals/{meal.pk}/")
        self.assertEqual(response.status_code, 404)
        self.assertTrue(PlanMeal.objects.filter(pk=meal.pk).exists())

    def test_update_meal_type(self):
        meal = PlanMeal.objects.create(
            plan=self.plan, recipe=self.recipe, date=self.plan.end_date, meal_type="lunch"
        )
        response = self.client.patch(
            f"/api/plan-meals/{meal.pk}/", {"meal_type": "dinner"}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["meal_type"], "dinner")

    def test_delete_meal(self):
        meal = PlanMeal.objects.create(
            plan=self.plan, recipe=self.recipe, date=self.plan.end_date, meal_type="lunch"
        )
        response = self.client.delete(f"/api/plan-meals/{meal.pk}/")
        self.assertEqual(response.status_code, 204)
        self.assertEqual(PlanMeal.objects.count(), 0)

    def test_delete_recipe_in_use_returns_400(self):
        PlanMeal.objects.create(
            plan=self.plan, recipe=self.recipe, date=self.plan.end_date, meal_type="lunch"
        )
        response = self.client.delete(f"/api/recipes/{self.recipe.pk}/")
        self.assertEqual(response.status_code, 400)
        self.assertTrue(Recipe.objects.filter(pk=self.recipe.pk).exists())

    def test_plan_meals_list_is_paginated(self):
        meal_types = ["breakfast", "lunch", "dinner", "snack"]
        for index in range(12):
            PlanMeal.objects.create(
                plan=self.plan,
                recipe=self.recipe,
                date=self.plan.start_date.date() + timedelta(days=index // 4),
                meal_type=meal_types[index % 4],
            )
        first = self.client.get(f"/api/plans/{self.plan.pk}/meals/")
        self.assertEqual(first.data["count"], 12)
        self.assertEqual(len(first.data["results"]), 10)
        second = self.client.get(f"/api/plans/{self.plan.pk}/meals/?page=2")
        self.assertEqual(len(second.data["results"]), 2)

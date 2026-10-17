from datetime import date, timedelta

from django.db import IntegrityError, transaction
from django.db.models import ProtectedError
from django.test import TestCase

from apps.plan.models import Plan, PlanMeal
from apps.recipes.models import Recipe
from apps.user.models import User


class PlanModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="planner", password="x", country="Venezuela", date_birth=date(1990, 1, 1)
        )
        cls.recipe = Recipe.objects.create(
            name="Tortilla", instructions="Batir y cuajar.", prep_time=0.5, servings=4
        )

    def test_end_date_defaults_to_seven_days_after_start(self):
        plan = Plan.objects.create(user=self.user)
        self.assertEqual(plan.end_Date, plan.start_Date.date() + timedelta(days=7))

    def test_explicit_end_date_is_respected(self):
        fixed = date(2030, 1, 1)
        plan = Plan.objects.create(user=self.user, end_Date=fixed)
        self.assertEqual(plan.end_Date, fixed)

    def test_duplicate_meal_in_same_slot_is_rejected(self):
        plan = Plan.objects.create(user=self.user)
        PlanMeal.objects.create(
            plan=plan, recipe=self.recipe, date=plan.end_Date, meal_type="lunch"
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                PlanMeal.objects.create(
                    plan=plan, recipe=self.recipe, date=plan.end_Date, meal_type="lunch"
                )

    def test_same_recipe_in_different_slot_is_allowed(self):
        plan = Plan.objects.create(user=self.user)
        PlanMeal.objects.create(
            plan=plan, recipe=self.recipe, date=plan.end_Date, meal_type="lunch"
        )
        PlanMeal.objects.create(
            plan=plan, recipe=self.recipe, date=plan.end_Date, meal_type="dinner"
        )
        self.assertEqual(plan.meals.count(), 2)

    def test_recipe_in_use_cannot_be_deleted(self):
        plan = Plan.objects.create(user=self.user)
        PlanMeal.objects.create(
            plan=plan, recipe=self.recipe, date=plan.end_Date, meal_type="lunch"
        )
        with self.assertRaises(ProtectedError):
            with transaction.atomic():
                self.recipe.delete()

    def test_deleting_plan_cascades_meals(self):
        plan = Plan.objects.create(user=self.user)
        PlanMeal.objects.create(
            plan=plan, recipe=self.recipe, date=plan.end_Date, meal_type="lunch"
        )
        plan.delete()
        self.assertEqual(PlanMeal.objects.count(), 0)

from django.contrib import admin

from apps.recipes.models import Ingredient, Recipe, Recipe_Ingredient


class RecipeIngredientInline(admin.TabularInline):
    model = Recipe_Ingredient
    extra = 1


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "prep_time", "servings")
    search_fields = ("name",)
    inlines = [RecipeIngredientInline]


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "unit")
    search_fields = ("name",)

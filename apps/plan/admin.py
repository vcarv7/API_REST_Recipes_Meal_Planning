from django.contrib import admin

from apps.plan.models import Plan, PlanMeal


class PlanMealInline(admin.TabularInline):
    model = PlanMeal
    extra = 1


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "start_Date", "end_Date")
    search_fields = ("user__username",)
    date_hierarchy = "start_Date"
    inlines = [PlanMealInline]

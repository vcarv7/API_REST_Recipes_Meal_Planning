from django.db import models
from django.utils import timezone
from apps.user.models import User
from apps.recipes.models import Recipe
from datetime import timedelta

# Create your models here.

class Plan(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='plans')
    start_Date = models.DateTimeField(default=timezone.now)
    end_Date = models.DateField(blank=True, null=True)
    
    #   Sobreescribe el metodo save que django trae por defecto para agregar logica antes de
    #   guardar en la base de datos
    
    def save(self, *args, **kwargs): 
        if not self.end_Date:
            self.end_Date = (self.start_Date + timedelta(days=7)).date()
        
        # Llama al Metodo Padre para que guarde
        super().save( *args, **kwargs) 
        
    def __str__(self):
        return f"{self.user}:{self.start_Date}"


class PlanMeal(models.Model):
    class MealType(models.TextChoices):
        BREAKFAST = "breakfast", "Desayuno"
        LUNCH = "lunch", "Almuerzo"
        DINNER = "dinner", "Cena"
        SNACK = "snack", "Merienda"

    plan = models.ForeignKey(Plan, on_delete=models.CASCADE, related_name="meals")
    recipe = models.ForeignKey(Recipe, on_delete=models.PROTECT, related_name="plan_meals")
    date = models.DateField(help_text="Dia del plan en que se prepara")
    meal_type = models.CharField(max_length=20, choices=MealType.choices)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["plan", "date", "meal_type", "recipe"],
                name="unique_plan_meal",
            )
        ]

    def __str__(self):
        return f"{self.plan}:{self.date}:{self.meal_type}"
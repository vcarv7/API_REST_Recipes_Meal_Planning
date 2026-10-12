from django.db import models

# Create your models here.

class Recipe(models.Model):
    name = models.CharField( max_length=100)
    instructions = models.TextField(max_length=1000)
    prep_time = models.FloatField(help_text="Tiempo en Horas")
    servings =models.PositiveIntegerField(help_text="Numero de Porciones que rinde esta Receta", default=1)
    
    def __str__(self):
        return f"{self.name}"
    
class Ingredient(models.Model):
    name = models.CharField(max_length=50) 
    unit = models.CharField(
        max_length=50, 
        help_text="Unidad: g, ml, tazas, unidades...")
    
    def __str__(self):
        return f"{self.name}"
    
    
class Recipe_Ingredient(models.Model):
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE)
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE)
    
    def __str__(self):
        return f"{self.recipe}:{self.ingredient}"

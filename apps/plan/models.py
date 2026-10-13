from django.db import models
from apps.user.models import User
from datetime import timedelta

# Create your models here.

class Plan(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='plans')
    start_Date = models.DateTimeField(auto_now_add=True)
    end_Date = models.DateField(blank=True, null=True)
    
    #   Sobreescribe el metodo save que django trae por defecto para agregar logica antes de
    #   guardar en la base de datos
    
    def save(self, *args, **kwargs): 
        if not self.end_Date:
            self.end_Date = self.start_Date + timedelta(days=7)
        
        # Lama al Metodo Padre para que guarde
        super().save( *args, **kwargs) 
        
    def __str__(self):
        return f"{self.user}:{self.start_Date}"
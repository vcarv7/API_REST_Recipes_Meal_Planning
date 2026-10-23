from django.db import models
from django.contrib.auth.models import AbstractUser

# Create your models here.

class User(AbstractUser):
    email = models.EmailField(unique=True, null=True, blank=True)
    country = models.CharField(max_length=50, help_text="Pais Natal")
    date_birth = models.DateField(help_text="Fecha de Nacimiento")

    def save(self, *args, **kwargs):
        # Normaliza el email vacio a NULL: la constraint unique permite
        # multiples NULL, pero no multiples cadena vacia.
        if self.email == "":
            self.email = None
        super().save(*args, **kwargs)
from django.db import models
from django.contrib.auth.models import AbstractUser

# Create your models here.

class User(AbstractUser):
    country = models.CharField(max_length=50, help_text="Pais Natal")
    date_birth = models.DateField(help_text="Fecha de Nacimiento")

from django.db import models

from django.contrib.auth.models import AbstractUser
class CustomUser(AbstractUser):
    
    google_id = models.CharField(max_length=255, null=True, blank=True)
    avatar = models.URLField(null=True, blank=True)

# Create your models here.

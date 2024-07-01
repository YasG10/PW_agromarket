from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    is_seller = models.BooleanField(default=False)
    is_buyer = models.BooleanField(default=False)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    address = models.CharField(max_length=255, blank=True, null=True)

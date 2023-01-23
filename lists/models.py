from django.db import models

# Create your models here.
# A model represents the data in an application.

class Item(models.Model):
    text = models.TextField(default='')
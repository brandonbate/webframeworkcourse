from django.db import models

# Create your models here.
# A model represents the data in an application.

class List(models.Model):
    pass

class Item(models.Model):
    text = models.TextField(default='')
    list = models.ForeignKey(List, default=None)
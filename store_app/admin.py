from django.contrib import admin
from .models import Cart, Category, Order, Product

# Register your models here.
admin.site.register(Cart)
admin.site.register(Category)
admin.site.register(Order)
admin.site.register(Product)


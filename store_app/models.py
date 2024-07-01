from decimal import Decimal
from django.db import models
from user.models import User
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from django.utils import timezone

STATUS_CHOICES = (
    ("pending", "Pending"),
    ("completed", "Completed"),
    ("cancelled", "Cancelled"),
)


class Category(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name


class Product(models.Model):
    seller = models.ForeignKey(User, on_delete=models.CASCADE, related_name="products")
    name = models.CharField(max_length=255)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField()
    quantity_available = models.PositiveIntegerField()
    image = models.ImageField(upload_to="products/")

    def __str__(self):
        return self.name


class Order(models.Model):
    buyer = models.ForeignKey(User, related_name="orders", on_delete=models.CASCADE)
    product = models.ForeignKey(Product, related_name="orders", on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    shipping_address = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)


@receiver(post_save, sender=Order)
def update_sales(sender, instance, **kwargs):
    if instance.status == 'completed':
        sales, created = Sales.objects.get_or_create(
            seller=instance.product.seller,
            product=instance.product,
            defaults={'sale_date': timezone.now()}  # Establece la fecha de venta al crear
        )
        sales.total_quantity += instance.quantity
        sales.total_sales += Decimal(instance.quantity) * Decimal(instance.product.price)
        if created:
            sales.sale_date = timezone.now()
        sales.save()


@receiver(pre_delete, sender=Order)
def delete_sales(sender, instance, **kwargs):
    if instance.status == 'completed':
        sales = Sales.objects.get(seller=instance.product.seller, product=instance.product)
        sales.total_quantity -= instance.quantity
        sales.total_sales -= Decimal(instance.quantity) * Decimal(instance.product.price)
        if sales.total_quantity == 0:
            sales.delete()
        else:
            sales.save()


class Cart(models.Model):
    buyer = models.ForeignKey(User, on_delete=models.CASCADE, related_name="cart")
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.product.name} in {self.buyer.username}'s cart"


class Sales(models.Model):
    seller = models.ForeignKey(User, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    total_quantity = models.PositiveIntegerField(default=0)
    total_sales = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    sale_date = models.DateTimeField(default=timezone.now)  # Fecha de la venta

    def __str__(self):
        return f"{self.seller.username} - {self.product.name}"

from django import forms
from .models import Product
from .models import Order
from .models import Cart

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'category', 'price', 'description', 'quantity_available', 'image']




class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['status']




class CartForm(forms.ModelForm):
    class Meta:
        model = Cart
        fields = ['quantity']

# forms.py


class ProductSearchForm(forms.Form):
    query = forms.CharField(label='Buscar')

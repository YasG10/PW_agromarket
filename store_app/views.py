from decimal import Decimal
from django import forms
from django.db import transaction
from django.db.models import Sum, F, Q, FloatField
from django.forms import DecimalField
from django.shortcuts import render, get_object_or_404, redirect
from django.utils.timezone import datetime, localdate
from django.urls import reverse, reverse_lazy
from django.views.generic import (
    ListView,
    CreateView,
    UpdateView,
    DeleteView,
    DetailView,
    FormView,
    View,
)
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.utils.safestring import mark_safe
import json

from .models import Order, Product, Cart, Sales
from .forms import OrderForm, ProductForm, CartForm, ProductSearchForm
from django.utils.timezone import now
from django.views.generic import TemplateView


class SellerRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_seller


class BuyerRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_buyer


class DailySalesView(TemplateView):
    template_name = 'store_app/daily_sales.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = localdate()  # Asegúrate de que la fecha es local

        # Anotando tanto el total en dinero como la cantidad de productos vendidos
        daily_sales = Sales.objects.filter(sale_date__date=today).annotate(
            total_daily_sales=Sum('total_sales'),
            total_daily_quantity=Sum('total_quantity')  # Suma de cantidades vendidas
        )

        context['daily_sales'] = daily_sales
        return context

class MonthlySalesView(TemplateView):
    template_name = 'store_app/monthly_sales.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = localdate() 
       
        monthly_sales = Sales.objects.filter(sale_date__month=today.month, sale_date__year=today.year).annotate(
            total_monthly_sales=Sum('total_sales'),
            total_monthly_quantity=Sum('total_quantity')  
        )

        context['monthly_sales'] = monthly_sales
        return context


class TrendingProductsView(TemplateView):
    template_name = "store_app/trending_products.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Anotando tanto el total en dinero como la cantidad de productos vendidos
        top_products = Sales.objects.values('product__name', 'product__id') \
            .annotate(total_quantity=Sum('total_quantity'), total_sales=Sum('total_sales')) \
            .order_by('-total_quantity')[:10]
        
        context["top_products"] = top_products
        return context


class ProductSearchView(ListView):
    model = Product
    template_name = "store_app/product_search.html"
    context_object_name = "products"

    def get_queryset(self):
        form = ProductSearchForm(self.request.GET)
        if form.is_valid():
            return Product.objects.filter(name__icontains=form.cleaned_data["query"])
        return Product.objects.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["search_form"] = ProductSearchForm(self.request.GET or None)
        return context


class SalesReportView(LoginRequiredMixin, SellerRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        total_sales_float = (
            Order.objects.filter(product__seller=request.user, status="completed")
            .annotate(total_sale=F("quantity") * F("product__price"))
            .aggregate(total=Sum("total_sale", output_field=FloatField()))["total"]
            or 0.0
        )

        total_sales = Decimal(total_sales_float).quantize(Decimal("0.00"))

        product_sales = (
            Order.objects.filter(product__seller=request.user, status="completed")
            .values("product__name")
            .annotate(total_quantity=Sum("quantity"))
            .order_by("-total_quantity")
        )

        products = [sale["product__name"] for sale in product_sales]
        quantities = [sale["total_quantity"] for sale in product_sales]

        context = {
            "total_sales": total_sales,
            "products": mark_safe(json.dumps(products)),
            "quantities": mark_safe(json.dumps(quantities)),
            "product_sales": product_sales,
        }
        return render(request, "store_app/sales_report.html", context)


class ProductListView(LoginRequiredMixin, SellerRequiredMixin, ListView):
    model = Product
    template_name = "store_app/product_list.html"

    def get_queryset(self):
        return Product.objects.filter(seller=self.request.user)


class ProductCreateView(LoginRequiredMixin, SellerRequiredMixin, CreateView):
    model = Product
    form_class = ProductForm
    template_name = "store_app/product_form.html"
    success_url = "/store/products/"

    def form_valid(self, form):
        form.instance.seller = self.request.user
        return super().form_valid(form)


class ProductUpdateView(LoginRequiredMixin, SellerRequiredMixin, UpdateView):
    model = Product
    form_class = ProductForm
    template_name = "store_app/product_form.html"
    success_url = "/store/products/"


class ProductDeleteView(LoginRequiredMixin, SellerRequiredMixin, DeleteView):
    model = Product
    template_name = "store_app/product_confirm_delete.html"
    success_url = "/store/products/"

    def get_queryset(self):
        return Product.objects.filter(seller=self.request.user)


class OrderCreateView(LoginRequiredMixin, BuyerRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        cart_items = Cart.objects.filter(buyer=request.user)
        total_cost = sum(
            Decimal(item.product.price) * Decimal(item.quantity) for item in cart_items
        )

        if request.user.balance < total_cost:
            messages.error(request, "Insufficient balance to complete the purchase.")
            return redirect("cart_list")

        for item in cart_items:
            product = item.product
            if item.quantity > product.quantity_available:
                messages.error(
                    request, f"Insufficient quantity available for {product.name}."
                )
                return redirect("cart_list")

        for item in cart_items:
            product = item.product
            product.quantity_available -= item.quantity
            product.save()

            Order.objects.create(
                buyer=request.user,
                product=product,
                quantity=item.quantity,
                shipping_address=request.user.address,
                status="pending",
            )
            item.delete()

        request.user.balance -= total_cost
        request.user.save()

        messages.success(request, "Order placed successfully.")
        return redirect("product_public_list")


class OrderDeleteView(LoginRequiredMixin, SellerRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        order_id = kwargs.get("pk")
        order = get_object_or_404(Order, pk=order_id)

        product = order.product
        product.quantity_available += order.quantity
        product.save()

        order.buyer.balance += order.quantity * product.price
        order.buyer.save()

        order.delete()
        messages.success(request, "Order deleted successfully.")
        return redirect("order_list")


class OrderConfirmDeleteView(LoginRequiredMixin, SellerRequiredMixin, DeleteView):
    model = Order
    template_name = "store_app/order_confirm_delete.html"
    success_url = "/store/orders/"


class OrderListView(LoginRequiredMixin, SellerRequiredMixin, ListView):
    model = Order
    template_name = "store_app/order_list.html"

    def get_queryset(self):
        return Order.objects.filter(product__seller=self.request.user)


class OrderUpdateView(LoginRequiredMixin, SellerRequiredMixin, UpdateView):
    model = Order
    form_class = OrderForm
    template_name = "store_app/order_form.html"
    success_url = reverse_lazy("order_list")

    def form_valid(self, form):
        order = form.save(commit=False)
        original_status = Order.objects.get(pk=order.pk).status

        with transaction.atomic():
            if original_status != "cancelled" and order.status == "cancelled":
                order.product.quantity_available += order.quantity
                order.product.save()

                order.buyer.balance += order.quantity * order.product.price
                order.buyer.save()

                try:
                    sales = Sales.objects.get(
                        seller=order.product.seller, product=order.product
                    )
                    sales.total_quantity -= order.quantity
                    sales.total_sales -= Decimal(order.quantity) * Decimal(
                        order.product.price
                    )
                    if sales.total_quantity == 0:
                        sales.delete()
                    else:
                        sales.save()
                except Sales.DoesNotExist:
                    messages.warning(
                        self.request,
                        "No associated sales record found. Sales record not updated.",
                    )

            if order.status == "completed":
                messages.success(
                    self.request, "Order completed and deleted successfully."
                )
                order.save()
                return redirect(self.success_url)

            order.save()

        messages.success(self.request, "Order updated successfully.")
        return super().form_valid(form)


class CartListView(LoginRequiredMixin, ListView):
    model = Cart
    template_name = "store_app/cart_list.html"

    def get_queryset(self):
        return Cart.objects.filter(buyer=self.request.user)


class CartAddView(LoginRequiredMixin, CreateView):
    model = Cart
    fields = ["product", "quantity"]
    template_name = "store_app/cart_form.html"
    success_url = "/store/cart/"

    def form_valid(self, form):
        form.instance.buyer = self.request.user
        return super().form_valid(form)


class CartDeleteView(LoginRequiredMixin, DeleteView):
    model = Cart
    template_name = "store_app/cart_confirm_delete.html"
    success_url = "/store/cart/"

    def get_queryset(self):
        return Cart.objects.filter(buyer=self.request.user)


class CheckoutView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        cart_items = Cart.objects.filter(buyer=request.user)
        total_cost = sum(item.product.price * item.quantity for item in cart_items)

        if request.user.balance < total_cost:
            return redirect("cart_list")

        for item in cart_items:
            Order.objects.create(
                buyer=request.user,
                product=item.product,
                quantity=item.quantity,
                shipping_address=request.user.address,
                status="pending",
            )
            item.product.quantity_available -= item.quantity
            item.product.save()
            item.delete()

        request.user.balance -= total_cost
        request.user.save()

        return redirect("order_list")


from django.db.models import Q


class ProductPublicListView(ListView):
    model = Product
    template_name = "store_app/product_public_list.html"
    context_object_name = "products"

    def get_queryset(self):
        queryset = super().get_queryset()
        query = self.request.GET.get("q")
        if query:
            queryset = queryset.filter(
                Q(name__icontains=query) | Q(description__icontains=query)
            )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["search_query"] = self.request.GET.get("q", "")
        return context


class ProductDetailView(DetailView, FormView):
    model = Product
    template_name = "store_app/product_detail.html"
    form_class = CartForm

    def get_success_url(self):
        return reverse("product_detail", kwargs={"pk": self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form"] = CartForm(initial={"product": self.object})
        return context

    def form_valid(self, form):
        self.object = self.get_object()
        cart_item, created = Cart.objects.get_or_create(
            buyer=self.request.user,
            product=self.object,
            defaults={"quantity": form.cleaned_data["quantity"]},
        )
        if not created:
            cart_item.quantity += form.cleaned_data["quantity"]
            cart_item.save()
        return super().form_valid(form)

from django.urls import path
from .views import (
    CartAddView,
    CartDeleteView,
    CartListView,
    CheckoutView,
    DailySalesView,
    MonthlySalesView,
    OrderConfirmDeleteView,
    OrderCreateView,
    OrderDeleteView,
    ProductDetailView,
    ProductListView,
    ProductCreateView,
    ProductPublicListView,
    ProductUpdateView,
    ProductDeleteView,
    OrderListView,
    OrderUpdateView,
    SalesReportView,
    ProductSearchView,
    TrendingProductsView,
)


urlpatterns = [
    path("products/", ProductListView.as_view(), name="product_list"),
    path("products/add/", ProductCreateView.as_view(), name="product_add"),
    path("products/<int:pk>/edit/", ProductUpdateView.as_view(), name="product_edit"),
    path(
        "products/<int:pk>/delete/", ProductDeleteView.as_view(), name="product_delete"
    ),
    path("orders/", OrderListView.as_view(), name="order_list"),
    path("orders/<int:pk>/update/", OrderUpdateView.as_view(), name="order_update"),
    path("cart/", CartListView.as_view(), name="cart_list"),
    path("cart/add/", CartAddView.as_view(), name="cart_add"),
    path("cart/<int:pk>/delete/", CartDeleteView.as_view(), name="cart_delete"),
    path("checkout/", CheckoutView.as_view(), name="checkout"),
    path("products/all/", ProductPublicListView.as_view(), name="product_public_list"),
    path("products/<int:pk>/", ProductDetailView.as_view(), name="product_detail"),
    path("order/create/", OrderCreateView.as_view(), name="order_create"),
    path('orders/delete/<int:pk>/', OrderDeleteView.as_view(), name='order_delete'),
    path('orders/confirm_delete/<int:pk>/', OrderConfirmDeleteView.as_view(), name='order_confirm_delete'),
    path('sales_report/', SalesReportView.as_view(), name='sales_report'),
    path('search/', ProductSearchView.as_view(), name='product_search'),
    path('sales/daily/', DailySalesView.as_view(), name='daily_sales'),
    path('sales/monthly/', MonthlySalesView.as_view(), name='monthly_sales'),
    path('trending_products/', TrendingProductsView.as_view(), name='trending_products'),
    
]

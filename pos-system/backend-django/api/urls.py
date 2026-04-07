from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

urlpatterns = [
    # ── Authentication ──────────────────────────────────────────────────────
    path('auth/register/', views.RegisterView.as_view(), name='register'),
    path('auth/login/', views.LoginView.as_view(), name='login'),
    path('auth/logout/', views.LogoutView.as_view(), name='logout'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/profile/', views.UserProfileView.as_view(), name='profile'),
    path('auth/verify/', views.VerifyTokenView.as_view(), name='token_verify'),

    # ── Products ────────────────────────────────────────────────────────────
    path('products/', views.ProductListView.as_view(), name='product-list'),
    path('products/low-stock/', views.LowStockProductsView.as_view(), name='product-low-stock'),
    path('products/barcode/<str:barcode>/', views.ProductByBarcodeView.as_view(), name='product-barcode'),
    path('products/<int:pk>/', views.ProductDetailView.as_view(), name='product-detail'),

    # ── Categories ──────────────────────────────────────────────────────────
    path('categories/', views.CategoryListView.as_view(), name='category-list'),

    # ── Transactions ────────────────────────────────────────────────────────
    path('transactions/', views.TransactionListView.as_view(), name='transaction-list'),
    path('transactions/stats/today/', views.TransactionStatsTodayView.as_view(), name='transaction-stats-today'),
    path('transactions/range/', views.TransactionByDateRangeView.as_view(), name='transaction-range'),
    path('transactions/customer/<int:customer_id>/', views.TransactionByCustomerView.as_view(), name='transaction-by-customer'),
    path('transactions/<int:pk>/', views.TransactionDetailView.as_view(), name='transaction-detail'),
    path('transactions/<int:pk>/void/', views.VoidTransactionView.as_view(), name='transaction-void'),
    path('transactions/<int:pk>/receipt/', views.SendReceiptView.as_view(), name='transaction-receipt'),

    # ── Inventory ───────────────────────────────────────────────────────────
    path('inventory/', views.InventoryListView.as_view(), name='inventory-list'),

    # ── Customers ───────────────────────────────────────────────────────────
    path('customers/', views.CustomerListView.as_view(), name='customer-list'),
    path('customers/loyalty/<str:loyalty_number>/', views.CustomerByLoyaltyView.as_view(), name='customer-loyalty'),
    path('customers/user/<int:user_id>/', views.CustomerByUserIdView.as_view(), name='customer-by-user'),
    path('customers/<int:pk>/', views.CustomerDetailView.as_view(), name='customer-detail'),
    path('customers/<int:pk>/add-points/', views.AddLoyaltyPointsView.as_view(), name='customer-add-points'),

    # ── Payment Requests (ported from Spring Boot) ──────────────────────────
    path('payment-requests/', views.PaymentRequestListView.as_view(), name='payment-request-list'),
    path('payment-requests/active/<int:customer_id>/', views.PaymentRequestActiveView.as_view(), name='payment-request-active'),
    path('payment-requests/<str:request_id>/', views.PaymentRequestDetailView.as_view(), name='payment-request-detail'),
    path('payment-requests/<str:request_id>/status/', views.PaymentRequestStatusView.as_view(), name='payment-request-status'),
]
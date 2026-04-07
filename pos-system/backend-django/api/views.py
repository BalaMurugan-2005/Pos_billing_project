from rest_framework import generics, permissions, status, filters
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework_simplejwt.tokens import RefreshToken
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Sum, Count
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from datetime import datetime, timedelta
from .models import *
from .serializers import *
import logging

logger = logging.getLogger(__name__)

class RegisterView(generics.CreateAPIView):
    """User registration view"""
    queryset = User.objects.all()
    serializer_class = UserCreateSerializer
    permission_classes = [permissions.AllowAny]

class LoginView(APIView):
    """User login view"""
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user': UserSerializer(user).data
        })

class LogoutView(APIView):
    """User logout view"""
    def post(self, request):
        try:
            refresh_token = request.data["refresh"]
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response(status=status.HTTP_205_RESET_CONTENT)
        except Exception as e:
            return Response(status=status.HTTP_400_BAD_REQUEST)

class UserProfileView(generics.RetrieveUpdateAPIView):
    """User profile view"""
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        return self.request.user

import jwt
from django.conf import settings

class VerifyTokenView(APIView):
    """Verify JWT token and roles for Spring Boot integration"""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        token = request.data.get('token')
        if not token:
            return Response({'valid': False, 'error': 'Token not provided'}, status=status.HTTP_400_BAD_REQUEST)

        # Use the same secret as Spring Boot — read from settings (JWT_SECRET_KEY env var)
        from django.conf import settings as django_settings
        secret = django_settings.SIMPLE_JWT.get('SIGNING_KEY', '')

        try:
            # Verify validity and expiry
            decoded = jwt.decode(token, secret, algorithms=['HS256'])
            
            # Verify role permissions
            roles = decoded.get('role', [])
            role_names = [r.get('authority', '') if isinstance(r, dict) else r for r in roles]
            
            # Check user role exists
            user_id = decoded.get('user_id')
            username = decoded.get('sub')
            try:
                if user_id:
                    user_obj = User.objects.get(id=user_id)
                elif username:
                    user_obj = User.objects.get(username=username)
                else:
                    raise User.DoesNotExist
                
                user_role = user_obj.role
                resolved_username = user_obj.username
            except User.DoesNotExist:
                return Response({'valid': False, 'error': 'User not found'}, status=status.HTTP_401_UNAUTHORIZED)

            return Response({
                'valid': True,
                'username': resolved_username,
                'roles': role_names,
                'user_role': user_role
            })
        except jwt.ExpiredSignatureError:
            return Response({'valid': False, 'error': 'Token has expired'}, status=status.HTTP_401_UNAUTHORIZED)
        except jwt.InvalidTokenError as e:
            return Response({'valid': False, 'error': f'Invalid token: {str(e)}'}, status=status.HTTP_401_UNAUTHORIZED)

# Product Views
class ProductListView(generics.ListCreateAPIView):
    """List and create products"""
    queryset = Product.objects.filter(is_active=True)
    serializer_class = ProductSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category', 'is_weighted', 'brand']
    search_fields = ['name', 'barcode', 'description']
    ordering_fields = ['name', 'price', 'stock_quantity', 'created_at']
    
    def get_permissions(self):
        if self.request.method == 'POST':
            return [permissions.IsAuthenticated(), permissions.IsAdminUser()]
        return [permissions.IsAuthenticated()]

class ProductDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, delete product"""
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_permissions(self):
        if self.request.method in ['PUT', 'PATCH', 'DELETE']:
            return [permissions.IsAuthenticated(), permissions.IsAdminUser()]
        return [permissions.IsAuthenticated()]
    
    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save()

class ProductByBarcodeView(generics.RetrieveAPIView):
    """Get product by barcode"""
    queryset = Product.objects.filter(is_active=True)
    serializer_class = ProductSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'barcode'

class LowStockProductsView(generics.ListAPIView):
    """Get low stock products"""
    serializer_class = ProductSerializer
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]
    
    def get_queryset(self):
        return Product.objects.filter(
            stock_quantity__lte=models.F('min_stock_level'),
            is_active=True
        )

# Category Views
class CategoryListView(generics.ListCreateAPIView):
    """List and create categories"""
    queryset = Category.objects.filter(is_active=True)
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'description']
    
    def get_permissions(self):
        if self.request.method == 'POST':
            return [permissions.IsAuthenticated(), permissions.IsAdminUser()]
        return [permissions.IsAuthenticated()]

# Transaction Views
class TransactionListView(generics.ListCreateAPIView):
    """List and create transactions"""
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['status', 'payment_method', 'cashier', 'customer']
    ordering_fields = ['created_at', 'total']
    
    def perform_create(self, serializer):
        serializer.save(cashier=self.request.user)

class TransactionDetailView(generics.RetrieveAPIView):
    """Retrieve transaction"""
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer
    permission_classes = [permissions.IsAuthenticated]

class VoidTransactionView(APIView):
    """Void a transaction"""
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]
    
    def post(self, request, pk):
        try:
            transaction = Transaction.objects.get(pk=pk)
            if transaction.status != 'completed':
                return Response(
                    {'error': 'Only completed transactions can be voided'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            transaction.status = 'void'
            transaction.save()
            
            # Restore inventory
            for item in transaction.items.all():
                Inventory.objects.create(
                    product=item.product,
                    quantity_change=item.quantity,
                    movement_type='return',
                    reason=f"Void transaction: {transaction.transaction_number}",
                    previous_quantity=item.product.stock_quantity,
                    performed_by=request.user,
                    reference_number=transaction.transaction_number
                )
            
            return Response({'message': 'Transaction voided successfully'})
            
        except Transaction.DoesNotExist:
            return Response(
                {'error': 'Transaction not found'},
                status=status.HTTP_404_NOT_FOUND
            )

# Inventory Views
class InventoryListView(generics.ListCreateAPIView):
    """List and create inventory movements"""
    queryset = Inventory.objects.all()
    serializer_class = InventorySerializer
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['movement_type', 'product']
    ordering_fields = ['created_at']
    
    def perform_create(self, serializer):
        serializer.save(performed_by=self.request.user)

# Customer Views
class CustomerListView(generics.ListCreateAPIView):
    """List and create customers"""
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['user__first_name', 'user__last_name', 'user__email', 'loyalty_number']
    ordering_fields = ['created_at', 'loyalty_points', 'total_purchases']
    
    def get_permissions(self):
        if self.request.method == 'POST':
            return [permissions.IsAuthenticated(), permissions.IsAdminUser()]
        return [permissions.IsAuthenticated()]

class CustomerDetailView(generics.RetrieveUpdateAPIView):
    """Retrieve, update customer"""
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_permissions(self):
        if self.request.method in ['PUT', 'PATCH']:
            return [permissions.IsAuthenticated(), permissions.IsAdminUser()]
        return [permissions.IsAuthenticated()]

class CustomerByLoyaltyView(generics.RetrieveAPIView):
    """Get customer by loyalty number"""
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'loyalty_number'

class CustomerByUserIdView(generics.RetrieveAPIView):
    """Get customer by user ID"""
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'user_id'
    lookup_url_kwarg = 'user_id'
    
    def get_queryset(self):
        return Customer.objects.filter(user_id=self.kwargs.get('user_id'))

class AddLoyaltyPointsView(APIView):
    """Add loyalty points to customer"""
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]
    
    def post(self, request, pk):
        try:
            customer = Customer.objects.get(pk=pk)
            points = request.data.get('points', 0)
            
            customer.loyalty_points += points
            customer.save()
            
            return Response({
                'message': f'Added {points} points successfully',
                'total_points': customer.loyalty_points
            })
            
        except Customer.DoesNotExist:
            return Response(
                {'error': 'Customer not found'},
                status=status.HTTP_404_NOT_FOUND
            )


# ─────────────────────────────────────────────────────────────────────────────
# Transaction Extended Views (ported from Spring Boot)
# ─────────────────────────────────────────────────────────────────────────────

class TransactionStatsTodayView(APIView):
    """Return today's total sales and transaction count — replaces Spring Boot /transactions/stats/today"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        today = timezone.now().date()
        start = timezone.make_aware(datetime.combine(today, datetime.min.time()))
        end = timezone.make_aware(datetime.combine(today, datetime.max.time()))

        agg = Transaction.objects.filter(
            created_at__range=[start, end],
            status='completed'
        ).aggregate(sales=Sum('total'), count=Count('id'))

        return Response({
            'sales': float(agg['sales'] or 0),
            'count': agg['count'] or 0,
        })


class TransactionByCustomerView(generics.ListAPIView):
    """List all transactions for a specific customer — replaces Spring Boot /transactions/customer/{customerId}"""
    serializer_class = TransactionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        customer_id = self.kwargs.get('customer_id')
        return Transaction.objects.filter(customer_id=customer_id).order_by('-created_at')


class TransactionByDateRangeView(generics.ListAPIView):
    """Get transactions between two ISO datetimes — replaces Spring Boot /transactions/range"""
    serializer_class = TransactionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        start_str = self.request.query_params.get('start')
        end_str = self.request.query_params.get('end')
        qs = Transaction.objects.all()
        if start_str:
            try:
                start = datetime.fromisoformat(start_str.replace('Z', '+00:00'))
                qs = qs.filter(created_at__gte=start)
            except ValueError:
                pass
        if end_str:
            try:
                end = datetime.fromisoformat(end_str.replace('Z', '+00:00'))
                qs = qs.filter(created_at__lte=end)
            except ValueError:
                pass
        return qs.order_by('-created_at')


class SendReceiptView(APIView):
    """Email a transaction receipt — replaces Spring Boot /transactions/{id}/receipt"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        try:
            transaction = Transaction.objects.select_related(
                'cashier', 'customer__user'
            ).prefetch_related('items__product').get(pk=pk)
        except Transaction.DoesNotExist:
            return Response({'error': 'Transaction not found'}, status=status.HTTP_404_NOT_FOUND)

        email = request.data.get('email', '')
        if not email:
            return Response({'error': 'Email is required'}, status=status.HTTP_400_BAD_REQUEST)

        # Build receipt body
        items_text = '\n'.join([
            f"  {item.product.name if item.product else 'Item'} x{item.quantity} @ ₹{item.price} = ₹{item.subtotal}"
            for item in transaction.items.all()
        ])

        body = (
            f"Thank you for your purchase!\n\n"
            f"Transaction: {transaction.transaction_number}\n"
            f"Date: {transaction.created_at.strftime('%Y-%m-%d %H:%M')}\n"
            f"Cashier: {transaction.cashier.get_full_name() if transaction.cashier else 'N/A'}\n\n"
            f"Items:\n{items_text}\n\n"
            f"Subtotal : ₹{transaction.subtotal}\n"
            f"Tax      : ₹{transaction.tax}\n"
            f"Discount : ₹{transaction.discount}\n"
            f"Total    : ₹{transaction.total}\n"
            f"Payment  : {transaction.payment_method.upper()}\n\n"
            f"Thank you for shopping with us!"
        )

        try:
            send_mail(
                subject=f'Receipt — {transaction.transaction_number}',
                message=body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=False,
            )
            return Response({'message': f'Receipt sent successfully to {email}'})
        except Exception as e:
            logger.error(f'Failed to send receipt email: {e}')
            return Response({'error': 'Failed to send email'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ─────────────────────────────────────────────────────────────────────────────
# Payment Request Views (ported from Spring Boot)
# ─────────────────────────────────────────────────────────────────────────────

class PaymentRequestListView(APIView):
    """Create a new request (cashier/admin) or list all pending requests (admin/cashier)"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        requests = PaymentRequest.objects.filter(status='PENDING')
        serializer = PaymentRequestSerializer(requests, many=True)
        return Response(serializer.data)

    def post(self, request):
        customer_id = request.data.get('customerId')
        amount = request.data.get('amount')
        method = request.data.get('method', 'CARD')

        if not customer_id or not amount:
            return Response(
                {'error': 'customerId and amount are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Resolve customer
        customer = None
        try:
            customer = Customer.objects.get(user_id=customer_id)
        except Customer.DoesNotExist:
            # Try by customer pk
            try:
                customer = Customer.objects.get(pk=customer_id)
            except Customer.DoesNotExist:
                pass

        pay_request = PaymentRequest.objects.create(
            customer=customer,
            cashier=request.user,
            amount=amount,
            method=method,
            status='PENDING',
        )
        serializer = PaymentRequestSerializer(pay_request)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class PaymentRequestActiveView(APIView):
    """Get PENDING payment requests for a specific customer (by their user ID)"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, customer_id):
        try:
            customer = Customer.objects.get(user_id=customer_id)
        except Customer.DoesNotExist:
            try:
                customer = Customer.objects.get(pk=customer_id)
            except Customer.DoesNotExist:
                return Response([], status=status.HTTP_200_OK)

        requests = PaymentRequest.objects.filter(customer=customer, status='PENDING')
        serializer = PaymentRequestSerializer(requests, many=True)
        return Response(serializer.data)


class PaymentRequestDetailView(APIView):
    """Get a specific payment request by its request_id string"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, request_id):
        try:
            pay_request = PaymentRequest.objects.get(request_id=request_id)
        except PaymentRequest.DoesNotExist:
            return Response({'error': 'Request not found'}, status=status.HTTP_404_NOT_FOUND)
        serializer = PaymentRequestSerializer(pay_request)
        return Response(serializer.data)


class PaymentRequestStatusView(APIView):
    """Update the status of a payment request (COMPLETED / DECLINED / EXPIRED)"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, request_id):
        try:
            pay_request = PaymentRequest.objects.get(request_id=request_id)
        except PaymentRequest.DoesNotExist:
            return Response({'error': 'Request not found'}, status=status.HTTP_404_NOT_FOUND)

        new_status = request.data.get('status')
        valid_statuses = ['PENDING', 'COMPLETED', 'DECLINED', 'EXPIRED']
        if new_status not in valid_statuses:
            return Response(
                {'error': f'Invalid status. Must be one of {valid_statuses}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        pay_request.status = new_status
        pay_request.save()
        serializer = PaymentRequestSerializer(pay_request)
        return Response(serializer.data)
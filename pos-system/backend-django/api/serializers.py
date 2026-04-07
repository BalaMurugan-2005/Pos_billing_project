from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from .models import *
import re

class UserSerializer(serializers.ModelSerializer):
    """User serializer"""
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'full_name', 
                  'phone', 'role', 'profile_picture', 'is_active', 'date_joined', 'last_login']
        read_only_fields = ['id', 'date_joined', 'last_login']

    def get_full_name(self, obj):
        return obj.get_full_name()

    def to_representation(self, instance):
        """Map ROLE_* to frontend roles"""
        data = super().to_representation(instance)
        role_map = {
            'ROLE_ADMIN': 'admin',
            'ROLE_CASHIER': 'cashier',
            'ROLE_CUSTOMER': 'customer',
        }
        data['role'] = role_map.get(instance.role, 'customer')
        return data

class UserCreateSerializer(serializers.ModelSerializer):
    """User creation serializer"""
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=False)  # optional: frontend validates client-side
    name = serializers.CharField(write_only=True, required=False, default='')  # frontend sends 'name'
    role = serializers.CharField(required=False, default='customer')  # Accept any string, validate in validate()
    phone = serializers.CharField(required=False, allow_blank=True)  # Make phone optional

    class Meta:
        model = User
        fields = ['username', 'password', 'password2', 'name', 'email', 'first_name', 'last_name', 'phone', 'role']

    def validate(self, attrs):
        password2 = attrs.get('password2')
        if password2 and attrs['password'] != password2:
            raise serializers.ValidationError({"password": "Password fields didn't match."})

        # Split 'name' → first_name / last_name if provided
        name = attrs.pop('name', '')
        if name and not attrs.get('first_name'):
            parts = name.strip().split(' ', 1)
            attrs['first_name'] = parts[0]
            attrs['last_name'] = parts[1] if len(parts) > 1 else ''

        # Normalise role to match ROLE_CHOICES (accept lowercase, convert to uppercase)
        if 'role' in attrs:
            role = attrs['role'].lower().strip()
            role_map = {
                'admin': 'ROLE_ADMIN',
                'cashier': 'ROLE_CASHIER',
                'customer': 'ROLE_CUSTOMER',
            }
            attrs['role'] = role_map.get(role, 'ROLE_CUSTOMER')

        # Remove phone if empty (optional field)
        if not attrs.get('phone'):
            attrs.pop('phone', None)

        return attrs

    def create(self, validated_data):
        validated_data.pop('password2', None)
        user = User.objects.create_user(**validated_data)
        return user

class LoginSerializer(serializers.Serializer):
    """Login serializer"""
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)
    
    def validate(self, data):
        username = data.get('username')
        password = data.get('password')
        
        if username and password:
            user = None
            # Try to resolve actual user model based on email or username
            try:
                if '@' in username:
                    user_obj = User.objects.get(email=username)
                else:
                    user_obj = User.objects.get(username=username)
                
                # Use authenticate with the correct kwarg (email, which is USERNAME_FIELD)
                user = authenticate(request=self.context.get('request'), 
                                  email=user_obj.email, password=password)
            except User.DoesNotExist:
                pass

            if not user:
                raise serializers.ValidationError({"message": "Invalid username or password."})
            if not user.is_active:
                raise serializers.ValidationError({"message": "User account is disabled."})
        else:
            raise serializers.ValidationError({"message": "Must include username and password."})
        
        data['user'] = user
        return data

class CustomerSerializer(serializers.ModelSerializer):
    """Customer serializer"""
    user_details = UserSerializer(source='user', read_only=True)
    
    class Meta:
        model = Customer
        fields = ['id', 'user', 'user_details', 'loyalty_number', 'loyalty_points', 
                  'tier', 'qr_code', 'preferred_payment_method', 'date_of_birth',
                  'anniversary_date', 'newsletter_subscription', 'total_purchases',
                  'last_purchase_date', 'created_at']
        read_only_fields = ['id', 'loyalty_number', 'loyalty_points', 'qr_code', 
                           'total_purchases', 'created_at']

class CategorySerializer(serializers.ModelSerializer):
    """Category serializer"""
    subcategories = serializers.SerializerMethodField()
    
    class Meta:
        model = Category
        fields = ['id', 'name', 'description', 'parent', 'subcategories', 'image', 'is_active', 'created_at']
        read_only_fields = ['id', 'created_at']
    
    def get_subcategories(self, obj):
        if obj.subcategories.exists():
            return CategorySerializer(obj.subcategories.all(), many=True).data
        return []

class ProductSerializer(serializers.ModelSerializer):
    """Product serializer"""
    category_name = serializers.CharField(source='category.name', read_only=True)
    is_low_stock = serializers.BooleanField(read_only=True)
    is_out_of_stock = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Product
        fields = ['id', 'name', 'barcode', 'description', 'category', 'category_name',
                  'price', 'cost_price', 'tax_rate', 'stock_quantity', 'min_stock_level',
                  'max_stock_level', 'unit', 'is_weighted', 'price_per_kg', 'brand',
                  'image', 'is_active', 'is_low_stock', 'is_out_of_stock', 'created_at']
        read_only_fields = ['id', 'created_at']
    
    def validate_barcode(self, value):
        if Product.objects.filter(barcode=value).exists():
            raise serializers.ValidationError("Product with this barcode already exists.")
        return value

class InventorySerializer(serializers.ModelSerializer):
    """Inventory serializer"""
    product_name = serializers.CharField(source='product.name', read_only=True)
    performed_by_name = serializers.CharField(source='performed_by.get_full_name', read_only=True)
    
    class Meta:
        model = Inventory
        fields = ['id', 'product', 'product_name', 'quantity_change', 'movement_type',
                  'reason', 'previous_quantity', 'new_quantity', 'performed_by',
                  'performed_by_name', 'reference_number', 'notes', 'created_at']
        read_only_fields = ['id', 'previous_quantity', 'new_quantity', 'created_at']

class TransactionItemSerializer(serializers.ModelSerializer):
    """Transaction item serializer"""
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_barcode = serializers.CharField(source='product.barcode', read_only=True)
    
    class Meta:
        model = TransactionItem
        fields = ['id', 'product', 'product_name', 'product_barcode', 'quantity',
                  'weight', 'price', 'subtotal', 'tax']

class TransactionSerializer(serializers.ModelSerializer):
    """Transaction serializer"""
    items = TransactionItemSerializer(many=True)
    cashier_name = serializers.CharField(source='cashier.get_full_name', read_only=True)
    customer_name = serializers.CharField(source='customer.user.get_full_name', read_only=True)
    
    class Meta:
        model = Transaction
        fields = ['id', 'transaction_number', 'cashier', 'cashier_name', 'customer',
                  'customer_name', 'subtotal', 'tax', 'discount', 'total',
                  'payment_method', 'paid_amount', 'change_amount', 'status',
                  'notes', 'items', 'created_at']
        read_only_fields = ['id', 'transaction_number', 'created_at']
    
    def create(self, validated_data):
        items_data = validated_data.pop('items')
        transaction = Transaction.objects.create(**validated_data)
        
        for item_data in items_data:
            TransactionItem.objects.create(transaction=transaction, **item_data)
            
            # Update inventory
            product = item_data['product']
            Inventory.objects.create(
                product=product,
                quantity_change=-item_data['quantity'],
                movement_type='sale',
                reason=f"Transaction: {transaction.transaction_number}",
                previous_quantity=product.stock_quantity,
                performed_by=validated_data.get('cashier'),
                reference_number=transaction.transaction_number
            )
        
        # Update customer total purchases
        if transaction.customer:
            customer = transaction.customer
            customer.total_purchases += transaction.total
            customer.last_purchase_date = timezone.now()
            customer.save()
            
            # Update loyalty points (1 point per dollar spent)
            points_earned = int(transaction.total)
            customer.loyalty_points += points_earned
            customer.save()
        
        return transaction


class PaymentRequestSerializer(serializers.ModelSerializer):
    """Payment request serializer"""
    customer_name = serializers.SerializerMethodField()
    cashier_name = serializers.SerializerMethodField()

    class Meta:
        model = PaymentRequest
        fields = [
            'id', 'request_id', 'customer', 'customer_name',
            'cashier', 'cashier_name', 'amount', 'method',
            'status', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'request_id', 'created_at', 'updated_at']

    def get_customer_name(self, obj):
        if obj.customer and obj.customer.user:
            return obj.customer.user.get_full_name()
        return None

    def get_cashier_name(self, obj):
        if obj.cashier:
            return obj.cashier.get_full_name()
        return None
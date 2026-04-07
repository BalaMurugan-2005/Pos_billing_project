from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from phonenumber_field.modelfields import PhoneNumberField
from djmoney.models.fields import MoneyField
import uuid
import qrcode
from io import BytesIO
from django.core.files import File
from PIL import Image

class User(AbstractUser):
    """Custom User model"""
    ROLE_CHOICES = (
        ('ROLE_ADMIN', 'Admin'),
        ('ROLE_CASHIER', 'Cashier'),
        ('ROLE_CUSTOMER', 'Customer'),
    )
    
    email = models.EmailField(unique=True)
    phone = PhoneNumberField(blank=True, null=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='ROLE_CUSTOMER')
    profile_picture = models.ImageField(upload_to='profiles/', null=True, blank=True)
    is_active = models.BooleanField(default=True)
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']
    
    def __str__(self):
        return f"{self.get_full_name()} ({self.email})"
    
    class Meta:
        db_table = 'users'
        ordering = ['-date_joined']

class Customer(models.Model):
    """Customer model"""
    TIER_CHOICES = (
        ('bronze', 'Bronze'),
        ('silver', 'Silver'),
        ('gold', 'Gold'),
        ('platinum', 'Platinum'),
    )
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='customer_profile')
    loyalty_number = models.CharField(max_length=50, unique=True, null=True, blank=True)
    loyalty_points = models.IntegerField(default=0)
    tier = models.CharField(max_length=20, choices=TIER_CHOICES, default='bronze')
    qr_code = models.ImageField(upload_to='qr_codes/', null=True, blank=True)
    preferred_payment_method = models.CharField(max_length=50, null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    anniversary_date = models.DateField(null=True, blank=True)
    newsletter_subscription = models.BooleanField(default=False)
    total_purchases = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    last_purchase_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.loyalty_number or 'No Loyalty'}"
    
    def generate_loyalty_number(self):
        """Generate unique loyalty number"""
        return f"LOY{str(uuid.uuid4()).replace('-', '')[:10].upper()}"
    
    def generate_qr_code(self):
        """Generate QR code for customer"""
        qr_data = f"customer_id:{self.id}\nemail:{self.user.email}\nloyalty_id:{self.loyalty_number}"
        qr = qrcode.QRCode(
            version=1,
            box_size=10,
            border=5
        )
        qr.add_data(qr_data)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        
        self.qr_code.save(f'customer_{self.id}_qr.png', File(buffer), save=False)
    
    def save(self, *args, **kwargs):
        if not self.loyalty_number:
            self.loyalty_number = self.generate_loyalty_number()
        if not self.qr_code:
            self.generate_qr_code()
        super().save(*args, **kwargs)
    
    class Meta:
        db_table = 'customers'
        ordering = ['-created_at']

class Category(models.Model):
    """Product category model"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='subcategories')
    image = models.ImageField(upload_to='categories/', null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        db_table = 'categories'
        verbose_name_plural = 'Categories'
        ordering = ['name']

class Product(models.Model):
    """Product model"""
    UNIT_CHOICES = (
        ('piece', 'Piece'),
        ('kg', 'Kilogram'),
        ('g', 'Gram'),
        ('l', 'Liter'),
        ('ml', 'Milliliter'),
        ('box', 'Box'),
        ('pack', 'Pack'),
    )
    
    name = models.CharField(max_length=200)
    barcode = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='products')
    price = models.DecimalField(max_digits=10, decimal_places=2)
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    stock_quantity = models.IntegerField(default=0)
    min_stock_level = models.IntegerField(default=10)
    max_stock_level = models.IntegerField(default=100)
    unit = models.CharField(max_length=20, choices=UNIT_CHOICES, default='piece')
    is_weighted = models.BooleanField(default=False)
    price_per_kg = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    brand = models.CharField(max_length=100, blank=True)
    image = models.ImageField(upload_to='products/', null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.name} - {self.barcode}"
    
    @property
    def is_low_stock(self):
        return self.stock_quantity <= self.min_stock_level
    
    @property
    def is_out_of_stock(self):
        return self.stock_quantity <= 0
    
    class Meta:
        db_table = 'products'
        ordering = ['name']
        indexes = [
            models.Index(fields=['barcode']),
            models.Index(fields=['category']),
            models.Index(fields=['is_active']),
        ]

class Inventory(models.Model):
    """Inventory movement model"""
    MOVEMENT_TYPES = (
        ('purchase', 'Purchase'),
        ('sale', 'Sale'),
        ('return', 'Return'),
        ('adjustment', 'Adjustment'),
        ('damage', 'Damage'),
    )
    
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='inventory_movements')
    quantity_change = models.IntegerField()
    movement_type = models.CharField(max_length=20, choices=MOVEMENT_TYPES)
    reason = models.TextField(blank=True)
    previous_quantity = models.IntegerField()
    new_quantity = models.IntegerField()
    performed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    reference_number = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.product.name} - {self.movement_type}: {self.quantity_change}"
    
    def save(self, *args, **kwargs):
        if not self.previous_quantity:
            self.previous_quantity = self.product.stock_quantity
        self.new_quantity = self.previous_quantity + self.quantity_change
        super().save(*args, **kwargs)
        # Update product stock
        self.product.stock_quantity = self.new_quantity
        self.product.save()
    
    class Meta:
        db_table = 'inventory'
        verbose_name_plural = 'Inventory'
        ordering = ['-created_at']

class Transaction(models.Model):
    """Transaction model"""
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('void', 'Void'),
        ('refunded', 'Refunded'),
    )
    
    PAYMENT_METHODS = (
        ('cash', 'Cash'),
        ('card', 'Card'),
        ('upi', 'UPI'),
        ('wallet', 'Digital Wallet'),
        ('mixed', 'Mixed'),
    )
    
    transaction_number = models.CharField(max_length=50, unique=True)
    cashier = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='cashier_transactions')
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True, related_name='transactions')
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    tax = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS)
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    change_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='completed')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.transaction_number} - {self.total}"
    
    def generate_transaction_number(self):
        """Generate unique transaction number"""
        return f"TXN{timezone.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:6].upper()}"
    
    def save(self, *args, **kwargs):
        if not self.transaction_number:
            self.transaction_number = self.generate_transaction_number()
        super().save(*args, **kwargs)
    
    class Meta:
        db_table = 'transactions'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['transaction_number']),
            models.Index(fields=['cashier']),
            models.Index(fields=['customer']),
            models.Index(fields=['created_at']),
        ]

class TransactionItem(models.Model):
    """Transaction item model"""
    transaction = models.ForeignKey(Transaction, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    quantity = models.IntegerField()
    weight = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    tax = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    def __str__(self):
        return f"{self.product.name if self.product else 'Deleted Product'} x {self.quantity}"
    
    def save(self, *args, **kwargs):
        self.subtotal = self.price * self.quantity
        super().save(*args, **kwargs)
    
    class Meta:
        db_table = 'transaction_items'
        ordering = ['id']


class PaymentRequest(models.Model):
    """Payment request model — replaces Spring Boot PaymentRequest entity"""
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('COMPLETED', 'Completed'),
        ('DECLINED', 'Declined'),
        ('EXPIRED', 'Expired'),
    )

    request_id = models.CharField(max_length=100, unique=True, blank=True)
    customer = models.ForeignKey(
        Customer, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='payment_requests'
    )
    cashier = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True,
        related_name='cashier_payment_requests'
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    method = models.CharField(max_length=50)  # CARD, UPI, CASH, etc.
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.request_id:
            self.request_id = 'PAY-' + uuid.uuid4().hex.upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.request_id} — {self.amount} [{self.status}]"

    class Meta:
        db_table = 'payment_requests'
        ordering = ['-created_at']
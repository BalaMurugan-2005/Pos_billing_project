from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import Customer
import logging

logger = logging.getLogger(__name__)
User = get_user_model()

@receiver(post_save, sender=User)
def create_customer_profile(sender, instance, created, **kwargs):
    """Create customer profile when user with role 'ROLE_CUSTOMER' is created"""
    if created and instance.role == 'ROLE_CUSTOMER':
        Customer.objects.create(user=instance)
        logger.info(f"Customer profile created for user: {instance.email}")

@receiver(post_save, sender=User)
def save_customer_profile(sender, instance, **kwargs):
    """Save customer profile when user is saved"""
    if instance.role == 'ROLE_CUSTOMER' and hasattr(instance, 'customer_profile'):
        instance.customer_profile.save()
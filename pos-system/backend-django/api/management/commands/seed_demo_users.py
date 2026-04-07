from django.core.management.base import BaseCommand
from api.models import User

class Command(BaseCommand):
    help = 'Creates demo users for the POS system'

    def handle(self, *args, **options):
        users = [
            {'username': 'admin', 'email': 'admin@pos.com', 'role': 'ROLE_ADMIN', 'is_staff': True, 'is_superuser': True},
            {'username': 'cashier', 'email': 'cashier@pos.com', 'role': 'ROLE_CASHIER', 'is_staff': False, 'is_superuser': False},
            {'username': 'customer', 'email': 'customer@pos.com', 'role': 'ROLE_CUSTOMER', 'is_staff': False, 'is_superuser': False},
        ]
        
        password = 'Bala9677540588#'
        
        for u_data in users:
            user, created = User.objects.get_or_create(
                username=u_data['username'],
                defaults={
                    'email': u_data['email'],
                    'role': u_data['role'],
                    'is_staff': u_data['is_staff'],
                    'is_superuser': u_data['is_superuser']
                }
            )
            if created or not user.check_password(password):
                user.set_password(password)
                user.save()
                self.stdout.write(self.style.SUCCESS(f"Successfully created/updated user: {user.username}"))
            else:
                self.stdout.write(self.style.SUCCESS(f"User already exists: {user.username}"))

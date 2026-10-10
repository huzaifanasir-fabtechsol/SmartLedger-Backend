from django.db import models
from django.contrib.auth.models import AbstractUser

class BaseModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

class User(AbstractUser):
    USER_ROLES = [
        ('admin', 'Admin'),
        ('superadmin', 'Super_Admin'),
    ]
    email = models.EmailField(unique=True)
    company_email = models.EmailField(max_length=250, blank=True, null=True)
    company_name = models.CharField(max_length=250, blank=True, null=True)
    company_phone = models.CharField(max_length=250, blank=True, null=True)
    company_website = models.CharField(max_length=250, blank=True, null=True)
    company_address = models.CharField(max_length=250, blank=True, null=True)
    business_registration = models.CharField(max_length=250, blank=True, null=True)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=10.00, blank=True, null=True)
    role = models.CharField(max_length=50, choices=USER_ROLES, default='admin')

    
    class Meta:
        db_table = 'users'


class TaxRate(BaseModel):
    """Named tax rates that a user can define and reuse across the system."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tax_rates')
    name = models.CharField(max_length=100)                   # e.g. "Consumption Tax (10%)"
    rate = models.DecimalField(max_digits=5, decimal_places=2)  # e.g. 10.00

    class Meta:
        db_table = 'tax_rates'
        unique_together = [('user', 'name')]
        ordering = ['rate']

    def __str__(self):
        return f"{self.name} ({self.rate}%)"


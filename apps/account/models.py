import uuid

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
    # Hashed 6-digit PIN used by the Ctrl+Q screen lock; empty when no PIN is set.
    lock_pin = models.CharField(max_length=128, blank=True, default='')

    
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


class Letterhead(BaseModel):
    """A saved company letterhead design (details, template and colors) owned by a user."""
    TEMPLATES = [
        ('angles', 'Angles'),
        ('chevron', 'Chevron'),
        ('wave', 'Wave'),
        ('corner', 'Corner Cut'),
        ('classic', 'Classic Bars'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='letterheads')
    name = models.CharField(max_length=250)  # company name, shown in the saved list
    logo = models.TextField(blank=True, default='')  # data: URL of the (already downscaled) logo
    tagline = models.CharField(max_length=250, blank=True, default='')
    address = models.TextField(blank=True, default='')
    phone = models.CharField(max_length=250, blank=True, default='')
    email = models.CharField(max_length=250, blank=True, default='')
    website = models.CharField(max_length=250, blank=True, default='')
    registration = models.CharField(max_length=250, blank=True, default='')
    template = models.CharField(max_length=20, choices=TEMPLATES, default='angles')
    color1 = models.CharField(max_length=7, default='#1e3a8a')
    color2 = models.CharField(max_length=7, default='#3b82f6')
    show_date = models.BooleanField(default=True)

    class Meta:
        db_table = 'letterheads'
        ordering = ['-updated_at']

    def __str__(self):
        return self.name


def _letterhead_record_path(instance, filename):
    # Random name: the stored file is only served through the authenticated download endpoint
    return f'letterhead_records/{instance.user_id}/{uuid.uuid4().hex}'


class LetterheadRecord(BaseModel):
    """A finished document (e.g. a filled-in exported letterhead) uploaded for the record."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='letterhead_records')
    description = models.TextField()
    file = models.FileField(upload_to=_letterhead_record_path, max_length=255)
    original_name = models.CharField(max_length=255)
    size = models.PositiveBigIntegerField()  # original bytes
    stored_size = models.PositiveBigIntegerField()  # bytes on disk
    is_compressed = models.BooleanField(default=False)  # stored gzip-wrapped; unwrapped on download
    sha256 = models.CharField(max_length=64)  # of the original bytes

    class Meta:
        db_table = 'letterhead_records'
        ordering = ['-created_at', '-id']

    def __str__(self):
        return self.original_name

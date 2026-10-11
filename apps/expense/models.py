from django.db import models
from apps.account.models import BaseModel, User

class ExpenseCategory(BaseModel):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='categories')

    class Meta:
        db_table = 'expense_categories'
        verbose_name_plural = 'Expense Categories'
        ordering = ['-id']

    def __str__(self):
        return self.name

class Expense(BaseModel):
    title = models.CharField(max_length=200)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField(blank=True)
    date = models.DateField()
    category = models.ForeignKey(ExpenseCategory, on_delete=models.SET_NULL, null=True, related_name='expenses')
    transaction = models.ForeignKey('revenue.Transaction', on_delete=models.SET_NULL, null=True, blank=True, related_name='expenses')
    restaurant = models.ForeignKey('Restaurant', on_delete=models.SET_NULL, null=True, blank=True, related_name='expenses')
    spare_part = models.ForeignKey('SparePart', on_delete=models.SET_NULL, null=True, blank=True, related_name='expenses')
    is_cash = models.BooleanField(default=False)
    TAX_CATEGORY_CHOICES = [
        ('exclusive', 'Tax Exclusive'),
        ('inclusive', 'Tax Inclusive'),
    ]
    # Tax tracking fields
    tax_category = models.CharField(
        max_length=20,
        choices=TAX_CATEGORY_CHOICES,
        default='exclusive',
        help_text="Tax category: tax-inclusive (tax is included in the entered amount) or tax-exclusive (tax is added)."
    )
    tax_percent_used = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True,
                                           help_text="The tax rate (%) applied to this expense, if any.")
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True,
                                     help_text="The calculated tax amount for this expense.")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='expenses')

    @property
    def total_amount(self):
        from decimal import Decimal
        amt = self.amount or Decimal('0')
        tax = self.tax_amount or Decimal('0')
        return amt + tax

    class Meta:
        db_table = 'expenses'
        ordering = ['-date', '-id']

    def __str__(self):
        return f"{self.title} - {self.amount}"

class ExpenseImportJob(BaseModel):
    """One bulk expense + transaction import (xlsx upload processed by a Celery task)."""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    ACTIVE_STATUSES = ('pending', 'running')

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='expense_import_jobs')
    company_account = models.ForeignKey('revenue.CompanyAccount', on_delete=models.SET_NULL, null=True, related_name='+')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    file_name = models.CharField(max_length=255)
    total_rows = models.PositiveIntegerField(default=0)
    processed_rows = models.PositiveIntegerField(default=0)
    # Validated rows waiting to be imported. Cleared as soon as the job finishes.
    payload = models.JSONField(null=True, blank=True)
    result = models.JSONField(null=True, blank=True)
    error = models.TextField(blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'expense_import_jobs'
        ordering = ['-id']
        constraints = [
            # The database itself guarantees a user can only have one import in flight.
            models.UniqueConstraint(
                fields=['user'],
                condition=models.Q(status__in=['pending', 'running']),
                name='one_active_expense_import_per_user',
            ),
        ]

    def __str__(self):
        return f"{self.file_name} - {self.status}"

class Restaurant(BaseModel):
    name = models.CharField(max_length=200)
    location = models.CharField(max_length=300)
    description = models.TextField(blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='restaurants')

    class Meta:
        db_table = 'restaurants'
        ordering = ['-id']

    def __str__(self):
        return self.name


class SparePart(BaseModel):
    name = models.CharField(max_length=200)
    # Legacy compatibility for deployments where these columns already exist as NOT NULL.
    part_number = models.CharField(max_length=120, blank=True, default='', editable=False)
    brand = models.CharField(max_length=120, blank=True, default='', editable=False)
    address = models.CharField(max_length=300, blank=True, db_column='location')
    description = models.TextField(blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='spare_parts')

    class Meta:
        db_table = 'spare_parts'
        ordering = ['-id']

    def __str__(self):
        return self.name

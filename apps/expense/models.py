from django.db import models
from apps.account.models import BaseModel, User

class ExpenseCategory(BaseModel):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='categories')

    class Meta:
        db_table = 'expense_categories'
        verbose_name_plural = 'Expense Categories'

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
    # Tax tracking fields
    tax_percent_used = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True,
                                           help_text="The tax rate (%) applied to this expense, if any.")
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True,
                                     help_text="The calculated tax amount for this expense.")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='expenses')

    class Meta:
        db_table = 'expenses'
        ordering = ['-date']

    def __str__(self):
        return f"{self.title} - {self.amount}"

class Restaurant(BaseModel):
    name = models.CharField(max_length=200)
    location = models.CharField(max_length=300)
    description = models.TextField(blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='restaurants')

    class Meta:
        db_table = 'restaurants'

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

    def __str__(self):
        return self.name

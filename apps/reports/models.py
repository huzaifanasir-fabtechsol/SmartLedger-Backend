from django.db import models

from apps.account.models import BaseModel, User


class CompanyProfile(BaseModel):
    """Legal/company details printed on the statements (one per user)."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='company_profile')
    legal_name = models.CharField(max_length=250, blank=True)
    legal_name_kana = models.CharField(max_length=250, blank=True)
    representative_name = models.CharField(max_length=250, blank=True)
    representative_name_kana = models.CharField(max_length=250, blank=True)
    corporate_number = models.CharField(max_length=13, blank=True)
    capital = models.BigIntegerField(default=0)
    address = models.CharField(max_length=250, blank=True)
    phone = models.CharField(max_length=50, blank=True)
    tax_office = models.CharField(max_length=100, blank=True)
    business_description = models.CharField(max_length=250, blank=True)
    # Optional English renderings, used by the English PDFs (fall back to the Japanese values)
    legal_name_en = models.CharField(max_length=250, blank=True)
    representative_name_en = models.CharField(max_length=250, blank=True)
    address_en = models.CharField(max_length=250, blank=True)
    # Tax accountant (税理士) shown on powers of attorney / filings
    accountant_name = models.CharField(max_length=250, blank=True)
    accountant_address = models.CharField(max_length=250, blank=True)
    accountant_phone = models.CharField(max_length=50, blank=True)
    accountant_registration = models.CharField(max_length=50, blank=True)
    # [{"name", "address", "relationship", "shares", "group"}] — 別表二 (family-company test)
    shareholders = models.JSONField(default=list, blank=True)
    # [{"prefecture", "prefecture_office", "municipality", "employees", "months",
    #   "pref_levy", "city_levy", "pref_rate", "city_rate"}] — 地方税 allocation
    offices = models.JSONField(default=list, blank=True)

    class Meta:
        db_table = 'report_company_profiles'

    def __str__(self):
        return self.legal_name or f'CompanyProfile {self.pk}'


class FiscalYear(BaseModel):
    STATUS_CHOICES = [('draft', 'Draft'), ('final', 'Final')]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='fiscal_years')
    term_no = models.PositiveIntegerField()
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='draft')

    class Meta:
        db_table = 'report_fiscal_years'
        ordering = ['-start_date']
        unique_together = [('user', 'term_no')]

    def __str__(self):
        return f'第{self.term_no}期 {self.start_date} - {self.end_date}'


class StatementInput(BaseModel):
    """Manually entered figures for a fiscal year. See services/inputs.py for the schema."""
    fiscal_year = models.OneToOneField(FiscalYear, on_delete=models.CASCADE, related_name='inputs')
    data = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'report_statement_inputs'


class FixedAsset(BaseModel):
    CATEGORY_CHOICES = [
        ('building', '建物'),
        ('equipment', '工具器具備品'),
        ('vehicle', '車両運搬具'),
        ('other_tangible', 'その他有形固定資産'),
        ('deferred', '繰延資産'),
    ]
    METHOD_CHOICES = [
        ('straight_line', '定額法'),
        ('declining_200', '200%定率法'),
        ('lump_sum', '一時償却'),
        ('none', '償却なし'),
    ]

    fiscal_year = models.ForeignKey(FiscalYear, on_delete=models.CASCADE, related_name='fixed_assets')
    name = models.CharField(max_length=250)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    acquired_on = models.DateField()
    cost = models.BigIntegerField()
    method = models.CharField(max_length=20, choices=METHOD_CHOICES, default='straight_line')
    useful_life = models.PositiveIntegerField(default=0, help_text='耐用年数 (years)')
    # Book value at the start of this fiscal year. Ignored (cost is used) when the asset
    # was acquired within the fiscal year.
    opening_book_value = models.BigIntegerField(default=0)

    class Meta:
        db_table = 'report_fixed_assets'
        ordering = ['acquired_on', 'id']

    def __str__(self):
        return self.name

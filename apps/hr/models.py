from django.db import models
from apps.account.models import BaseModel, User


class Employee(BaseModel):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
    ]

    name = models.CharField(max_length=200)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=50)
    role = models.CharField(max_length=100)
    address = models.TextField(blank=True)
    employment_start_month = models.DateField()
    basic_salary = models.DecimalField(max_digits=12, decimal_places=2)
    commuting_allowance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    dependents_count = models.IntegerField(default=0)
    employment_insurance_exempt = models.BooleanField(default=False)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')
    admin = models.ForeignKey(User, on_delete=models.CASCADE, related_name='employees')

    class Meta:
        db_table = 'employees'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.role})"


class Salary(BaseModel):
    STATUS_CHOICES = [
        ('paid', 'Paid'),
        ('unpaid', 'Unpaid'),
    ]

    salary_month = models.CharField(max_length=7)  # YYYY-MM format
    payment_date = models.DateField(null=True, blank=True)  # 支給日
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='salaries')
    admin = models.ForeignKey(User, on_delete=models.CASCADE, related_name='salaries')

    # Earnings (支給)
    basic_salary = models.DecimalField(max_digits=12, decimal_places=2, default=0)  # 基本給
    commuting_allowance = models.DecimalField(max_digits=12, decimal_places=2, default=0)  # 非課税通勤費
    overtime_allowance = models.DecimalField(max_digits=12, decimal_places=2, default=0)  # 残業手当
    allowances = models.DecimalField(max_digits=12, decimal_places=2, default=0)  # その他手当
    taxable_payment = models.DecimalField(max_digits=12, decimal_places=2, default=0)  # 課税支給額
    gross_payment = models.DecimalField(max_digits=12, decimal_places=2, default=0)  # 支給額合計

    # Deductions (控除)
    health_insurance = models.DecimalField(max_digits=12, decimal_places=2, default=0)  # 健康保険料
    welfare_pension = models.DecimalField(max_digits=12, decimal_places=2, default=0)  # 厚生年金
    employment_insurance = models.DecimalField(max_digits=12, decimal_places=2, default=0)  # 雇用保険
    total_social_insurance = models.DecimalField(max_digits=12, decimal_places=2, default=0)  # 社会保険計
    taxable_income_base = models.DecimalField(max_digits=12, decimal_places=2, default=0)  # 課税対象額
    income_tax = models.DecimalField(max_digits=12, decimal_places=2, default=0)  # 所得税
    resident_tax = models.DecimalField(max_digits=12, decimal_places=2, default=0)  # 住民税
    leaves = models.DecimalField(max_digits=5, decimal_places=1, default=0)
    leave_deduction = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    other_deductions = models.DecimalField(max_digits=12, decimal_places=2, default=0)  # その他控除
    total_deductions = models.DecimalField(max_digits=12, decimal_places=2, default=0)  # 控除額合計

    # Net Amount (差引支給額)
    net_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)  # 差引支給額
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='unpaid')

    # Attendance (勤怠)
    working_days = models.DecimalField(max_digits=5, decimal_places=1, default=0)  # 勤務日数
    working_hours = models.DecimalField(max_digits=6, decimal_places=2, default=0)  # 勤務時間数
    overtime_hours = models.DecimalField(max_digits=6, decimal_places=2, default=0)  # 普通時間外時間
    holiday_overtime_hours = models.DecimalField(max_digits=6, decimal_places=2, default=0)  # 休日時間外時間
    midnight_overtime_hours = models.DecimalField(max_digits=6, decimal_places=2, default=0)  # 深夜時間外時間
    paid_leaves = models.DecimalField(max_digits=5, decimal_places=1, default=0)  # 有給日数
    statutory_leaves = models.DecimalField(max_digits=5, decimal_places=1, default=0)  # 公休日数
    absence_days = models.DecimalField(max_digits=5, decimal_places=1, default=0)  # 欠勤日数
    late_early_count = models.IntegerField(default=0)  # 遅刻・早退 回数
    late_early_hours = models.DecimalField(max_digits=6, decimal_places=2, default=0)  # 遅刻・早退 時間
    remarks = models.TextField(blank=True)  # 備考

    class Meta:
        db_table = 'salaries'
        ordering = ['-salary_month', '-created_at']

    def __str__(self):
        return f"{self.employee.name} - {self.salary_month}"


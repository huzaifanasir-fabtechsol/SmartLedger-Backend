from django.contrib import admin
from apps.hr.models import Employee, Salary


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'phone', 'role', 'status', 'basic_salary', 'commuting_allowance', 'admin']
    list_filter = ['status', 'role', 'employment_insurance_exempt']
    search_fields = ['name', 'email', 'phone']


@admin.register(Salary)
class SalaryAdmin(admin.ModelAdmin):
    list_display = [
        'employee', 'salary_month', 'payment_date',
        'basic_salary', 'gross_payment', 'total_social_insurance',
        'income_tax', 'total_deductions', 'net_amount', 'status', 'admin'
    ]
    list_filter = ['status', 'salary_month']
    search_fields = ['employee__name', 'employee__email']

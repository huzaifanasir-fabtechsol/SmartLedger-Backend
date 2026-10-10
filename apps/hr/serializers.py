import re
from decimal import Decimal
from rest_framework import serializers
from apps.hr.models import Employee, Salary
from apps.hr.payroll_calculator import calculate_japanese_payroll


class EmployeeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Employee
        fields = [
            'id', 'name', 'email', 'phone', 'role', 'address',
            'employment_start_month', 'basic_salary',
            'commuting_allowance', 'dependents_count', 'employment_insurance_exempt',
            'status', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

    def validate_email(self, value):
        """Email must be globally unique across all employees."""
        qs = Employee.objects.filter(email__iexact=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("An employee with this email already exists.")
        return value.lower()

    def validate_basic_salary(self, value):
        if value < 0:
            raise serializers.ValidationError("Basic salary cannot be negative.")
        return value

    def validate_dependents_count(self, value):
        if value < 0:
            raise serializers.ValidationError("Dependents count cannot be negative.")
        return value


class SalarySerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.name', read_only=True)
    employee_role = serializers.CharField(source='employee.role', read_only=True)

    class Meta:
        model = Salary
        fields = [
            'id', 'salary_month', 'payment_date', 'employee', 'employee_name', 'employee_role',
            # Earnings
            'basic_salary', 'commuting_allowance', 'overtime_allowance', 'allowances',
            'taxable_payment', 'gross_payment',
            # Deductions
            'health_insurance', 'welfare_pension', 'employment_insurance',
            'total_social_insurance', 'taxable_income_base',
            'income_tax', 'resident_tax', 'leave_deduction', 'other_deductions',
            'total_deductions',
            # Net Payout & Status
            'net_amount', 'status',
            # Attendance
            'leaves', 'working_days', 'working_hours', 'overtime_hours',
            'holiday_overtime_hours', 'midnight_overtime_hours',
            'paid_leaves', 'statutory_leaves', 'absence_days',
            'late_early_count', 'late_early_hours',
            'remarks',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

    def validate_employee(self, value):
        """Employee must belong to the authenticated admin."""
        request = self.context.get('request')
        if request and value.admin != request.user:
            raise serializers.ValidationError("This employee does not belong to your account.")
        return value

    def validate_salary_month(self, value):
        """Must be YYYY-MM format."""
        if not re.match(r'^\d{4}-(0[1-9]|1[0-2])$', str(value)):
            raise serializers.ValidationError("Salary month must be in YYYY-MM format (e.g. 2026-02).")
        return value

    def validate(self, attrs):
        # Default basic_salary from employee if not explicitly passed
        employee = attrs.get('employee') or (self.instance.employee if self.instance else None)
        
        basic_salary = attrs.get('basic_salary')
        if basic_salary is None:
            if self.instance and self.instance.basic_salary:
                basic_salary = self.instance.basic_salary
            elif employee:
                basic_salary = employee.basic_salary
            else:
                basic_salary = Decimal('0')
            attrs['basic_salary'] = basic_salary

        commuting_allowance = attrs.get('commuting_allowance')
        if commuting_allowance is None:
            if self.instance and self.instance.commuting_allowance is not None:
                commuting_allowance = self.instance.commuting_allowance
            elif employee and getattr(employee, 'commuting_allowance', None) is not None:
                commuting_allowance = employee.commuting_allowance
            else:
                commuting_allowance = Decimal('0')
            attrs['commuting_allowance'] = commuting_allowance

        overtime_allowance = attrs.get('overtime_allowance', self.instance.overtime_allowance if self.instance else Decimal('0'))
        allowances = attrs.get('allowances', self.instance.allowances if self.instance else Decimal('0'))
        leave_deduction = attrs.get('leave_deduction', self.instance.leave_deduction if self.instance else Decimal('0'))
        resident_tax = attrs.get('resident_tax', self.instance.resident_tax if self.instance else Decimal('0'))
        other_deductions = attrs.get('other_deductions', self.instance.other_deductions if self.instance else Decimal('0'))

        dependents = employee.dependents_count if employee else 0
        is_exempt = employee.employment_insurance_exempt if employee else False

        # If social insurance or tax fields are not explicitly provided, calculate automatically
        calc_result = calculate_japanese_payroll(
            basic_salary=basic_salary,
            commuting_allowance=commuting_allowance,
            overtime_allowance=overtime_allowance,
            allowances=allowances,
            resident_tax=resident_tax,
            leave_deduction=leave_deduction,
            other_deductions=other_deductions,
            dependents_count=dependents,
            is_employment_insurance_exempt=is_exempt,
            custom_health_insurance=attrs.get('health_insurance'),
            custom_welfare_pension=attrs.get('welfare_pension'),
            custom_employment_insurance=attrs.get('employment_insurance'),
            custom_income_tax=attrs.get('income_tax'),
        )

        for k, v in calc_result.items():
            if k not in attrs or attrs[k] is None:
                attrs[k] = v

        return attrs


class SalaryCalculationSerializer(serializers.Serializer):
    """Serializer to preview salary and tax calculations before saving."""
    employee_id = serializers.IntegerField(required=False, allow_null=True)
    basic_salary = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, default=Decimal('0'))
    commuting_allowance = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, default=Decimal('0'))
    overtime_allowance = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, default=Decimal('0'))
    allowances = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, default=Decimal('0'))
    leave_deduction = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, default=Decimal('0'))
    resident_tax = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, default=Decimal('0'))
    other_deductions = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, default=Decimal('0'))
    dependents_count = serializers.IntegerField(required=False, default=0)
    employment_insurance_exempt = serializers.BooleanField(required=False, default=False)
    custom_health_insurance = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, allow_null=True)
    custom_welfare_pension = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, allow_null=True)
    custom_employment_insurance = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, allow_null=True)
    custom_income_tax = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, allow_null=True)

import re
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Q
from django.http import HttpResponse

from apps.hr.models import Employee, Salary
from apps.hr.serializers import (
    EmployeeSerializer,
    SalarySerializer,
    SalaryCalculationSerializer
)
from apps.hr.payroll_calculator import calculate_japanese_payroll
from apps.hr.payslip_generator import generate_payslip_excel, generate_payslip_pdf
from project.pagination import CustomPageNumberPagination


class EmployeeViewSet(viewsets.ModelViewSet):
    serializer_class = EmployeeSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPageNumberPagination

    def get_queryset(self):
        queryset = Employee.objects.filter(admin=self.request.user)

        search = self.request.query_params.get('search', '').strip()
        role = self.request.query_params.get('role', '').strip()

        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(email__icontains=search) |
                Q(phone__icontains=search)
            )
        if role:
            queryset = queryset.filter(role__iexact=role)

        return queryset

    def perform_create(self, serializer):
        serializer.save(admin=self.request.user)

    @action(detail=False, methods=['get'], url_path='roles')
    def roles(self, request):
        """Return distinct roles for the authenticated admin's employees."""
        roles = (
            Employee.objects
            .filter(admin=request.user)
            .exclude(role='')
            .values_list('role', flat=True)
            .distinct()
            .order_by('role')
        )
        return Response(list(roles))

    @action(detail=False, methods=['get'], url_path='all')
    def all_employees(self, request):
        """Return all employees (no pagination) for dropdown use in Salary module."""
        employees = Employee.objects.filter(admin=request.user, status='active').order_by('name')
        serializer = self.get_serializer(employees, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['patch'], url_path='toggle-status')
    def toggle_status(self, request, pk=None):
        """Toggle employee status between active and inactive."""
        employee = self.get_object()
        employee.status = 'inactive' if employee.status == 'active' else 'active'
        employee.save()
        serializer = self.get_serializer(employee)
        return Response(serializer.data)

    @action(detail=True, methods=['get'], url_path='salary-report')
    def salary_report(self, request, pk=None):
        """Return detailed salary report for an employee filtered by year or month."""
        employee = self.get_object()
        user = request.user

        year = request.query_params.get('year', '').strip()
        month = request.query_params.get('month', '').strip()

        queryset = Salary.objects.filter(employee=employee, admin=user)

        if month:
            queryset = queryset.filter(salary_month=month)
        elif year:
            queryset = queryset.filter(salary_month__startswith=year)

        queryset = queryset.order_by('salary_month')
        salaries_data = SalarySerializer(queryset, many=True).data

        total_gross_payment = sum(float(s.gross_payment or 0) for s in queryset)
        total_taxable_payment = sum(float(s.taxable_payment or 0) for s in queryset)
        total_social_insurance = sum(float(s.total_social_insurance or 0) for s in queryset)
        total_health_insurance = sum(float(s.health_insurance or 0) for s in queryset)
        total_welfare_pension = sum(float(s.welfare_pension or 0) for s in queryset)
        total_employment_insurance = sum(float(s.employment_insurance or 0) for s in queryset)
        total_income_tax = sum(float(s.income_tax or 0) for s in queryset)
        total_resident_tax = sum(float(s.resident_tax or 0) for s in queryset)
        total_leaves = sum(float(s.leaves or 0) for s in queryset)
        total_leave_deduction = sum(float(s.leave_deduction or 0) for s in queryset)
        total_allowances = sum(float(s.allowances or 0) for s in queryset)
        total_other_deductions = sum(float(s.other_deductions or 0) for s in queryset)
        total_deductions = sum(float(s.total_deductions or 0) for s in queryset)
        total_net_amount = sum(float(s.net_amount or 0) for s in queryset)
        total_working_days = sum(float(s.working_days or 0) for s in queryset)
        total_working_hours = sum(float(s.working_hours or 0) for s in queryset)
        total_overtime_hours = sum(float(s.overtime_hours or 0) for s in queryset)
        paid_count = queryset.filter(status='paid').count()
        unpaid_count = queryset.filter(status='unpaid').count()

        admin_company = {
            'company_name': user.company_name or 'Smart Ledger',
            'company_email': user.company_email or user.email,
            'company_phone': user.company_phone or '',
            'company_address': user.company_address or '',
            'business_registration': user.business_registration or '',
        }

        response_data = {
            'employee': EmployeeSerializer(employee).data,
            'admin_company': admin_company,
            'year': year,
            'month': month,
            'salaries': salaries_data,
            'summary': {
                'total_records': len(salaries_data),
                'total_gross_payment': total_gross_payment,
                'total_taxable_payment': total_taxable_payment,
                'total_social_insurance': total_social_insurance,
                'total_health_insurance': total_health_insurance,
                'total_welfare_pension': total_welfare_pension,
                'total_employment_insurance': total_employment_insurance,
                'total_income_tax': total_income_tax,
                'total_resident_tax': total_resident_tax,
                'total_leaves': total_leaves,
                'total_leave_deduction': total_leave_deduction,
                'total_allowances': total_allowances,
                'total_other_deductions': total_other_deductions,
                'total_deductions': total_deductions,
                'total_net_amount': total_net_amount,
                'total_working_days': total_working_days,
                'total_working_hours': total_working_hours,
                'total_overtime_hours': total_overtime_hours,
                'paid_count': paid_count,
                'unpaid_count': unpaid_count,
            }
        }
        return Response(response_data)


class SalaryViewSet(viewsets.ModelViewSet):
    serializer_class = SalarySerializer
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPageNumberPagination

    def get_queryset(self):
        queryset = Salary.objects.filter(admin=self.request.user).select_related('employee')

        search = self.request.query_params.get('search', '').strip()
        employee_id = self.request.query_params.get('employee', '').strip()
        salary_month = self.request.query_params.get('salary_month', '').strip()
        salary_status = self.request.query_params.get('status', '').strip()

        if search:
            queryset = queryset.filter(
                Q(employee__name__icontains=search) |
                Q(employee__role__icontains=search)
            )
        if employee_id:
            queryset = queryset.filter(employee_id=employee_id)
        if salary_month:
            queryset = queryset.filter(salary_month=salary_month)
        if salary_status:
            queryset = queryset.filter(status=salary_status)

        return queryset

    def perform_create(self, serializer):
        serializer.save(admin=self.request.user)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    @action(detail=False, methods=['post'], url_path='calculate')
    def calculate(self, request):
        """Preview salary calculations including Japan social insurance & withholding tax."""
        calc_serializer = SalaryCalculationSerializer(data=request.data)
        calc_serializer.is_valid(raise_exception=True)
        data = calc_serializer.validated_data

        employee_id = data.get('employee_id')
        basic_salary = data.get('basic_salary')
        commuting_allowance = data.get('commuting_allowance')
        dependents = data.get('dependents_count', 0)
        is_exempt = data.get('employment_insurance_exempt', False)

        if employee_id:
            try:
                emp = Employee.objects.get(id=employee_id, admin=request.user)
                if not basic_salary:
                    basic_salary = emp.basic_salary
                if not commuting_allowance:
                    commuting_allowance = emp.commuting_allowance
                if 'dependents_count' not in request.data:
                    dependents = emp.dependents_count
                if 'employment_insurance_exempt' not in request.data:
                    is_exempt = emp.employment_insurance_exempt
            except Employee.DoesNotExist:
                return Response({'error': 'Employee not found.'}, status=status.HTTP_404_NOT_FOUND)

        calc_result = calculate_japanese_payroll(
            basic_salary=basic_salary,
            commuting_allowance=commuting_allowance,
            overtime_allowance=data.get('overtime_allowance', 0),
            allowances=data.get('allowances', 0),
            resident_tax=data.get('resident_tax', 0),
            leave_deduction=data.get('leave_deduction', 0),
            other_deductions=data.get('other_deductions', 0),
            dependents_count=dependents,
            is_employment_insurance_exempt=is_exempt,
            custom_health_insurance=data.get('custom_health_insurance'),
            custom_welfare_pension=data.get('custom_welfare_pension'),
            custom_employment_insurance=data.get('custom_employment_insurance'),
            custom_income_tax=data.get('custom_income_tax'),
        )

        return Response(calc_result)

    @action(detail=True, methods=['get'], url_path='export-excel')
    def export_excel(self, request, pk=None):
        """Export salary slip as an Excel file matching the official Japanese template."""
        salary = self.get_object()
        excel_buffer = generate_payslip_excel(salary)

        # Sanitize employee name for Content-Disposition header
        emp_name = re.sub(r'[^a-zA-Z0-9_-]', '_', salary.employee.name if salary.employee else 'Employee')
        filename = f"Pay_Slip_{emp_name}_{salary.salary_month}.xlsx"

        response = HttpResponse(
            excel_buffer.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        response['X-Content-Type-Options'] = 'nosniff'
        return response

    @action(detail=True, methods=['get'], url_path='export-pdf')
    def export_pdf(self, request, pk=None):
        """Export salary slip as a formatted PDF."""
        salary = self.get_object()
        pdf_buffer = generate_payslip_pdf(salary)

        emp_name = re.sub(r'[^a-zA-Z0-9_-]', '_', salary.employee.name if salary.employee else 'Employee')
        filename = f"Pay_Slip_{emp_name}_{salary.salary_month}.pdf"

        response = HttpResponse(
            pdf_buffer.getvalue(),
            content_type='application/pdf'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        response['X-Content-Type-Options'] = 'nosniff'
        return response

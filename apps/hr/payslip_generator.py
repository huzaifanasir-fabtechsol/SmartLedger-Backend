"""
Payslip Generator for Japanese Salary Slips (給与支払明細書).
Supports exact Excel (.xlsx) reproduction and professional PDF generation.
"""

import io
import os
from pathlib import Path
from decimal import Decimal
from datetime import datetime
import openpyxl
import openpyxl.worksheet.properties
from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
from django.conf import settings

from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont

# Built-in CJK font (no font file needed) so Japanese glyphs render in PDFs
pdfmetrics.registerFont(UnicodeCIDFont('HeiseiKakuGo-W5'))
JP_FONT = 'HeiseiKakuGo-W5'


TEMPLATE_PATH = Path(settings.BASE_DIR) / 'Pay Slip.xlsx'


def generate_payslip_excel(salary) -> io.BytesIO:
    """
    Generate an Excel salary slip matching the official template.
    Populates all fields dynamically based on the Salary model instance.
    """
    if TEMPLATE_PATH.exists():
        wb = openpyxl.load_workbook(str(TEMPLATE_PATH))
        ws = wb.active
    else:
        # Template file not available: build the full layout from scratch
        return _build_payslip_excel(salary)

    # 1. Target Period (Year & Month)
    # salary_month is in 'YYYY-MM' format
    try:
        parts = salary.salary_month.split('-')
        year_num = int(parts[0])
        month_num = int(parts[1])
    except Exception:
        year_num = datetime.now().year
        month_num = datetime.now().month

    ws['F6'] = year_num
    ws['H6'] = month_num

    # 2. Company Name
    admin_user = salary.admin
    company_name = (
        getattr(admin_user, 'company_name', None) or
        getattr(admin_user, 'first_name', '') or
        'ILYAS SONS合同会社'
    )
    ws['B5'] = company_name

    # 3. Employee Name
    emp_name = salary.employee.name if salary.employee else ''
    ws['C3'] = emp_name

    # 4. Payment Date (支給日)
    if salary.payment_date:
        p_date = salary.payment_date
    else:
        # Default to end of salary month
        p_date = datetime(year_num, month_num, 1)

    ws['R11'] = p_date.year
    ws['T11'] = p_date.month
    ws['V11'] = p_date.day

    # 5. Earnings (支給)
    ws['G13'] = float(salary.basic_salary or 0)
    ws['G25'] = float(salary.commuting_allowance or 0)
    ws['G26'] = float(salary.taxable_payment or (salary.basic_salary + salary.overtime_allowance + salary.allowances))
    ws['G28'] = float(salary.gross_payment or (salary.taxable_payment + salary.commuting_allowance))

    # 6. Deductions (控除)
    ws['R13'] = float(salary.health_insurance or 0)
    ws['R14'] = float(salary.welfare_pension or 0)
    ws['R15'] = float(salary.employment_insurance or 0)
    # Keep standard excel formulas or values
    ws['R19'] = '=SUM(R13:W18)'
    ws['R20'] = '=G26-R19'
    ws['R21'] = float(salary.income_tax or 0)
    if salary.resident_tax and float(salary.resident_tax) > 0:
        ws['R22'] = float(salary.resident_tax)
    else:
        ws['R22'] = None

    ws['R27'] = '=R19+SUM(R21:W26)'
    ws['R28'] = '=G28-R27'

    # 7. Attendance (勤怠)
    ws['B34'] = float(salary.working_days or 0)
    ws['E34'] = float(salary.working_hours or 0)
    ws['H34'] = float(salary.overtime_hours or 0)
    ws['J34'] = float(salary.holiday_overtime_hours or 0)
    ws['L34'] = float(salary.midnight_overtime_hours or 0)
    ws['N34'] = float(salary.paid_leaves or 0)
    ws['P34'] = float(salary.statutory_leaves or 0)
    ws['R34'] = float(salary.absence_days or 0)
    ws['T34'] = int(salary.late_early_count or 0)
    ws['V34'] = float(salary.late_early_hours or 0)

    # 8. Remarks (備考)
    if salary.remarks:
        ws['B40'] = str(salary.remarks)

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output


def _build_payslip_excel(salary) -> io.BytesIO:
    """Build a formatted salary slip workbook (labels, borders, colours) without a template."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "給与明細"

    thin = Side(style='thin', color='BBBBBB')
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    blue = PatternFill('solid', fgColor='EBF3FB')
    blue_dk = PatternFill('solid', fgColor='DCE9F6')
    red = PatternFill('solid', fgColor='FBEBEB')
    red_dk = PatternFill('solid', fgColor='F9DFDF')
    green = PatternFill('solid', fgColor='D0E4A9')
    grey = PatternFill('solid', fgColor='F5F5F5')
    yen = '"¥"#,##0'

    for col, w in zip('ABCDE', [34, 16, 36, 16, 3]):
        ws.column_dimensions[col].width = w
    for col in 'FGH':
        ws.column_dimensions[col].width = 0

    try:
        parts = salary.salary_month.split('-')
        title = f"{parts[0]}年 {parts[1]}月 給与支払明細書 (Salary Slip)"
    except Exception:
        title = f"{salary.salary_month} 給与支払明細書 (Salary Slip)"
    ws.merge_cells('A1:D1')
    ws['A1'] = title
    ws['A1'].font = Font(name='Arial', size=16, bold=True)
    ws['A1'].alignment = Alignment(horizontal='center', vertical='center')
    ws.row_dimensions[1].height = 32

    admin_user = salary.admin
    company_name = (
        getattr(admin_user, 'company_name', None) or
        getattr(admin_user, 'first_name', '') or
        'ILYAS SONS合同会社'
    )
    emp = salary.employee
    p_date = str(salary.payment_date) if salary.payment_date else salary.salary_month
    ws['A3'] = f"Company: {company_name}"
    ws['C3'] = f"Payment Date: {p_date}"
    ws['A4'] = f"Employee: {emp.name if emp else ''} 様"
    ws['C4'] = f"Department/Role: {getattr(emp, 'role', '') or ''}"

    def n(v):
        return float(v or 0)

    rows = [
        ("支給 (Earnings)", "金額 (JPY)", "控除 (Deductions)", "金額 (JPY)"),
        ("基本給 (Base Salary)", n(salary.basic_salary), "健康保険料 (Health Insurance)", n(salary.health_insurance)),
        ("残業手当 (Overtime Pay)", n(salary.overtime_allowance), "厚生年金 (Welfare Pension)", n(salary.welfare_pension)),
        ("その他手当 (Allowances)", n(salary.allowances), "雇用保険 (Employment Insurance)", n(salary.employment_insurance)),
        ("非課税通勤費 (Commuting)", n(salary.commuting_allowance), "社会保険計 (Total Social Insurance)", n(salary.total_social_insurance)),
        ("課税支給額 (Taxable Gross)", n(salary.taxable_payment), "所得税 (Income Tax)", n(salary.income_tax)),
        ("", None, "住民税 (Resident Tax)", n(salary.resident_tax)),
        ("", None, "その他控除 (Other Deductions)", n(salary.other_deductions)),
        ("支給額合計 (Total Gross)", n(salary.gross_payment), "控除額合計 (Total Deductions)", n(salary.total_deductions)),
        ("差引支給額 (Net Take-Home Pay)", n(salary.net_amount), "", None),
    ]
    start = 6
    for i, row in enumerate(rows):
        r = start + i
        for c, val in enumerate(row, start=1):
            cell = ws.cell(row=r, column=c, value=val)
            cell.border = border
            cell.font = Font(name='Arial', size=10)
            if c in (2, 4):
                cell.alignment = Alignment(horizontal='right')
                if i > 0:
                    cell.number_format = yen
            if i == 0:
                cell.fill = blue if c <= 2 else red
            elif i == 8:
                cell.fill = blue_dk if c <= 2 else red_dk
                cell.font = Font(name='Arial', size=10, bold=True)
            elif i == 9 and c <= 2:
                cell.fill = green
                cell.font = Font(name='Arial', size=11, bold=True)

    r = start + len(rows) + 1
    ws.cell(row=r, column=1, value="勤怠 (Attendance)").font = Font(name='Arial', size=11, bold=True, italic=True)
    req = getattr(salary, 'required_working_hours', None) or (salary.working_days * Decimal('8.0'))
    att = [
        ["所定時間 (Required)", "実働時間 (Worked)", "普通残業 (OT)", "休日残業 (Holiday)", "深夜残業 (Midnight)"],
        [f"{req} h", f"{salary.working_hours} h", f"{salary.overtime_hours} h", f"{salary.holiday_overtime_hours} h", f"{salary.midnight_overtime_hours} h"],
        ["勤務日数 (Days)", "有給日数 (Paid Leave)", "公休日数 (Off Days)", "欠勤日数 (Absence)", "遅刻・早退 (Late/Early)"],
        [f"{salary.working_days} days", f"{salary.paid_leaves} days", f"{salary.statutory_leaves} days", f"{salary.absence_days} days", f"{salary.late_early_count} times / {salary.late_early_hours}h"],
    ]
    # Attendance uses 4 data columns wide layout: wrap into A-D plus E
    ws.column_dimensions['E'].width = 24
    for i, row in enumerate(att):
        for c, val in enumerate(row, start=1):
            cell = ws.cell(row=r + 1 + i, column=c, value=val)
            cell.border = border
            cell.font = Font(name='Arial', size=9)
            cell.alignment = Alignment(horizontal='center')
            if i % 2 == 0:
                cell.fill = grey

    if salary.remarks:
        rr = r + len(att) + 2
        ws.cell(row=rr, column=1, value=f"備考 (Remarks): {salary.remarks}").font = Font(name='Arial', size=10)

    ws.page_setup.orientation = 'landscape'
    ws.page_setup.fitToWidth = 1
    ws.sheet_properties.pageSetUpPr = openpyxl.worksheet.properties.PageSetupProperties(fitToPage=True)

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output


def _add_watermark(canvas, doc, text="Ilyas Sons 合同会社"):
    """Tiled diagonal watermark, same style as the invoice PDFs."""
    canvas.saveState()
    canvas.setFont(JP_FONT, 60)
    canvas.setFillColor(colors.lightgrey)
    canvas.setFillAlpha(0.12)

    width, height = doc.pagesize
    x_spacing = width / 3
    y_spacing = height / 4
    for i in range(3):
        for j in range(4):
            canvas.saveState()
            canvas.translate(x_spacing * (i + 0.5), y_spacing * (j + 0.5))
            canvas.rotate(45)
            canvas.drawCentredString(0, 0, text)
            canvas.restoreState()
    canvas.restoreState()


def generate_payslip_pdf(salary) -> io.BytesIO:
    """
    Generate a clean, structured PDF payslip for printing or digital delivery.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=30,
        leftMargin=30,
        topMargin=30,
        bottomMargin=30
    )

    story = []
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'PayslipTitle',
        parent=styles['Heading1'],
        fontName=JP_FONT,
        fontSize=18,
        leading=22,
        alignment=1,  # Center
        spaceAfter=15
    )

    sub_style = ParagraphStyle(
        'PayslipSub',
        parent=styles['Normal'],
        fontName=JP_FONT,
        fontSize=10,
        leading=14
    )

    try:
        parts = salary.salary_month.split('-')
        period_str = f"{parts[0]}年 {parts[1]}月 給与支払明細書 (Salary Slip)"
    except Exception:
        period_str = f"{salary.salary_month} 給与支払明細書 (Salary Slip)"

    story.append(Paragraph(period_str, title_style))

    company_name = salary.admin.company_name or 'Smart Ledger'
    p_date_str = str(salary.payment_date) if salary.payment_date else salary.salary_month

    header_data = [
        [f"Company: {company_name}", f"Payment Date: {p_date_str}"],
        [f"Employee: {salary.employee.name} 様", f"Department/Role: {salary.employee.role}"],
    ]
    t_header = Table(header_data, colWidths=[260, 260])
    t_header.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), JP_FONT),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(t_header)
    story.append(Spacer(1, 12))

    # Payment & Deductions Table
    table_data = [
        ["支給 (Earnings)", "金額 (JPY)", "控除 (Deductions)", "金額 (JPY)"],
        ["基本給 (Base Salary)", f"¥{int(salary.basic_salary):,}", "健康保険料 (Health Insurance)", f"¥{int(salary.health_insurance):,}"],
        ["残業手当 (Overtime Pay)", f"¥{int(salary.overtime_allowance):,}", "厚生年金 (Welfare Pension)", f"¥{int(salary.welfare_pension):,}"],
        ["その他手当 (Allowances)", f"¥{int(salary.allowances):,}", "雇用保険 (Employment Insurance)", f"¥{int(salary.employment_insurance):,}"],
        ["非課税通勤費 (Commuting)", f"¥{int(salary.commuting_allowance):,}", "社会保険計 (Total Social Insurance)", f"¥{int(salary.total_social_insurance):,}"],
        ["課税支給額 (Taxable Gross)", f"¥{int(salary.taxable_payment):,}", "所得税 (Income Tax)", f"¥{int(salary.income_tax):,}"],
        ["", "", "住民税 (Resident Tax)", f"¥{int(salary.resident_tax):,}"],
        ["", "", "その他控除 (Other Deductions)", f"¥{int(salary.other_deductions):,}"],
        ["支給額合計 (Total Gross)", f"¥{int(salary.gross_payment):,}", "控除額合計 (Total Deductions)", f"¥{int(salary.total_deductions):,}"],
        ["差引支給額 (Net Take-Home Pay)", f"¥{int(salary.net_amount):,}", "", ""],
    ]

    t_main = Table(table_data, colWidths=[160, 100, 160, 100])
    t_main.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (1, 0), colors.HexColor('#EBF3FB')),
        ('BACKGROUND', (2, 0), (3, 0), colors.HexColor('#FBEBEB')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#222222')),
        ('FONTNAME', (0, 0), (-1, -1), JP_FONT),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('ALIGN', (3, 0), (3, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CCCCCC')),
        ('BACKGROUND', (0, 8), (1, 8), colors.HexColor('#DCE9F6')),
        ('BACKGROUND', (2, 8), (3, 8), colors.HexColor('#F9DFDF')),
        ('BACKGROUND', (0, 9), (1, 9), colors.HexColor('#D0E4A9')),
    ]))
    story.append(t_main)
    story.append(Spacer(1, 14))

    # Attendance Table
    story.append(Paragraph("勤怠 (Attendance)", ParagraphStyle('SecTitle', parent=styles['Heading3'], fontName=JP_FONT, fontSize=11)))
    story.append(Spacer(1, 4))

    req_hrs_val = getattr(salary, 'required_working_hours', None) or (salary.working_days * Decimal('8.0'))

    att_data = [
        ["所定時間 (Required)", "実働時間 (Worked)", "普通残業 (OT)", "休日残業 (Holiday)", "深夜残業 (Midnight)"],
        [f"{req_hrs_val} h", f"{salary.working_hours} h", f"{salary.overtime_hours} h", f"{salary.holiday_overtime_hours} h", f"{salary.midnight_overtime_hours} h"],
        ["勤務日数 (Days)", "有給日数 (Paid Leave)", "公休日数 (Off Days)", "欠勤日数 (Absence)", "遅刻・早退 (Late/Early)"],
        [f"{salary.working_days} days", f"{salary.paid_leaves} days", f"{salary.statutory_leaves} days", f"{salary.absence_days} days", f"{salary.late_early_count} times / {salary.late_early_hours}h"],
    ]

    t_att = Table(att_data, colWidths=[104, 104, 104, 104, 104])
    t_att.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F5F5F5')),
        ('BACKGROUND', (0, 2), (-1, 2), colors.HexColor('#F5F5F5')),
        ('FONTNAME', (0, 0), (-1, -1), JP_FONT),
        ('FONTSIZE', (0, 0), (-1, -1), 8.5),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#DDDDDD')),
    ]))
    story.append(t_att)

    if salary.remarks:
        story.append(Spacer(1, 10))
        story.append(Paragraph(f"<b>備考 (Remarks):</b> {salary.remarks}", sub_style))

    doc.build(story, onFirstPage=_add_watermark, onLaterPages=_add_watermark)
    buffer.seek(0)
    return buffer


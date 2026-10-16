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
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls
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


def _set_cell_bg(cell, hex_color: str):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{hex_color}"/>')
    tcPr.append(shd)


def _set_cell_borders(cell, color="CCCCCC", sz="4"):
    tcPr = cell._tc.get_or_add_tcPr()
    borders = parse_xml(
        f'<w:tcBorders {nsdecls("w")}>'
        f'<w:top w:val="single" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'<w:left w:val="single" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'<w:bottom w:val="single" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'<w:right w:val="single" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'</w:tcBorders>'
    )
    tcPr.append(borders)


def generate_payslip_docx(salary) -> io.BytesIO:
    """
    Generate an editable Microsoft Word (.docx) payslip document matching
    the Japanese salary payment statement layout (給与支払明細書).
    """
    import docx
    from docx.shared import Inches, Pt, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.enum.table import WD_TABLE_ALIGNMENT

    doc = docx.Document()

    # Set margins
    for section in doc.sections:
        section.top_margin = Inches(0.55)
        section.bottom_margin = Inches(0.55)
        section.left_margin = Inches(0.65)
        section.right_margin = Inches(0.65)

    def num(v):
        try:
            return f"¥{int(round(float(v or 0))):,}"
        except Exception:
            return "¥0"

    admin_user = salary.admin
    company_name = (
        getattr(admin_user, 'company_name', None) or
        getattr(admin_user, 'first_name', '') or
        'ILYAS SONS 合同会社'
    )
    emp_name = salary.employee.name if salary.employee else 'Employee'
    emp_role = salary.employee.role if salary.employee and salary.employee.role else '-'

    try:
        parts = salary.salary_month.split('-')
        year_str = parts[0]
        month_str = parts[1]
        period_title = f"{year_str}年 {month_str}月 給与支払明細書"
        period_sub = f"Salary Payment Statement ({salary.salary_month})"
    except Exception:
        period_title = f"{salary.salary_month} 給与支払明細書"
        period_sub = f"Salary Payment Statement ({salary.salary_month})"

    p_date = str(salary.payment_date) if salary.payment_date else salary.salary_month

    # 1. Main Title
    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_title.paragraph_format.space_before = Pt(0)
    p_title.paragraph_format.space_after = Pt(1)
    run_title = p_title.add_run(period_title)
    run_title.font.name = 'Arial'
    run_title.font.size = Pt(16)
    run_title.font.bold = True
    run_title.font.color.rgb = RGBColor(15, 23, 42)

    p_sub = doc.add_paragraph()
    p_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_sub.paragraph_format.space_before = Pt(0)
    p_sub.paragraph_format.space_after = Pt(10)
    run_sub = p_sub.add_run(period_sub)
    run_sub.font.name = 'Arial'
    run_sub.font.size = Pt(9)
    run_sub.font.color.rgb = RGBColor(100, 116, 139)

    # 2. Company & Employee Info Block
    meta_table = doc.add_table(rows=2, cols=2)
    meta_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    meta_table.autofit = False

    meta_rows = [
        [(f"会社名 (Company): {company_name}", True), (f"支給日 (Payment Date): {p_date}", False)],
        [(f"氏名 (Employee): {emp_name} 様", True), (f"役職/所属 (Role/Dept): {emp_role}", False)]
    ]
    for r_idx, row_data in enumerate(meta_rows):
        for c_idx, (text, is_bold) in enumerate(row_data):
            cell = meta_table.cell(r_idx, c_idx)
            cell.width = Inches(3.55)
            _set_cell_borders(cell, color="CBD5E1", sz="4")
            _set_cell_bg(cell, "F8FAFC")
            p = cell.paragraphs[0]
            p.paragraph_format.space_before = Pt(2.5)
            p.paragraph_format.space_after = Pt(2.5)
            run = p.add_run(text)
            run.font.name = 'Arial'
            run.font.size = Pt(9)
            run.font.bold = is_bold
            run.font.color.rgb = RGBColor(30, 41, 59)

    doc.add_paragraph().paragraph_format.space_after = Pt(4)

    # 3. Highlighted Net Pay Callout Box
    net_table = doc.add_table(rows=1, cols=1)
    net_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    net_cell = net_table.cell(0, 0)
    net_cell.width = Inches(7.1)
    _set_cell_bg(net_cell, "0F172A")
    _set_cell_borders(net_cell, color="0F172A", sz="6")
    np = net_cell.paragraphs[0]
    np.alignment = WD_ALIGN_PARAGRAPH.CENTER
    np.paragraph_format.space_before = Pt(5)
    np.paragraph_format.space_after = Pt(5)

    n_lbl = np.add_run("差引支給額 (Net Take-Home Pay):   ")
    n_lbl.font.name = 'Arial'
    n_lbl.font.size = Pt(11)
    n_lbl.font.bold = True
    n_lbl.font.color.rgb = RGBColor(203, 213, 225)

    n_val = np.add_run(num(salary.net_amount))
    n_val.font.name = 'Arial'
    n_val.font.size = Pt(15)
    n_val.font.bold = True
    n_val.font.color.rgb = RGBColor(52, 211, 153)

    doc.add_paragraph().paragraph_format.space_after = Pt(6)

    # 4. Earnings and Deductions Table
    rows_data = [
        ("支給項目 (Earnings)", "金額 (JPY)", "控除項目 (Deductions)", "金額 (JPY)", True, False, False),
        ("基本給 (Base Salary)", num(salary.basic_salary), "健康保険料 (Health Insurance)", num(salary.health_insurance), False, False, False),
        ("残業手当 (Overtime Pay)", num(salary.overtime_allowance), "厚生年金 (Welfare Pension)", num(salary.welfare_pension), False, False, False),
        ("その他手当 (Allowances)", num(salary.allowances), "雇用保険 (Employment Insurance)", num(salary.employment_insurance), False, False, False),
        ("非課税通勤費 (Commuting)", num(salary.commuting_allowance), "社会保険計 (Total Social Insurance)", num(salary.total_social_insurance), False, False, False),
        ("課税支給額 (Taxable Gross)", num(salary.taxable_payment), "所得税 (Income Tax)", num(salary.income_tax), False, False, False),
        ("", "", "住民税 (Resident Tax)", num(salary.resident_tax) if float(salary.resident_tax or 0) > 0 else "-", False, False, False),
        ("", "", "欠勤・不就労控除 (Leave Ded.)", num(salary.leave_deduction) if float(salary.leave_deduction or 0) > 0 else "-", False, False, False),
        ("", "", "その他控除 (Other Deductions)", num(salary.other_deductions) if float(salary.other_deductions or 0) > 0 else "-", False, False, False),
        ("支給合計 (Total Gross)", num(salary.gross_payment), "控除合計 (Total Deductions)", num(salary.total_deductions), False, True, False),
        ("差引支給額 (Net Pay)", num(salary.net_amount), "", "", False, False, True),
    ]

    main_table = doc.add_table(rows=len(rows_data), cols=4)
    main_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    main_table.autofit = False

    col_widths = [Inches(2.15), Inches(1.4), Inches(2.15), Inches(1.4)]

    for r_idx, (e_item, e_val, d_item, d_val, is_head, is_tot, is_net) in enumerate(rows_data):
        cells = [main_table.cell(r_idx, i) for i in range(4)]
        for i, c in enumerate(cells):
            c.width = col_widths[i]
            _set_cell_borders(c, color="CCCCCC", sz="4")

        # Shading
        if is_head:
            _set_cell_bg(cells[0], "EBF3FB")
            _set_cell_bg(cells[1], "EBF3FB")
            _set_cell_bg(cells[2], "FBEBEB")
            _set_cell_bg(cells[3], "FBEBEB")
        elif is_tot:
            _set_cell_bg(cells[0], "DCE9F6")
            _set_cell_bg(cells[1], "DCE9F6")
            _set_cell_bg(cells[2], "F9DFDF")
            _set_cell_bg(cells[3], "F9DFDF")
        elif is_net:
            _set_cell_bg(cells[0], "D0E4A9")
            _set_cell_bg(cells[1], "D0E4A9")
            _set_cell_bg(cells[2], "FFFFFF")
            _set_cell_bg(cells[3], "FFFFFF")
        else:
            _set_cell_bg(cells[0], "FFFFFF")
            _set_cell_bg(cells[1], "FFFFFF")
            _set_cell_bg(cells[2], "FFFFFF")
            _set_cell_bg(cells[3], "FFFFFF")

        cell_values = [
            (cells[0], e_item, False, is_head or is_tot or is_net),
            (cells[1], e_val, True, is_head or is_tot or is_net),
            (cells[2], d_item, False, is_head or is_tot),
            (cells[3], d_val, True, is_head or is_tot)
        ]

        for c, text, is_right, is_bold in cell_values:
            p = c.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.RIGHT if is_right else WD_ALIGN_PARAGRAPH.LEFT
            p.paragraph_format.space_before = Pt(2.5)
            p.paragraph_format.space_after = Pt(2.5)
            run = p.add_run(text)
            run.font.name = 'Arial'
            run.font.size = Pt(8.5) if not (is_head or is_tot or is_net) else Pt(9)
            run.font.bold = is_bold
            if is_tot or is_net:
                run.font.color.rgb = RGBColor(15, 23, 42)
            else:
                run.font.color.rgb = RGBColor(30, 41, 59)

    doc.add_paragraph().paragraph_format.space_after = Pt(6)

    # 5. Attendance Table
    p_att_title = doc.add_paragraph()
    p_att_title.paragraph_format.space_before = Pt(3)
    p_att_title.paragraph_format.space_after = Pt(2)
    run_att = p_att_title.add_run("勤怠明細 (Attendance Summary)")
    run_att.font.name = 'Arial'
    run_att.font.size = Pt(10)
    run_att.font.bold = True
    run_att.font.color.rgb = RGBColor(15, 23, 42)

    req_hrs = getattr(salary, 'required_working_hours', None) or (salary.working_days * Decimal('8.0'))

    att_rows = [
        ["所定時間 (Required)", "実働時間 (Worked)", "普通残業 (OT)", "休日残業 (Holiday)", "深夜残業 (Midnight)"],
        [f"{req_hrs} h", f"{salary.working_hours} h", f"{salary.overtime_hours} h", f"{salary.holiday_overtime_hours} h", f"{salary.midnight_overtime_hours} h"],
        ["勤務日数 (Days)", "有給日数 (Paid Leave)", "公休日数 (Off Days)", "欠勤日数 (Absence)", "遅刻・早退 (Late/Early)"],
        [f"{salary.working_days} days", f"{salary.paid_leaves} days", f"{salary.statutory_leaves} days", f"{salary.absence_days} days", f"{salary.late_early_count} times ({salary.late_early_hours}h)"]
    ]

    att_table = doc.add_table(rows=4, cols=5)
    att_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    att_table.autofit = False

    for r_idx, row in enumerate(att_rows):
        is_h = (r_idx % 2 == 0)
        for c_idx, val in enumerate(row):
            c = att_table.cell(r_idx, c_idx)
            c.width = Inches(1.42)
            _set_cell_borders(c, color="CCCCCC", sz="4")
            _set_cell_bg(c, "F1F5F9" if is_h else "FFFFFF")
            p = c.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_before = Pt(2)
            p.paragraph_format.space_after = Pt(2)
            run = p.add_run(val)
            run.font.name = 'Arial'
            run.font.size = Pt(8.5)
            run.font.bold = is_h
            run.font.color.rgb = RGBColor(30, 41, 59)

    # 6. Remarks if present
    if salary.remarks:
        doc.add_paragraph().paragraph_format.space_after = Pt(4)
        p_rem = doc.add_paragraph()
        p_rem.paragraph_format.space_before = Pt(2)
        p_rem.paragraph_format.space_after = Pt(2)
        r_lbl = p_rem.add_run("備考 (Remarks): ")
        r_lbl.font.name = 'Arial'
        r_lbl.font.size = Pt(9)
        r_lbl.font.bold = True
        r_txt = p_rem.add_run(str(salary.remarks))
        r_txt.font.name = 'Arial'
        r_txt.font.size = Pt(9)

    output = io.BytesIO()
    doc.save(output)
    output.seek(0)
    return output


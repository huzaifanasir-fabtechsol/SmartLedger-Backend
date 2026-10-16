"""
Letterhead Generator for Microsoft Word (.docx) export.
Produces an editable Word document matching company letterhead branding,
including logos, corporate colors, header styles, and contact footer.
"""

import io
import re
import base64
from datetime import datetime

import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls


def _clean_hex(hex_str: str, default: str = "1E3A8A") -> str:
    """Normalize hex color string to 6 uppercase characters without #."""
    if not hex_str:
        return default
    cleaned = re.sub(r'[^0-9a-fA-F]', '', str(hex_str)).upper()
    if len(cleaned) == 6:
        return cleaned
    if len(cleaned) == 3:
        return ''.join(c * 2 for c in cleaned)
    return default


def _hex_to_rgb(hex_str: str, default=(30, 58, 138)) -> RGBColor:
    """Convert hex string to docx RGBColor."""
    c = _clean_hex(hex_str)
    try:
        r = int(c[0:2], 16)
        g = int(c[2:4], 16)
        b = int(c[4:6], 16)
        return RGBColor(r, g, b)
    except Exception:
        return RGBColor(*default)


def _set_cell_bg(cell, hex_color: str):
    """Set background color of a table cell."""
    tcPr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{hex_color}"/>')
    tcPr.append(shd)


def _set_cell_no_borders(cell):
    """Remove borders from a table cell."""
    tcPr = cell._tc.get_or_add_tcPr()
    borders = parse_xml(
        f'<w:tcBorders {nsdecls("w")}>'
        f'<w:top w:val="none"/>'
        f'<w:left w:val="none"/>'
        f'<w:bottom w:val="none"/>'
        f'<w:right w:val="none"/>'
        f'</w:tcBorders>'
    )
    tcPr.append(borders)


def _add_accent_bar(container, c1_hex: str, c2_hex: str, width_in: float = 6.77, reverse: bool = False):
    """
    Add a dual-color decorative accent bar table matching the letterhead palette.
    """
    table = container.add_table(rows=2, cols=1)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False

    top_color = c2_hex if reverse else c1_hex
    bottom_color = c1_hex if reverse else c2_hex
    top_height = 3 if reverse else 6
    bottom_height = 6 if reverse else 3

    # Row 0
    c0 = table.cell(0, 0)
    c0.width = Inches(width_in)
    _set_cell_no_borders(c0)
    _set_cell_bg(c0, top_color)
    p0 = c0.paragraphs[0]
    p0.paragraph_format.space_before = Pt(0)
    p0.paragraph_format.space_after = Pt(0)
    p0.paragraph_format.line_spacing = Pt(top_height)
    r0 = p0.add_run(" ")
    r0.font.size = Pt(top_height)

    # Row 1
    c1 = table.cell(1, 0)
    c1.width = Inches(width_in)
    _set_cell_no_borders(c1)
    _set_cell_bg(c1, bottom_color)
    p1 = c1.paragraphs[0]
    p1.paragraph_format.space_before = Pt(0)
    p1.paragraph_format.space_after = Pt(0)
    p1.paragraph_format.line_spacing = Pt(bottom_height)
    r1 = p1.add_run(" ")
    r1.font.size = Pt(bottom_height)


def generate_letterhead_docx(source) -> io.BytesIO:
    """
    Generate an editable Microsoft Word (.docx) document formatted with the
    company's letterhead design, branding, and contact details.

    Accepts either a Letterhead model instance or a dictionary of form values.
    """
    if hasattr(source, 'name'):
        company_name = source.name or 'Company Name'
        logo = source.logo or ''
        tagline = source.tagline or ''
        address = source.address or ''
        phone = source.phone or ''
        email = source.email or ''
        website = source.website or ''
        registration = source.registration or ''
        template = source.template or 'angles'
        color1 = source.color1 or '#1e3a8a'
        color2 = source.color2 or '#3b82f6'
        show_date = source.show_date
        date_str = datetime.now().strftime('%Y-%m-%d')
    elif isinstance(source, dict):
        company_name = source.get('name') or source.get('companyName') or 'Company Name'
        logo = source.get('logo', '')
        tagline = source.get('tagline', '')
        address = source.get('address', '')
        phone = source.get('phone', '')
        email = source.get('email', '')
        website = source.get('website', '')
        registration = source.get('registration', '')
        template = source.get('template', 'angles')
        color1 = source.get('color1', '#1e3a8a')
        color2 = source.get('color2', '#3b82f6')
        show_date = source.get('show_date', source.get('showDate', True))
        date_str = source.get('date') or datetime.now().strftime('%Y-%m-%d')
    else:
        company_name = 'Company Name'
        logo = ''
        tagline = ''
        address = ''
        phone = ''
        email = ''
        website = ''
        registration = ''
        template = 'angles'
        color1 = '#1e3a8a'
        color2 = '#3b82f6'
        show_date = True
        date_str = datetime.now().strftime('%Y-%m-%d')

    c1_hex = _clean_hex(color1, "1E3A8A")
    c2_hex = _clean_hex(color2, "3B82F6")
    c1_rgb = _hex_to_rgb(c1_hex)
    c2_rgb = _hex_to_rgb(c2_hex)
    is_centered = template in ('wave', 'classic')

    doc = docx.Document()
    section = doc.sections[0]
    section.page_width = Inches(8.27)
    section.page_height = Inches(11.69)
    section.top_margin = Inches(0.5)
    section.bottom_margin = Inches(0.5)
    section.left_margin = Inches(0.75)
    section.right_margin = Inches(0.75)

    usable_width_in = 6.77

    # 1. Top Decorative Header Accent Bar
    _add_accent_bar(doc, c1_hex, c2_hex, width_in=usable_width_in, reverse=False)

    p_spacer = doc.add_paragraph()
    p_spacer.paragraph_format.space_before = Pt(0)
    p_spacer.paragraph_format.space_after = Pt(8)

    # 2. Decode Logo if present
    logo_bytes = None
    if logo and isinstance(logo, str) and 'base64,' in logo:
        try:
            _, b64_part = logo.split('base64,', 1)
            logo_bytes = base64.b64decode(b64_part)
        except Exception:
            logo_bytes = None

    # 3. Header Branding Section
    if is_centered:
        # Centered Layout
        if logo_bytes:
            p_logo = doc.add_paragraph()
            p_logo.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p_logo.paragraph_format.space_before = Pt(0)
            p_logo.paragraph_format.space_after = Pt(4)
            r_img = p_logo.add_run()
            r_img.add_picture(io.BytesIO(logo_bytes), height=Inches(0.8))

        p_name = doc.add_paragraph()
        p_name.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_name.paragraph_format.space_before = Pt(0)
        p_name.paragraph_format.space_after = Pt(2)
        r_name = p_name.add_run(company_name)
        r_name.font.name = 'Segoe UI'
        r_name.font.size = Pt(22)
        r_name.font.bold = True
        r_name.font.color.rgb = c1_rgb

        if tagline:
            p_tag = doc.add_paragraph()
            p_tag.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p_tag.paragraph_format.space_before = Pt(0)
            p_tag.paragraph_format.space_after = Pt(12)
            r_tag = p_tag.add_run(tagline.upper())
            r_tag.font.name = 'Segoe UI'
            r_tag.font.size = Pt(8.5)
            r_tag.font.color.rgb = RGBColor(107, 114, 128)
        else:
            p_name.paragraph_format.space_after = Pt(12)
    else:
        # Left-Aligned Layout
        if logo_bytes:
            head_table = doc.add_table(rows=1, cols=2)
            head_table.alignment = WD_TABLE_ALIGNMENT.CENTER
            head_table.autofit = False

            c_logo = head_table.cell(0, 0)
            c_logo.width = Inches(1.8)
            _set_cell_no_borders(c_logo)
            c_logo.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            p_l = c_logo.paragraphs[0]
            p_l.paragraph_format.space_before = Pt(0)
            p_l.paragraph_format.space_after = Pt(0)
            r_img = p_l.add_run()
            r_img.add_picture(io.BytesIO(logo_bytes), height=Inches(0.85))

            c_text = head_table.cell(0, 1)
            c_text.width = Inches(usable_width_in - 1.8)
            _set_cell_no_borders(c_text)
            c_text.vertical_alignment = WD_ALIGN_VERTICAL.CENTER

            p_n = c_text.paragraphs[0]
            p_n.paragraph_format.space_before = Pt(0)
            p_n.paragraph_format.space_after = Pt(2)
            r_name = p_n.add_run(company_name)
            r_name.font.name = 'Segoe UI'
            r_name.font.size = Pt(22)
            r_name.font.bold = True
            r_name.font.color.rgb = c1_rgb

            if tagline:
                p_t = c_text.add_paragraph()
                p_t.paragraph_format.space_before = Pt(0)
                p_t.paragraph_format.space_after = Pt(0)
                r_tag = p_t.add_run(tagline.upper())
                r_tag.font.name = 'Segoe UI'
                r_tag.font.size = Pt(8.5)
                r_tag.font.color.rgb = RGBColor(107, 114, 128)

            p_post = doc.add_paragraph()
            p_post.paragraph_format.space_before = Pt(0)
            p_post.paragraph_format.space_after = Pt(12)
        else:
            p_name = doc.add_paragraph()
            p_name.paragraph_format.space_before = Pt(0)
            p_name.paragraph_format.space_after = Pt(2)
            r_name = p_name.add_run(company_name)
            r_name.font.name = 'Segoe UI'
            r_name.font.size = Pt(22)
            r_name.font.bold = True
            r_name.font.color.rgb = c1_rgb

            if tagline:
                p_tag = doc.add_paragraph()
                p_tag.paragraph_format.space_before = Pt(0)
                p_tag.paragraph_format.space_after = Pt(12)
                r_tag = p_tag.add_run(tagline.upper())
                r_tag.font.name = 'Segoe UI'
                r_tag.font.size = Pt(8.5)
                r_tag.font.color.rgb = RGBColor(107, 114, 128)
            else:
                p_name.paragraph_format.space_after = Pt(12)

    # 4. Date Line
    if show_date and date_str:
        p_date = doc.add_paragraph()
        p_date.alignment = WD_ALIGN_PARAGRAPH.RIGHT if not is_centered else WD_ALIGN_PARAGRAPH.CENTER
        p_date.paragraph_format.space_before = Pt(0)
        p_date.paragraph_format.space_after = Pt(18)
        r_dlbl = p_date.add_run("Date: ")
        r_dlbl.font.name = 'Segoe UI'
        r_dlbl.font.size = Pt(9.5)
        r_dlbl.font.bold = True
        r_dlbl.font.color.rgb = c1_rgb

        r_dval = p_date.add_run(str(date_str))
        r_dval.font.name = 'Segoe UI'
        r_dval.font.size = Pt(9.5)
        r_dval.font.color.rgb = RGBColor(55, 65, 81)

    # 5. Pre-formatted Editable Letter Content Body
    def add_body_p(text, before=0, after=6, bold=False, italic=False, color=RGBColor(31, 41, 55)):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(before)
        p.paragraph_format.space_after = Pt(after)
        p.paragraph_format.line_spacing = 1.2
        r = p.add_run(text)
        r.font.name = 'Segoe UI'
        r.font.size = Pt(10.5)
        r.font.bold = bold
        r.font.italic = italic
        r.font.color.rgb = color
        return p

    # Recipient block
    add_body_p("[Recipient Name]", after=1, color=RGBColor(100, 116, 139))
    add_body_p("[Recipient Title / Department]", after=1, color=RGBColor(100, 116, 139))
    add_body_p("[Company / Organization Name]", after=1, color=RGBColor(100, 116, 139))
    add_body_p("[Street Address]", after=1, color=RGBColor(100, 116, 139))
    add_body_p("[City, State / Prefecture, Postal Code]", after=16, color=RGBColor(100, 116, 139))

    # Subject line
    add_body_p("Subject: [Enter Letter Subject / Title Here]", after=12, bold=True, color=c1_rgb)

    # Salutation
    add_body_p("Dear [Recipient Name / Sir or Madam],", after=10)

    # Letter body paragraphs
    add_body_p(
        "[Type your letter content here. This letterhead document is fully editable, so you can compose letters, "
        "memos, formal proposals, invoices, or official notices directly in Microsoft Word or Google Docs.]",
        after=10
    )
    add_body_p(
        "[Add additional paragraphs, bullet points, terms, or descriptions as needed. You can change the typography, "
        "insert tables, or attach official stamps and signatures.]",
        after=18
    )

    # Sign-off block
    add_body_p("Sincerely,", after=40)
    add_body_p("[Authorized Signature]", after=2, color=RGBColor(100, 116, 139))
    add_body_p("[Signatory Name]", after=1, bold=True)
    add_body_p(f"[Title / Position, {company_name}]", after=24)

    # 6. Contact Details & Bottom Accent Bar in Body
    contact_parts = []
    if address:
        contact_parts.append(("Address", address))
    if phone:
        contact_parts.append(("Phone", phone))
    if email:
        contact_parts.append(("Email", email))
    if website:
        contact_parts.append(("Web", website))
    if registration:
        contact_parts.append(("Reg. No", registration))

    if contact_parts:
        p_c = doc.add_paragraph()
        p_c.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_c.paragraph_format.space_before = Pt(12)
        p_c.paragraph_format.space_after = Pt(4)

        for idx, (label, val) in enumerate(contact_parts):
            if idx > 0:
                r_sep = p_c.add_run("   |   ")
                r_sep.font.name = 'Segoe UI'
                r_sep.font.size = Pt(8)
                r_sep.font.color.rgb = RGBColor(156, 163, 175)

            r_l = p_c.add_run(f"{label}: ")
            r_l.font.name = 'Segoe UI'
            r_l.font.size = Pt(8)
            r_l.font.bold = True
            r_l.font.color.rgb = c1_rgb

            r_v = p_c.add_run(str(val))
            r_v.font.name = 'Segoe UI'
            r_v.font.size = Pt(8)
            r_v.font.color.rgb = RGBColor(75, 85, 99)

    _add_accent_bar(doc, c1_hex, c2_hex, width_in=usable_width_in, reverse=True)

    # 7. Also configure Section Footer for multi-page document continuity
    footer = section.footer
    f_p = footer.paragraphs[0]
    f_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    f_p.paragraph_format.space_before = Pt(2)
    f_p.paragraph_format.space_after = Pt(2)

    if contact_parts:
        for idx, (label, val) in enumerate(contact_parts):
            if idx > 0:
                r_f_sep = f_p.add_run(" | ")
                r_f_sep.font.name = 'Segoe UI'
                r_f_sep.font.size = Pt(7.5)
                r_f_sep.font.color.rgb = RGBColor(156, 163, 175)

            r_f_l = f_p.add_run(f"{label}: ")
            r_f_l.font.name = 'Segoe UI'
            r_f_l.font.size = Pt(7.5)
            r_f_l.font.bold = True
            r_f_l.font.color.rgb = c1_rgb

            r_f_v = f_p.add_run(str(val))
            r_f_v.font.name = 'Segoe UI'
            r_f_v.font.size = Pt(7.5)
            r_f_v.font.color.rgb = RGBColor(75, 85, 99)
    else:
        r_f_comp = f_p.add_run(company_name)
        r_f_comp.font.name = 'Segoe UI'
        r_f_comp.font.size = Pt(8)
        r_f_comp.font.bold = True
        r_f_comp.font.color.rgb = c1_rgb

    output = io.BytesIO()
    doc.save(output)
    output.seek(0)
    return output

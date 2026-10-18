"""Page/flow manager shared by every document renderer.

``mode='full'``   one form per page with a title and filer block (mirrors the official forms).
``mode='simple'`` compact: forms flow one after another, zero rows and empty forms are dropped.
``lang``          'ja' or 'en'; labels are ``(ja, en)`` tuples resolved through ``tr``.
"""
import io
from collections import namedtuple
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, Table, TableStyle

from .fonts import font_for
from .i18n import tr
from .layout import CONTENT_W, MARGIN, PAGE_H, PAGE_W, en_date, fmt, jp_date, spaced

TOP = PAGE_H - 62
BOTTOM = 44
GRAY = colors.Color(0.93, 0.93, 0.93)

Row = namedtuple('Row', 'kind no label vals keep')


def H(label):
    """Section header row."""
    return Row('hdr', '', label, (), True)


def R(no, label, *vals, keep=False):
    """Normal line. In simple mode it is dropped when every value is empty/zero (unless keep)."""
    return Row('row', no, label, vals, keep)


def T(no, label, *vals, keep=False):
    """Total/result line (ruled above)."""
    return Row('total', no, label, vals, keep)


def _empty(vals):
    return all(v in (None, '', 0, 0.0) for v in vals)


class Writer:
    def __init__(self, data, lang='ja', mode='full'):
        self.data, self.lang, self.mode = data, lang, mode
        self.font = font_for(lang)
        self.buffer = io.BytesIO()
        self.c = canvas.Canvas(self.buffer, pagesize=(PAGE_W, PAGE_H))
        self.page = 0
        self.y = TOP
        self._open = False
        self._styles = {}

    # ---- text/company helpers ---------------------------------------------------------
    def t(self, label):
        return tr(label, self.lang)

    @property
    def full(self):
        return self.mode == 'full'

    @property
    def company(self):
        p, base = self.data.get('profile'), self.data['company']
        if self.lang == 'en':
            name = (p and p.legal_name_en) or base['name']
            address = (p and p.address_en) or base['address']
            rep = (p and (p.representative_name_en or p.representative_name_kana or p.representative_name)) or ''
        else:
            name, address = base['name'], base['address']
            rep = (p and p.representative_name) or ''
        return {'name': name, 'address': address, 'rep': rep,
                'phone': (p and p.phone) or '', 'corp_no': (p and p.corporate_number) or '',
                'tax_office': (p and p.tax_office) or ''}

    def period_text(self):
        per = self.data['period']
        if self.lang == 'ja':
            return f"第{per['term_no']}期　自 {jp_date(per['start_date'])}　至 {jp_date(per['end_date'])}"
        return f"Term {per['term_no']}: {en_date(per['start_date'])} - {en_date(per['end_date'])}"

    # ---- pages ------------------------------------------------------------------------
    def _ensure_page(self):
        if not self._open:
            self.page += 1
            self.y = TOP
            self._open = True

    def _footer(self):
        c = self.c
        c.setFont(self.font, 7)
        c.setFillColor(colors.Color(0.4, 0.4, 0.4))
        c.drawString(MARGIN, 24, self.company['name'])
        c.drawCentredString(PAGE_W / 2, 24, str(self.page))
        c.drawRightString(PAGE_W - MARGIN, 24, self.t(('参考資料(申告書そのものではありません)',
                                                       'Working copy - not a tax filing')))
        c.setFillColor(colors.black)

    def new_page(self):
        if self._open:
            self._footer()
            self.c.showPage()
            self._open = False
        self._ensure_page()

    def finish(self):
        if self._open:
            self._footer()
            self.c.showPage()
        self.c.save()
        self.buffer.seek(0)
        return self.buffer

    def space(self, h=8):
        self._ensure_page()
        self.y -= h

    # ---- headings ---------------------------------------------------------------------
    def begin_form(self, title, subtitle=None, filer=False, need=170):
        """Start a form: a fresh page in full mode, flowing on the current page in simple mode
        (``need`` = points of room required to start on the current page)."""
        if self.full or not self._open or self.y - BOTTOM < need:
            self.new_page()
        else:
            self.y -= 14
        c = self.c
        title_text = self.t(title)
        if self.full:
            if self.lang == 'ja':
                title_text = spaced(title_text)
            size = 15
            while size > 8 and c.stringWidth(title_text, self.font, size) > CONTENT_W:
                size -= 0.5                      # long titles shrink to fit the page
            c.setFont(self.font, size)
            c.drawCentredString(PAGE_W / 2, self.y - 8, title_text)
            width = c.stringWidth(title_text, self.font, size)
            x0 = PAGE_W / 2 - width / 2
            c.setLineWidth(0.8)
            c.line(x0, self.y - 12, x0 + width, self.y - 12)
            c.line(x0, self.y - 14, x0 + width, self.y - 14)
            self.y -= 30
            if subtitle and self.t(subtitle):
                c.setFont(self.font, 8)
                c.drawCentredString(PAGE_W / 2, self.y, self.t(subtitle))
                self.y -= 14
        else:
            c.setFont(self.font, 11)
            c.drawString(MARGIN, self.y - 4, title_text)
            c.setLineWidth(0.6)
            c.line(MARGIN, self.y - 8, PAGE_W - MARGIN, self.y - 8)
            self.y -= 20
            if subtitle and self.t(subtitle):
                c.setFont(self.font, 7.5)
                c.drawString(MARGIN, self.y, self.t(subtitle))
                self.y -= 11
        if filer and self.full:
            self.filer_block()
        elif filer:
            self.caption(f"{self.company['name']}  /  {self.period_text()}")
        self.y -= 4

    def caption(self, text, size=8, align='left'):
        self._ensure_page()
        self.c.setFont(self.font, size)
        text = self.t(text)
        if align == 'right':
            self.c.drawRightString(PAGE_W - MARGIN, self.y, text)
        elif align == 'center':
            self.c.drawCentredString(PAGE_W / 2, self.y, text)
        else:
            self.c.drawString(MARGIN, self.y, text)
        self.y -= size + 4

    def company_line(self, unit=True):
        self._ensure_page()
        self.c.setFont(self.font, 8)
        self.c.drawString(MARGIN, self.y, self.company['name'])
        if unit:
            self.c.drawRightString(PAGE_W - MARGIN, self.y, self.t(('（単位：　円）', '(Unit: JPY)')))
        self.y -= 14

    def filer_block(self):
        co = self.company
        rows = [
            [self.t(('納税地', 'Address')), co['address'], self.t(('電話', 'Phone')), co['phone']],
            [self.t(('法人名', 'Company name')), co['name'], self.t(('法人番号', 'Corporate no.')), co['corp_no']],
            [self.t(('代表者', 'Representative')), co['rep'], self.t(('税務署', 'Tax office')), co['tax_office']],
            [self.t(('事業年度', 'Fiscal period')), self.period_text(), '', ''],
        ]
        data = [[self.para(c, 7.5) if i in (1, 3) else c for i, c in enumerate(r)] for r in rows]
        cmds = [('GRID', (0, 0), (-1, -1), 0.5, colors.black), ('BACKGROUND', (0, 0), (0, -1), GRAY),
                ('BACKGROUND', (2, 0), (2, -1), GRAY), ('SPAN', (1, 3), (3, 3))]
        self.table(data, [70, 215, 70, CONTENT_W - 355], cmds, size=7.5, gap=8, keep=True)

    # ---- text -------------------------------------------------------------------------
    def style(self, size=8, align=0, leading=None):
        key = (size, align, leading)
        if key not in self._styles:
            self._styles[key] = ParagraphStyle(
                f's{size}{align}', fontName=self.font, fontSize=size, leading=leading or size * 1.25,
                alignment=align, wordWrap='CJK')
        return self._styles[key]

    def para(self, text, size=8, align=0):
        return Paragraph(escape(self.t(text)).replace('\n', '<br/>'), self.style(size, align))

    def paragraph(self, text, size=8, gap=4):
        """Wrapped text block across the full width (breaks to a new page if needed)."""
        self._ensure_page()
        p = self.para(text, size)
        _, h = p.wrap(CONTENT_W, PAGE_H)
        if self.y - h < BOTTOM:
            self.new_page()
        p.drawOn(self.c, MARGIN, self.y - h)
        self.y -= h + gap

    def lines(self, lines, size=9, leading=14, indent=0):
        self._ensure_page()
        for line in lines:
            if self.y < BOTTOM + leading:
                self.new_page()
            self.c.setFont(self.font, size)
            self.c.drawString(MARGIN + indent, self.y, self.t(line))
            self.y -= leading

    # ---- tables -----------------------------------------------------------------------
    def table(self, data, widths, cmds=(), size=8, repeat=1, gap=10, x=MARGIN, keep=False):
        """Draw a platypus table at the cursor, splitting across pages when it does not fit."""
        self._ensure_page()
        style = [('FONTNAME', (0, 0), (-1, -1), self.font), ('FONTSIZE', (0, 0), (-1, -1), size),
                 ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), ('TOPPADDING', (0, 0), (-1, -1), 2.2),
                 ('BOTTOMPADDING', (0, 0), (-1, -1), 2.2), ('LEFTPADDING', (0, 0), (-1, -1), 3),
                 ('RIGHTPADDING', (0, 0), (-1, -1), 3)] + list(cmds)
        tbl = Table(data, colWidths=widths, repeatRows=repeat)
        tbl.setStyle(TableStyle(style))
        width = sum(widths)
        for _ in range(60):          # hard stop against pathological tables
            _, h = tbl.wrapOn(self.c, width, PAGE_H)
            room = self.y - BOTTOM
            if keep and h > room and h <= TOP - BOTTOM and self.y < TOP - 1:
                self.new_page()      # statement tables stay on one page when they can
                continue
            if h <= room:
                tbl.drawOn(self.c, x, self.y - h)
                self.y -= h + gap
                return
            if room < 60:
                self.new_page()
                continue
            parts = tbl.split(width, room)
            if len(parts) < 2:
                if self.y < TOP - 1:
                    self.new_page()
                    continue
                tbl.drawOn(self.c, x, self.y - h)      # taller than a page: draw anyway
                self.y -= h + gap
                return
            _, h0 = parts[0].wrapOn(self.c, width, PAGE_H)
            parts[0].drawOn(self.c, x, self.y - h0)
            self.new_page()
            tbl = parts[1]

    def kv_table(self, rows, widths=None, size=8):
        data = [[self.t(k), self.para(v, size)] for k, v in rows]
        widths = widths or [150, CONTENT_W - 150]
        self.table(data, widths, [('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                                  ('BACKGROUND', (0, 0), (0, -1), GRAY)], size=size, repeat=0)

    def lines_table(self, columns, rows, size=8, no_header=False, extra_cmds=()):
        """Numbered-line form. columns: [(header, width, align)] with the first = line no., second = label.
        rows: H/R/T rows. Right-aligned value columns are formatted as whole yen."""
        if not self.full:
            rows = self._simplify(rows)
        if not rows:
            return
        headers = [self.t(h) for h, _, _ in columns]
        data = [headers] if not no_header else []
        offset = 0 if no_header else 1
        cmds = [('GRID', (0, 0), (-1, -1), 0.5, colors.black)]
        if not no_header:
            cmds += [('BACKGROUND', (0, 0), (-1, 0), GRAY), ('ALIGN', (0, 0), (-1, 0), 'CENTER')]
        for idx, row in enumerate(rows, start=offset):
            if row.kind == 'hdr':
                data.append([''] + [self.para(row.label, size)] + [''] * (len(columns) - 2))
                cmds += [('SPAN', (1, idx), (-1, idx)), ('BACKGROUND', (0, idx), (-1, idx), GRAY)]
                continue
            vals = [fmt(v) if not isinstance(v, float) else f'{v:g}' for v in row.vals]
            vals += [''] * (len(columns) - 2 - len(vals))
            data.append([str(row.no), self.para(row.label, size)] + vals)
            if row.kind == 'total':
                cmds.append(('LINEABOVE', (0, idx), (-1, idx), 1.0, colors.black))
        for ci, (_, _, align) in enumerate(columns):
            al = {'l': 'LEFT', 'c': 'CENTER', 'r': 'RIGHT'}[align]
            cmds.append(('ALIGN', (ci, offset), (ci, -1), al))
        self.table(data, [w for _, w, _ in columns], cmds + list(extra_cmds), size=size,
                   repeat=0 if no_header else 1)

    @staticmethod
    def _simplify(rows):
        kept = [r for r in rows if r.kind == 'hdr' or r.keep or not _empty(r.vals)]
        out = []
        for i, r in enumerate(kept):
            if r.kind == 'hdr' and (i + 1 == len(kept) or kept[i + 1].kind == 'hdr'):
                continue
            out.append(r)
        return out

    def simple_skip(self):
        """True when a form with nothing to show should be omitted (simple mode only)."""
        return not self.full

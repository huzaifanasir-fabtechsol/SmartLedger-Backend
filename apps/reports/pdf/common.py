"""Helpers shared by the tax-form renderers."""
from .layout import CONTENT_W, MARGIN, PAGE_W


def jp_name(ja_name):
    """Subtitle for English PDFs: the official Japanese form name (empty in Japanese PDFs)."""
    return ('', f'Japanese form name: {ja_name}')


def cols(n_values=1, headers=None, label=('項目', 'Item'), value_w=100, no=('番号', 'No.'), no_w=34):
    """Column spec for ``Writer.lines_table``: line no., label, then ``n_values`` right-aligned amounts."""
    headers = headers or [('金額(円)', 'Amount (JPY)')] * n_values
    label_w = CONTENT_W - no_w - value_w * n_values
    return [(no, no_w, 'c'), (label, label_w, 'l')] + [(h, value_w, 'r') for h in headers]


def power_of_attorney(w, matters, authority):
    """Blank power-of-attorney form (委任状). Signature/seal are left for the user."""
    p, co = w.data.get('profile'), w.company
    w.begin_form(('委任状', 'Power of Attorney'), jp_name('委任状'))
    per = w.data['period']
    w.paragraph((
        '私は、下記の税理士を代理人と定め、下記の事項に関する一切の権限を委任します。',
        'I hereby appoint the tax accountant named below as my agent and delegate full authority over the '
        'matters listed below.'), size=9, gap=8)
    acc = lambda attr: (getattr(p, attr, '') if p else '') or ''
    w.kv_table([
        (('委任者 (納税者)', 'Principal (taxpayer)'), ''),
        (('住所 (所在地)', 'Address'), co['address']),
        (('名称', 'Company name'), co['name']),
        (('代表者', 'Representative'), co['rep']),
        (('電話番号', 'Phone'), co['phone']),
        (('受任者 (税理士)', 'Agent (tax accountant)'), ''),
        (('氏名 (名称)', 'Name'), acc('accountant_name')),
        (('事務所所在地', 'Office address'), acc('accountant_address')),
        (('電話番号', 'Phone'), acc('accountant_phone')),
        (('税理士登録番号', 'Registration no.'), acc('accountant_registration')),
        (('提出先', 'Filed with'), authority),
        (('対象期間', 'Period'), w.period_text()),
        (('委任事項', 'Matters delegated'), matters),
    ], size=8.5)
    w.space(30)
    c = w.c
    c.setFont(w.font, 9)
    c.drawString(MARGIN, w.y, w.t(('令和　　年　　月　　日', 'Date: ____________________')))
    w.y -= 38
    c.drawString(MARGIN, w.y, w.t(('委任者 署名・押印', 'Principal signature / seal')))
    c.line(MARGIN + 130, w.y - 2, PAGE_W - MARGIN, w.y - 2)
    w.y -= 20

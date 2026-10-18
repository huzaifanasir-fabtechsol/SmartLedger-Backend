"""決算報告書 / Financial Statements: cover, balance sheet, P&L, SG&A schedule,
statement of changes in equity, notes."""
from reportlab.lib import colors

from .layout import CONTENT_W, PAGE_H, PAGE_W, en_date, fmt, jp_date, spaced

IND = '　'


def _sp(w, ja, en):
    """Heading/total labels are letter-spaced in Japanese statements."""
    return spaced(ja) if w.lang == 'ja' else en


def _period(w):
    per = w.data['period']
    if w.lang == 'ja':
        return f"{jp_date(per['start_date'])} 〜 {jp_date(per['end_date'])}"
    return f"{en_date(per['start_date'])} - {en_date(per['end_date'])}"


def _ind(w, n):
    return (IND if w.lang == 'ja' else '  ') * n


def draw_cover(w):
    if not w.full:
        return
    w.new_page()
    c, per, co = w.c, w.data['period'], w.company
    mid = PAGE_H * 0.58
    c.setFont(w.font, 30)
    c.drawCentredString(PAGE_W / 2, mid, spaced('決算報告書') if w.lang == 'ja' else 'FINANCIAL STATEMENTS')
    c.setFont(w.font, 13)
    c.drawCentredString(PAGE_W / 2, mid - 120, w.t((f"第 {per['term_no']} 期", f"Term {per['term_no']}")))
    c.setFont(w.font, 9)
    if w.lang == 'ja':
        c.drawCentredString(PAGE_W / 2, mid - 140, f"自 {jp_date(per['start_date'])}")
        c.drawCentredString(PAGE_W / 2, mid - 154, f"至 {jp_date(per['end_date'])}")
    else:
        c.drawCentredString(PAGE_W / 2, mid - 140, f"From {en_date(per['start_date'])}")
        c.drawCentredString(PAGE_W / 2, mid - 154, f"To {en_date(per['end_date'])}")
    c.setFont(w.font, 14)
    c.drawCentredString(PAGE_W / 2, 120, co['name'])
    c.setFont(w.font, 9)
    c.drawCentredString(PAGE_W / 2, 100, co['address'])


# ---------------------------------------------------------------- balance sheet
def _bs_left(w, bs):
    rows = [(('【流動資産】', 'Current assets'), bs['current_assets_total'], 'section')]
    rows += [(IND + i['label'], i['amount'], 'item') for i in bs['current_assets']]
    if bs['tangible_assets'] or bs['investments']:
        rows.append((('【固定資産】', 'Fixed assets'), bs['fixed_assets_total'], 'section'))
        if bs['tangible_assets']:
            rows.append((IND + w.t(('有形固定資産', 'Tangible fixed assets')), bs['tangible_total'], 'item'))
            rows += [(IND * 2 + i['label'], i['amount'], 'item') for i in bs['tangible_assets']]
        if bs['investments']:
            rows.append((IND + w.t(('投資その他の資産', 'Investments and other assets')), bs['investments_total'], 'item'))
            rows += [(IND * 2 + i['label'], i['amount'], 'item') for i in bs['investments']]
    if bs['deferred_assets']:
        rows.append((('【繰延資産】', 'Deferred assets'), bs['deferred_total'], 'section'))
        rows += [(IND + i['label'], i['amount'], 'item') for i in bs['deferred_assets']]
    return rows


def _bs_right(w, bs):
    rows = []
    if bs['current_liabilities']:
        rows.append((('【流動負債】', 'Current liabilities'), bs['current_liabilities_total'], 'section'))
        rows += [(IND + i['label'], i['amount'], 'item') for i in bs['current_liabilities']]
    if bs['fixed_liabilities']:
        rows.append((('【固定負債】', 'Long-term liabilities'), bs['fixed_liabilities_total'], 'section'))
        rows += [(IND + i['label'], i['amount'], 'item') for i in bs['fixed_liabilities']]
    rows.append((_sp(w, '負債の部合計', 'Total liabilities'), bs['liabilities_total'], 'liab_total'))
    rows.append((_sp(w, '純資産の部', 'NET ASSETS'), None, 'equity_header'))
    rows += [
        (('【社員資本】', "Members' equity"), bs['equity_total'], 'section'),
        (IND + w.t(('資本金', 'Capital')), bs['capital'], 'item'),
        (IND + w.t(('利益剰余金', 'Retained earnings')), bs['retained_earnings'], 'item'),
        (IND * 2 + w.t(('その他利益剰余金', 'Other retained earnings')), bs['retained_earnings'], 'item'),
        (IND * 3 + w.t(('繰越利益剰余金', 'Retained earnings brought forward')), bs['retained_earnings'], 'item'),
        (_sp(w, '純資産の部合計', 'Total net assets'), bs['equity_total'], 'equity_total'),
    ]
    return rows


def draw_balance_sheet(w):
    bs = w.data['bs']
    end = w.data['period']['end_date']
    w.begin_form(('貸借対照表', 'Balance Sheet'),
                 (f'{jp_date(end)}　現在', f'As of {en_date(end)}'))
    w.company_line()

    left, right = _bs_left(w, bs), _bs_right(w, bs)
    size = max(len(left), len(right))
    left += [('', None, 'blank')] * (size - len(left))
    right = right[:-1] + [('', None, 'blank')] * (size - len(right)) + right[-1:]

    table = [[_sp(w, '資産の部', 'ASSETS'), '', _sp(w, '負債の部', 'LIABILITIES'), ''],
             [_sp(w, '科目', 'Account'), _sp(w, '金額', 'Amount'), _sp(w, '科目', 'Account'), _sp(w, '金額', 'Amount')]]
    for (ll, la, _), (rl, ra, _) in zip(left, right):
        table.append([w.t(ll), fmt(la), w.t(rl), fmt(ra)])
    table.append([_sp(w, '資産の部合計', 'Total assets'), fmt(bs['assets_total']),
                  _sp(w, '負債及び純資産の部合計', 'Total liabilities and net assets'), fmt(bs['liabilities_and_equity_total'])])

    last = len(table) - 1
    cmds = [
        ('ALIGN', (0, 0), (-1, 1), 'CENTER'),
        ('ALIGN', (1, 2), (1, -1), 'RIGHT'), ('ALIGN', (3, 2), (3, -1), 'RIGHT'),
        ('SPAN', (0, 0), (1, 0)), ('SPAN', (2, 0), (3, 0)),
        ('BOX', (0, 0), (-1, -1), 0.8, colors.black),
        ('LINEAFTER', (0, 0), (2, -1), 0.5, colors.black),
        ('LINEBELOW', (0, 0), (-1, 1), 0.5, colors.black),
        ('LINEABOVE', (0, last), (-1, last), 0.8, colors.black),
        ('ALIGN', (0, last), (0, last), 'CENTER'), ('ALIGN', (2, last), (2, last), 'CENTER'),
    ]
    for idx, (_, _, kind) in enumerate(right, start=2):
        if kind == 'liab_total':
            cmds += [('LINEABOVE', (2, idx), (3, idx), 0.5, colors.black),
                     ('LINEBELOW', (2, idx), (3, idx), 0.5, colors.black), ('ALIGN', (2, idx), (2, idx), 'CENTER')]
        elif kind == 'equity_header':
            cmds += [('SPAN', (2, idx), (3, idx)), ('ALIGN', (2, idx), (2, idx), 'CENTER'),
                     ('LINEBELOW', (2, idx), (3, idx), 0.5, colors.black)]
        elif kind == 'equity_total':
            cmds += [('LINEABOVE', (2, idx), (3, idx), 0.5, colors.black),
                     ('LINEBELOW', (2, idx), (3, idx), 0.5, colors.black), ('ALIGN', (2, idx), (2, idx), 'CENTER')]
    third = CONTENT_W / 4
    w.table(table, [third * 1.2, third * 0.8, third * 1.2, third * 0.8], cmds, size=8.5 if w.full else 7.5)


# ---------------------------------------------------------------- P&L / SG&A
def _two_amount_table(w, rows):
    """rows: (label, inner_amount, total_amount, kind)."""
    table = [[_sp(w, '科目', 'Account'), _sp(w, '金額', 'Amount'), '']]
    for label, inner, total, _ in rows:
        table.append([w.t(label), fmt(inner), fmt(total)])
    cmds = [('ALIGN', (0, 0), (-1, 0), 'CENTER'), ('SPAN', (1, 0), (2, 0)), ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
            ('BOX', (0, 0), (-1, -1), 0.8, colors.black), ('LINEAFTER', (0, 0), (0, -1), 0.5, colors.black),
            ('LINEAFTER', (1, 1), (1, -1), 0.5, colors.black), ('LINEBELOW', (0, 0), (-1, 0), 0.5, colors.black)]
    for idx, (_, _, _, kind) in enumerate(rows, start=1):
        if kind == 'total':
            cmds.append(('LINEABOVE', (2, idx), (2, idx), 0.5, colors.black))
        elif kind == 'result':
            cmds += [('LINEABOVE', (2, idx), (2, idx), 0.5, colors.black),
                     ('LINEBELOW', (2, idx), (2, idx), 0.5, colors.black)]
    w.table(table, [CONTENT_W - 210, 105, 105], cmds, size=8.5 if w.full else 7.5)


def draw_profit_loss(w):
    pl = w.data['pl']
    w.begin_form(('損益計算書', 'Income Statement'), _period(w))
    w.company_line()
    i1, i2 = _ind(w, 2), _ind(w, 4)

    rows = [(('【売上高】', 'Net sales'), None, None, 'hdr'),
            (i1 + w.t(('売上高', 'Sales')), pl['sales'], None, 'item'),
            (i2 + _sp(w, '売上高計', 'Total net sales'), None, pl['sales'], 'total'),
            (('【売上原価】', 'Cost of sales'), None, None, 'hdr')]
    if pl['opening_inventory']:
        rows.append((i1 + w.t(('期首商品棚卸高', 'Beginning merchandise inventory')), pl['opening_inventory'], None, 'item'))
    rows.append((i1 + w.t(('当期商品仕入高', 'Merchandise purchases')), pl['purchases'], None, 'item'))
    if pl['purchase_discounts']:
        rows.append((i1 + w.t(('仕入値引高', 'Purchase discounts')), -pl['purchase_discounts'], None, 'item'))
    rows.append((i1 + w.t(('期末商品棚卸高（控除）', 'Ending merchandise inventory (deduction)')),
                 -pl['closing_inventory'], None, 'item'))
    rows += [(i2 + _sp(w, '売上原価計', 'Total cost of sales'), None, pl['cost_of_sales'], 'total'),
             (i2 * 2 + _sp(w, '売上総利益', 'Gross profit'), None, pl['gross_profit'], 'result'),
             (('【販売管理費】', 'Selling, general and administrative expenses'), None, None, 'hdr'),
             (i2 + _sp(w, '販売管理費計', 'Total SG&A expenses'), None, pl['sga_total'], 'total'),
             (i2 * 2 + _sp(w, '営業利益', 'Operating income'), None, pl['operating_income'], 'result')]
    if pl['non_op_income_items']:
        rows.append((('【営業外収益】', 'Non-operating income'), None, None, 'hdr'))
        rows += [(i1 + i['label'], i['amount'], None, 'item') for i in pl['non_op_income_items']]
        rows.append((i2 + _sp(w, '営業外収益計', 'Total non-operating income'), None, pl['non_op_income_total'], 'total'))
    if pl['non_op_expense_items']:
        rows.append((('【営業外費用】', 'Non-operating expenses'), None, None, 'hdr'))
        rows += [(i1 + i['label'], i['amount'], None, 'item') for i in pl['non_op_expense_items']]
        rows.append((i2 + _sp(w, '営業外費用計', 'Total non-operating expenses'), None, pl['non_op_expense_total'], 'total'))
    rows += [(i2 * 2 + _sp(w, '経常利益', 'Ordinary income'), None, pl['ordinary_income'], 'result'),
             (i2 * 2 + _sp(w, '税引前当期純利益', 'Income before income taxes'), None, pl['pretax_income'], 'result'),
             (('【法人税等】', 'Income taxes'), None, None, 'hdr'),
             (i1 + w.t(('法人税・住民税及び事業税', 'Corporate, inhabitant and enterprise taxes')),
              pl['income_taxes'], None, 'item')]
    if pl['prior_year_taxes']:
        rows.append((i1 + w.t(('過年度法人税等', 'Prior-year corporate taxes')), pl['prior_year_taxes'], None, 'item'))
    rows += [(i2 + _sp(w, '法人税等計', 'Total income taxes'), None, pl['taxes_total'], 'total'),
             (i2 * 2 + _sp(w, '当期純利益', 'Net income'), None, pl['net_income'], 'result')]
    _two_amount_table(w, rows)


def draw_sga(w):
    pl = w.data['pl']
    w.begin_form(('販売費及び一般管理費内訳書', 'Schedule of SG&A Expenses'), _period(w))
    w.company_line()
    indent = _ind(w, 2)
    rows = [(indent + i['label'], i['amount'], None, 'item') for i in pl['sga_items']]
    rows.append((_ind(w, 4) + _sp(w, '販売管理費計', 'Total SG&A expenses'), None, pl['sga_total'], 'total'))
    _two_amount_table(w, rows)


# ---------------------------------------------------------------- equity statement
def draw_equity(w):
    eq = w.data['equity']
    w.begin_form(('社員資本等変動計算書', "Statement of Changes in Members' Equity"), _period(w))
    w.company_line()
    t = w.t

    def row(label, capital=None, retained=None, total=None):
        return [label, fmt(capital), '', '', '', fmt(retained), fmt(total), '', fmt(total)]

    ja = w.lang == 'ja'
    sp = lambda a, b: _sp(w, a, b)
    table = [
        ['', t(('社員資本', "Members' equity")), '', '', '', '', '', t(('評価・換算\n差額等', 'Valuation &\ntranslation adj.')),
         t(('純資産合計', 'Total net assets'))],
        ['', t(('資本金', 'Capital')), t(('出資金\n申込証拠金', 'Capital\nsubscriptions')),
         t(('資本剰余金', 'Capital\nsurplus')), t(('利益剰余金', 'Retained earnings')), '', t(('計', 'Total')), '', ''],
        ['', '', '', '', t(('別途積立金', 'Reserve')), t(('繰越利益\n剰余金', 'Brought\nforward')), '', '', ''],
        row(sp('当期首残高', 'Beginning balance'), eq['opening_capital'], eq['opening_retained'], eq['opening_total']),
        row(sp('社員出資金増加', 'Capital contributions')),
        row(sp('社員出資金減少', 'Capital reductions')),
        row(sp('申込証拠金受入額', 'Subscriptions received')),
        row(sp('剰余金の配当', 'Dividends'), None, -eq['dividends'] or None, -eq['dividends'] or None),
        row(sp('当期純利益', 'Net income'), None, eq['net_income'], eq['net_income']),
        row(t(('社員資本以外(純額)', 'Non-equity items (net)'))),
        row(sp('当期変動額', 'Net change'), None, eq['change_total'], eq['change_total']),
        row(sp('当期末残高', 'Ending balance'), eq['closing_capital'], eq['closing_retained'], eq['closing_total']),
    ]
    cmds = [
        ('FONTSIZE', (0, 0), (-1, -1), 6.5), ('ALIGN', (0, 0), (-1, 2), 'CENTER'), ('ALIGN', (1, 3), (-1, -1), 'RIGHT'),
        ('SPAN', (1, 0), (6, 0)), ('SPAN', (4, 1), (5, 1)), ('SPAN', (0, 0), (0, 2)), ('SPAN', (1, 1), (1, 2)),
        ('SPAN', (2, 1), (2, 2)), ('SPAN', (3, 1), (3, 2)), ('SPAN', (6, 1), (6, 2)), ('SPAN', (7, 0), (7, 2)),
        ('SPAN', (8, 0), (8, 2)), ('GRID', (0, 0), (-1, -1), 0.5, colors.black), ('BOX', (0, 0), (-1, -1), 0.8, colors.black),
    ]
    w.table(table, [78, 50, 50, 48, 52, 52, 56, 50, CONTENT_W - 436], cmds, size=6.5)


# ---------------------------------------------------------------- notes
def draw_notes(w):
    w.begin_form(('個別注記表', 'Notes to the Financial Statements'), _period(w))
    w.lines(w.data['notes'], size=9, leading=14)


PAGES = (draw_cover, draw_balance_sheet, draw_profit_loss, draw_sga, draw_equity, draw_notes)


def render(w):
    for draw in PAGES:
        draw(w)

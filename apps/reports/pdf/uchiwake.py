"""勘定科目内訳明細書 / Account Detail Schedules attached to the corporate tax return."""
from reportlab.lib import colors

from .common import jp_name
from .layout import CONTENT_W, fmt

GRAY = (0.93, 0.93, 0.93)


def _table(w, headers, widths, aligns, rows, total_col=None, total_label=('合計', 'Total')):
    """Render one schedule table. ``rows`` are lists of plain values; amounts in ``total_col`` are summed."""
    head = [w.t(h) for h in headers]
    data = [head]
    total = 0
    for r in rows:
        line = []
        for i, v in enumerate(r):
            if isinstance(v, int) and not isinstance(v, bool):
                line.append(fmt(v))
            else:
                line.append(w.para(v, 7.5) if v else '')
        data.append(line)
        if total_col is not None:
            total += r[total_col] or 0
    if not rows:
        data.append([w.t(('該当なし', 'None'))] + [''] * (len(headers) - 1))
    elif total_col is not None:
        trow = [''] * len(headers)
        trow[0] = w.t(total_label)
        trow[total_col] = fmt(total)
        data.append(trow)
    cmds = [('GRID', (0, 0), (-1, -1), 0.5, colors.black), ('BACKGROUND', (0, 0), (-1, 0), GRAY),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER')]
    for i, a in enumerate(aligns):
        cmds.append(('ALIGN', (i, 1), (i, -1), {'l': 'LEFT', 'r': 'RIGHT', 'c': 'CENTER'}[a]))
    if rows and total_col is not None:
        cmds.append(('LINEABOVE', (0, -1), (-1, -1), 1.0, colors.black))
    w.table(data, widths, cmds, size=7.5)


def _widths(*fixed):
    """Fixed widths for all columns except the first (None), which takes the remainder."""
    rest = CONTENT_W - sum(f for f in fixed if f)
    return [rest if f is None else f for f in fixed]


def _schedule(w, title, ja_name, sections):
    """sections: [(caption or None, headers, widths, aligns, rows, total_col)]. Skipped in simple mode when empty."""
    if not w.full and not any(s[4] for s in sections):
        return
    w.begin_form(title, jp_name(ja_name), filer=True)
    for caption, headers, widths, aligns, rows, total_col in sections:
        if not w.full and not rows:
            continue
        if caption:
            w.caption(caption, size=8)
        _table(w, headers, widths, aligns, rows, total_col)


NAME_COLS = [('取引先', 'Counterparty'), ('所在地', 'Address'), ('金額(円)', 'Amount (JPY)'), ('摘要', 'Note')]
NAME_W = _widths(110, None, 90, 130)
NAME_A = ['l', 'l', 'r', 'l']


def _name_rows(items):
    return [[i['name'], i['address'], i['amount'], i['note']] for i in items]


def render(w):
    s = w.data['schedules']

    _schedule(w, ('預貯金等の内訳書', 'Schedule: Deposits and Savings'), '預貯金等の内訳書', [
        (None, [('金融機関名', 'Financial institution'), ('支店名', 'Branch'), ('種類', 'Type'), ('口座番号', 'Account no.'),
                ('期末現在高(円)', 'Year-end balance (JPY)'), ('摘要', 'Note')],
         _widths(None, 70, 50, 70, 90, 70), ['l', 'l', 'l', 'l', 'r', 'l'],
         [[d['name'], d['branch'], d['type'], d['account_no'], d['amount'], d['note']] for d in s['deposits']], 4)])

    _schedule(w, ('売掛金(未収入金)の内訳書', 'Schedule: Accounts Receivable'), '売掛金(未収入金)の内訳書', [
        (None, NAME_COLS, NAME_W, NAME_A, _name_rows(s['receivables']), 2)])

    interest = [[i['name'], i['address'], i['amount'], i['note']] for i in s['interest_income']]
    loans = [[l['name'], l['address'], l['amount'], l['rate'] or l['note']] for l in s['loans']]
    _schedule(w, ('仮払金(前渡金)の内訳書 / 貸付金及び受取利息の内訳書', 'Schedule: Advances Paid, Loans and Interest Received'),
              '仮払金(前渡金)の内訳書・貸付金及び受取利息の内訳書', [
        (('仮払金(前渡金)', 'Advances paid'), NAME_COLS, NAME_W, NAME_A, _name_rows(s['advances']), 2),
        (('貸付金', 'Loans receivable'), [('貸付先', 'Borrower'), ('所在地', 'Address'), ('期末現在高(円)', 'Balance (JPY)'),
                                          ('利率・摘要', 'Rate / note')], NAME_W, NAME_A, loans, 2),
        (('受取利息', 'Interest received'), NAME_COLS, NAME_W, NAME_A, interest, 2)])

    _schedule(w, ('棚卸資産の内訳書', 'Schedule: Inventories'), '棚卸資産(商品又は製品、半製品、仕掛品、原材料、貯蔵品)の内訳書', [
        (None, [('品名', 'Item'), ('数量', 'Quantity'), ('単価', 'Unit price'), ('金額(円)', 'Amount (JPY)'), ('摘要', 'Note')],
         _widths(None, 60, 70, 90, 100), ['l', 'r', 'r', 'r', 'l'],
         [[i['name'], i['qty'], i['unit'], i['amount'], i['note']] for i in s['inventory']], 3)])

    _schedule(w, ('有価証券・差入保証金の内訳書', 'Schedule: Securities and Guarantee Deposits'), '有価証券の内訳書', [
        (('差入保証金等', 'Guarantee deposits'), [('相手先', 'Counterparty'), ('所在地', 'Address'), ('金額(円)', 'Amount (JPY)'),
                                              ('摘要', 'Note')], NAME_W, NAME_A, _name_rows(s['guarantees']), 2)])

    _schedule(w, ('買掛金(未払金・未払費用)の内訳書', 'Schedule: Accounts Payable and Accrued Expenses'),
              '買掛金(未払金・未払費用)の内訳書', [
        (None, [('相手先', 'Payee'), ('所在地', 'Address'), ('金額(円)', 'Amount (JPY)'), ('摘要', 'Note')],
         NAME_W, NAME_A, _name_rows(s['payables']), 2)])

    wh = s['withholding']
    wh_rows = [[x['month'], x['amount']] for x in wh]
    _schedule(w, ('仮受金(前受金・預り金)の内訳書', 'Schedule: Deposits Received'), '仮受金(前受金・預り金)の内訳書', [
        (None, [('相手先', 'Payer / counterparty'), ('所在地', 'Address'), ('金額(円)', 'Amount (JPY)'), ('摘要', 'Note')],
         NAME_W, NAME_A, _name_rows(s['deposits_received']), 2),
        (('源泉所得税預り金の内訳', 'Withheld income tax by month'), [('月分', 'Month'), ('金額(円)', 'Amount (JPY)')],
         [CONTENT_W - 120, 120], ['l', 'r'], wh_rows, 1)])

    _schedule(w, ('借入金及び支払利子の内訳書', 'Schedule: Borrowings and Interest Paid'), '借入金及び支払利子の内訳書', [
        (None, [('借入先', 'Lender'), ('所在地', 'Address'), ('期末現在高(円)', 'Balance (JPY)'), ('摘要', 'Note')],
         NAME_W, NAME_A, _name_rows(s['borrowings']), 2)])

    rent = [[r['name'], r['address'], r['note'], r['amount'], r['registration']] for r in s['rent']]
    _schedule(w, ('地代家賃等の内訳書', 'Schedule: Rent and Land Lease Expenses'), '地代家賃等の内訳書(貸主の住所・氏名等)', [
        (None, [('貸主', 'Landlord'), ('所在地', 'Address'), ('用途・期間', 'Use / period'), ('支払金額(円)', 'Paid (JPY)'),
                ('登録番号', 'Registration no.')], _widths(100, None, 110, 80, 90), ['l', 'l', 'l', 'r', 'l'], rent, 3)])

    mi = [[i['name'], i['address'], i['amount'], i['note']] for i in s['misc_income']]
    ml = [[i['name'], i['address'], i['amount'], i['note']] for i in s['misc_loss']]
    _schedule(w, ('雑益、雑損失等の内訳書', 'Schedule: Miscellaneous Income and Losses'), '雑益、雑損失等の内訳書', [
        (('雑益 (雑収入)', 'Miscellaneous income'), NAME_COLS, NAME_W, NAME_A, mi, 2),
        (('雑損失', 'Miscellaneous losses'), NAME_COLS, NAME_W, NAME_A, ml, 2)])

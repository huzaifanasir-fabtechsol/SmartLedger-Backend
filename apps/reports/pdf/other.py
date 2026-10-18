"""法人事業概況説明書 / Business Overview, 納付一覧 / Payment Summary, 翌期見込 / Next-year Outlook."""
from reportlab.lib import colors

from .common import cols, jp_name
from .i18n import CATEGORY
from .layout import CONTENT_W, en_date, fmt, jp_date
from .writer import H, R, T

GRAY = (0.93, 0.93, 0.93)


def _date(w, d):
    return jp_date(d) if w.lang == 'ja' else en_date(d)


def draw_overview(w):
    d, pl, bs = w.data, w.data['pl'], w.data['bs']
    p, sched = d.get('profile'), d['schedules']
    w.begin_form(('法人事業概況説明書', 'Business Overview Statement'), jp_name('法人事業概況説明書'), filer=True)
    offices = d['local']['offices']
    w.kv_table([
        (('事業内容', 'Business'), (p.business_description if p else '') or ''),
        (('資本金', 'Capital'), fmt(d['corporate']['capital'])),
        (('従業員数 (事務所合計)', 'Employees (all offices)'), str(d['local']['total_employees'])),
        (('事務所・事業所数', 'Number of offices'), str(len(offices))),
    ])
    w.caption(('月別の売上高・仕入高', 'Monthly sales and purchases'), size=8)
    rows = [R('', m['month'].strftime('%Y-%m'), m['sales'], m['purchases'], keep=True) for m in sched['monthly']]
    rows.append(T('', ('合計', 'Total'), sum(m['sales'] for m in sched['monthly']),
                  sum(m['purchases'] for m in sched['monthly']), keep=True))
    w.lines_table(cols(2, [('売上高(円)', 'Sales (JPY)'), ('仕入高(円)', 'Purchases (JPY)')], label=('月', 'Month'),
                       no=('', ''), value_w=110), rows)
    w.paragraph(('※ 月別の金額は、受注データ(販売・仕入)の取引日による集計です。',
                 'Monthly figures are totals of Sale / Purchase orders by transaction date.'), size=7.5)
    exec_comp = sum(i['amount'] for i in pl['sga_items'] if '役員報酬' in i['label'] or 'xecutive' in i['label'])
    rows = [
        H(('当期の営業成績 (円)', 'Results for the period (JPY)')),
        R('', ('売上高', 'Sales'), pl['sales'], keep=True), R('', ('売上原価', 'Cost of sales'), pl['cost_of_sales'], keep=True),
        R('', ('売上総利益', 'Gross profit'), pl['gross_profit'], keep=True),
        R('', ('役員報酬', 'Executive compensation'), exec_comp), R('', ('販売管理費計', 'SG&A expenses'), pl['sga_total'], keep=True),
        R('', ('営業利益', 'Operating income'), pl['operating_income'], keep=True),
        R('', ('経常利益', 'Ordinary income'), pl['ordinary_income'], keep=True),
        R('', ('当期純利益', 'Net income'), pl['net_income'], keep=True),
        H(('期末の財産状況 (円)', 'Balance sheet at year end (JPY)')),
        R('', ('資産合計', 'Total assets'), bs['assets_total'], keep=True), R('', ('負債合計', 'Total liabilities'), bs['liabilities_total'], keep=True),
        R('', ('純資産合計', 'Total net assets'), bs['equity_total'], keep=True),
        R('', ('期末棚卸高', 'Ending inventory'), pl['closing_inventory']),
    ]
    w.lines_table(cols(1, label=('項目', 'Item'), no=('', '')), rows)
    w.kv_table([
        (('税理士の関与状況', 'Tax accountant'), ((p.accountant_name if p else '') or '')),
        (('事務所所在地', 'Accountant office'), ((p.accountant_address if p else '') or '')),
        (('電話番号', 'Accountant phone'), ((p.accountant_phone if p else '') or '')),
    ])


def draw_payments(w):
    d = w.data
    ct, corp, local = d['consumption'], d['corporate'], d['local']
    w.begin_form(('納付一覧表', 'Payment Summary'), jp_name('納付一覧表'), filer=True)
    due = _date(w, local['due_date'])
    pay = lambda n: max(0, n)
    refund = lambda n: max(0, -n)
    rows = [
        ('消費税及び地方消費税', 'Consumption tax and local consumption tax', ('税務署', 'Tax office'),
         pay(ct['lines'][26]), refund(ct['lines'][26])),
        ('法人税', 'Corporate tax', ('税務署', 'Tax office'), corp['corp_payable'], corp['corp_refund']),
        ('地方法人税', 'Local corporate tax', ('税務署', 'Tax office'), corp['local_payable'], 0),
    ]
    prefs, cities = {}, {}
    for o in local['offices']:
        pr = prefs.setdefault(o['prefecture'] or '-', {'office': o['prefecture_office'], 'inh': 0, 'biz': 0})
        pr['inh'] += o['pref_total']
        pr['biz'] += o['business_tax'] + o['special_tax']
        ci = cities.setdefault((o['prefecture'], o['municipality']), 0)
        cities[(o['prefecture'], o['municipality'])] = ci + o['city_total']
    for name, g in prefs.items():
        auth = g['office'] or name
        rows.append((f'{name} 道府県民税', f'{name} prefectural inhabitant tax', auth, g['inh'], 0))
        rows.append((f'{name} 事業税・特別法人事業税', f'{name} enterprise tax & special enterprise tax', auth, g['biz'], 0))
    for (pref, city), amount in cities.items():
        rows.append((f'{city or pref} 市町村民税', f'{city or pref} municipal inhabitant tax', city or pref, amount, 0))

    data = [[w.t(h) for h in (('税目', 'Tax'), ('納付先', 'Authority'), ('納付税額(円)', 'To pay (JPY)'),
                                ('還付税額(円)', 'Refund (JPY)'), ('納付期限', 'Due date'))]]
    pay_total = refund_total = 0
    for ja, en, auth, p_amt, r_amt in rows:
        if not w.full and not (p_amt or r_amt):
            continue
        data.append([w.para((ja, en), 7.5), w.para(auth, 7.5), fmt(p_amt), fmt(r_amt), due])
        pay_total += p_amt
        refund_total += r_amt
    data.append([w.t(('合計', 'Total')), '', fmt(pay_total), fmt(refund_total), ''])
    w.table(data, [CONTENT_W - 380, 100, 80, 80, 120],
            [('GRID', (0, 0), (-1, -1), 0.5, colors.black), ('BACKGROUND', (0, 0), (-1, 0), GRAY),
             ('ALIGN', (2, 1), (3, -1), 'RIGHT'), ('ALIGN', (4, 1), (4, -1), 'CENTER'),
             ('LINEABOVE', (0, -1), (-1, -1), 1.0, colors.black)], size=7.5)
    w.paragraph(('※ 納付期限は事業年度終了の日の翌日から2か月以内(土日の場合は翌月曜日)として計算しています(祝日は考慮していません)。',
                 'Due date = end of the 2nd month after year end, moved to Monday if it falls on a weekend (public holidays are not considered).'),
                size=7.5)
    notes = d['tax_notes']
    for n in notes:
        w.paragraph(n, size=7.5)


def draw_next_year(w):
    ny, d = w.data['schedules']['next_year'], w.data
    w.begin_form(('翌期概算償却額計算書', 'Estimated Depreciation for Next Fiscal Year'), jp_name('翌期概算償却額計算書'), filer=False)
    w.caption(f"{_date(w, ny['start'])} - {_date(w, ny['end'])}", size=8)
    if ny['rows']:
        data = [[w.t(h) for h in (('資産名', 'Asset'), ('種類', 'Category'), ('取得価額', 'Cost'), ('翌期首帳簿価額', 'Opening'),
                                  ('翌期概算償却額', 'Est. depreciation'), ('翌期末帳簿価額', 'Closing'))]]
        for r in ny['rows']:
            data.append([w.para(r['name'], 7), w.para(CATEGORY[r['category']], 7), fmt(r['cost']), fmt(r['opening']),
                         fmt(r['depreciation']), fmt(r['closing'])])
        data.append([w.t(('合計', 'Total')), '', fmt(sum(r['cost'] for r in ny['rows'])), fmt(sum(r['opening'] for r in ny['rows'])),
                     fmt(ny['depreciation_total']), fmt(sum(r['closing'] for r in ny['rows']))])
        w.table(data, [CONTENT_W - 5 * 70, 80 - 10, 70, 70, 70, 70],
                [('GRID', (0, 0), (-1, -1), 0.5, colors.black), ('BACKGROUND', (0, 0), (-1, 0), GRAY),
                 ('ALIGN', (2, 1), (-1, -1), 'RIGHT'), ('LINEABOVE', (0, -1), (-1, -1), 1.0, colors.black)], size=7)
    w.paragraph(('※ 定率法は償却保証額・改定償却率への切替えを考慮していません。',
                 'The declining-balance estimate does not switch to the revised rate (償却保証額).'), size=7.5)

    w.begin_form(('翌期中間申告税額の試算', 'Estimated Interim Tax Payments for Next Year'), jp_name('翌期中間申告税額の試算'), filer=False)
    iv = ny['interim']
    rows = [R('', ('法人税', 'Corporate tax'), iv['corporate'], keep=True),
            R('', ('地方法人税', 'Local corporate tax'), iv['local_corporate'], keep=True),
            R('', ('道府県民税', 'Prefectural inhabitant tax'), iv['pref'], keep=True),
            R('', ('市町村民税', 'Municipal inhabitant tax'), iv['city'], keep=True)]
    w.lines_table(cols(1, [('試算額(円)', 'Estimate (JPY)')], label=('税目', 'Tax'), no=('', '')), rows)
    if ny['interim_required']:
        w.paragraph(('当期の法人税額が20万円を超えるため、翌期は中間申告が必要です(前期実績の1/2)。',
                     'Corporate tax for this year exceeds ¥200,000, so an interim return (half of last year) is required next year.'),
                    size=8)
    else:
        w.paragraph(('当期の法人税額が20万円以下のため、翌期の中間申告税額はありません。地方税の中間申告税額も同様に0円です。',
                     'Corporate tax for this year is ¥200,000 or less, so no interim tax is due next year (local taxes likewise).'),
                    size=8)


def render(w):
    draw_overview(w)
    draw_payments(w)
    draw_next_year(w)

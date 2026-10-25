"""消費税及び地方消費税 / Consumption Tax: return, 内訳書, 付表4-(9)/(10), 課税取引金額計算表,
課税売上割合, 計算表, 還付申告に関する明細書, 委任状."""
from .common import cols, jp_name, power_of_attorney
from .layout import CONTENT_W
from .writer import H, R, T

KIND_LABELS = {
    'sales': ('課税売上げ', 'Taxable sales'),
    'nontaxable_sales': ('非課税売上げ', 'Non-taxable sales'),
    'purchase_assets': ('課税仕入れ (固定資産)', 'Taxable purchases - fixed assets'),
    'purchase_goods': ('課税仕入れ (仕入)', 'Taxable purchases - merchandise'),
    'purchase_expenses': ('課税仕入れ (経費)', 'Taxable purchases - expenses'),
    'purchase_reduced': ('課税仕入れ (軽減税率)', 'Taxable purchases - reduced rate'),
    'purchase_returns': ('課税仕入れの返還等', 'Returns / allowances on purchases'),
    'transitional': ('経過措置 80%控除対象 課税仕入れ', 'Purchases from non-registered suppliers (80% deduction)'),
    'transitional50': ('経過措置 50%控除対象 課税仕入れ', 'Purchases from non-registered suppliers (50% deduction)'),
}


def _lines(w, c):
    L = c['lines']
    return [
        H(('消費税額の計算', 'Consumption tax calculation')),
        R(1, ('課税標準額', 'Taxable base'), L[1], keep=True),
        R(2, ('消費税額', 'Consumption tax on sales (national)'), L[2], keep=True),
        R(3, ('控除過大調整税額', 'Adjustment for excess deduction'), L[3]),
        R(4, ('控除対象仕入税額', 'Deductible input tax'), L[4], keep=True),
        R(5, ('返還等対価に係る税額', 'Tax on sales returns and allowances'), L[5]),
        R(6, ('貸倒れに係る税額', 'Tax on bad debts'), L[6]),
        T(7, ('控除税額小計 (4+5+6)', 'Subtotal of deductions (4+5+6)'), L[7], keep=True),
        R(8, ('控除不足還付税額 (7-2-3)', 'Refund for excess deduction (7-2-3)'), L[8], keep=True),
        R(9, ('差引税額 (2+3-7)', 'Tax payable (2+3-7)'), L[9], keep=True),
        H(('この申告による納付税額', 'Amount payable on this return')),
        R(10, ('中間納付税額', 'Interim payment'), L[10]),
        R(11, ('納付税額 (9-10)', 'Tax to pay (9-10)'), L[11], keep=True),
        R(12, ('中間納付還付税額 (10-9)', 'Interim payment to refund (10-9)'), L[12]),
        R(13, ('既確定税額', 'Previously determined tax'), L[13]),
        R(14, ('差引納付税額', 'Net amount to pay'), L[14]),
        H(('課税売上高等', 'Sales information')),
        R(15, ('課税資産の譲渡等の対価の額', 'Consideration for taxable sales'), L[15], keep=True),
        R(16, ('資産の譲渡等の対価の額', 'Consideration for all sales'), L[16], keep=True),
        H(('地方消費税の課税標準となる消費税額', 'Consumption tax base for local consumption tax')),
        R(17, ('控除不足還付税額', 'Refund for excess deduction'), L[17], keep=True),
        R(18, ('差引税額', 'Tax payable'), L[18]),
        H(('譲渡割額', 'Local consumption tax (譲渡割額)')),
        R(19, ('還付額', 'Refund amount'), L[19], keep=True),
        R(20, ('納税額', 'Tax amount'), L[20]),
        R(21, ('中間納付譲渡割額', 'Interim payment'), L[21]),
        R(22, ('納付譲渡割額 (20-21)', 'Amount to pay (20-21)'), L[22]),
        R(23, ('中間納付還付譲渡割額 (21-20)', 'Interim payment to refund (21-20)'), L[23]),
        R(24, ('既確定譲渡割額', 'Previously determined amount'), L[24]),
        R(25, ('差引納付譲渡割額', 'Net local amount to pay'), L[25]),
        T(26, ('消費税及び地方消費税の合計(納付又は還付)税額  (11+22)-(8+12+19+23)',
               'Total consumption tax + local (payable; negative = refund)  (11+22)-(8+12+19+23)'),
          L[26], keep=True),
    ]


def draw_return(w, c):
    w.begin_form(('消費税及び地方消費税の確定申告書', 'Consumption Tax & Local Consumption Tax Return (Final)'),
                 jp_name('消費税及び地方消費税の確定申告書 (一般用)'), filer=True)
    w.lines_table(cols(), _lines(w, c))
    w.paragraph(('※ 課税期間分の申告書(本則課税)。マイナスは還付を示します。',
                 'Regular (non-simplified) taxation. A negative total means a refund is due.'), size=7.5)


def draw_breakdown(w, c):
    s, L, r = c['sales'], c['lines'], c['rate_rows']
    w.begin_form(('課税標準額等の内訳書', 'Breakdown of Taxable Base, etc.'), jp_name('課税標準額等の内訳書'), filer=True)
    T7 = r['total']
    rows = [
        H(('課税標準額', 'Taxable base')),
        R(1, ('課税標準額', 'Taxable base'), L[1], keep=True),
        H(('課税資産の譲渡等の対価の額', 'Consideration for taxable sales, by rate')),
        R(2, ('3% 適用分', '3% portion'), 0), R(3, ('4% 適用分', '4% portion'), 0), R(4, ('6.3% 適用分', '6.3% portion'), 0),
        R(5, ('6.24% 適用分 (軽減税率)', '6.24% portion (reduced)'), s['excl_8']),
        R(6, ('7.8% 適用分', '7.8% portion'), s['excl_10'], keep=True),
        T(7, ('合計', 'Total'), s['taxable_excl'], keep=True),
        H(('特定課税仕入れに係る支払対価の額', 'Reverse-charge purchases')),
        R(8, ('6.3% 適用分', '6.3% portion'), 0), R(9, ('7.8% 適用分', '7.8% portion'), 0),
        T(10, ('合計', 'Total'), 0),
        H(('消費税額', 'Consumption tax')),
        R(11, ('消費税額 (合計)', 'Consumption tax (total)'), L[2], keep=True),
        R(12, ('3% 適用分', '3% portion'), 0), R(13, ('4% 適用分', '4% portion'), 0), R(14, ('6.3% 適用分', '6.3% portion'), 0),
        R(15, ('6.24% 適用分', '6.24% portion'), r['6.24'][2]),
        R(16, ('7.8% 適用分', '7.8% portion'), r['7.8'][2], keep=True),
        H(('控除過大調整税額・返還等対価に係る税額', 'Adjustments and returns')),
        R(17, ('控除過大調整税額', 'Adjustment for excess deduction'), L[3]),
        R(18, ('返還等対価に係る税額', 'Tax on returns and allowances'), L[5]),
        R(19, ('貸倒れに係る税額', 'Tax on bad debts'), L[6]),
        H(('控除不足還付税額', 'Refund for excess deduction')),
        R(20, ('控除不足還付税額 (合計)', 'Refund (total)'), -L[8] if L[8] else 0, keep=True),
        R(21, ('4% 適用分', '4% portion'), 0), R(22, ('6.3% 適用分', '6.3% portion'), 0),
        R(23, ('6.24% ・ 7.8% 適用分', '6.24% / 7.8% portion'), -L[8] if L[8] else 0, keep=True),
    ]
    w.lines_table(cols(), rows)


def draw_appendix_9(w, c):
    r = c['rate_rows']
    w.begin_form(('付表4-(9) 税率別消費税額計算表', 'Schedule 4-(9): Consumption Tax by Rate'),
                 jp_name('付表4-(9) 税率別消費税額計算表兼地方消費税の課税標準となる消費税額計算表'), filer=True)
    names = [('1', ('課税標準額', 'Taxable base')), ('1-1', ('課税資産の譲渡等の対価の額', 'Consideration for taxable sales')),
             ('1-2', ('特定課税仕入れに係る支払対価の額', 'Reverse-charge purchases')),
             (2, ('消費税額', 'Consumption tax')), (3, ('控除過大調整税額', 'Adjustment for excess deduction')),
             (4, ('控除対象仕入税額', 'Deductible input tax')), (5, ('返還等対価に係る税額', 'Returns and allowances')),
             ('5-1', ('売上げの返還等対価に係る税額', 'Tax on sales returns')),
             ('5-2', ('特定課税仕入れの返還等対価に係る税額', 'Tax on reverse-charge returns')),
             (6, ('貸倒れに係る税額', 'Tax on bad debts')), (7, ('控除税額小計', 'Subtotal of deductions')),
             (8, ('控除不足還付税額', 'Refund for excess deduction')), (9, ('差引税額', 'Tax payable')),
             (10, ('地方消費税の課税標準: 控除不足還付税額', 'Local tax base: refund')),
             (11, ('地方消費税の課税標準: 差引税額', 'Local tax base: payable')),
             (12, ('譲渡割額 還付額', 'Local amount: refund')), (13, ('譲渡割額 納税額', 'Local amount: payable'))]
    rows = []
    for key, label in names:
        k = int(key) if str(key).isdigit() else key
        a, b, t = r['6.24'].get(k), r['7.8'].get(k), r['total'].get(k)
        if k in (8, 9, 10, 11, 12, 13):
            a = b = None
        rows.append(R(key, label, a, b, t, keep=k in (1, 2, 4, 7, 8)))
    w.lines_table(cols(3, [('6.24% (軽減)', '6.24% (reduced)'), ('7.8%', '7.8%'), ('合計', 'Total')], value_w=88), rows)


def draw_appendix_10(w, c):
    s, p, L = c['sales'], c['purchases'], c['lines']
    col8, col10 = p['cols']['6.24'], p['cols']['7.8']
    w.begin_form(('付表4-(10) 課税売上割合・控除対象仕入税額等の計算表',
                  'Schedule 4-(10): Taxable Sales Ratio and Deductible Input Tax'),
                 jp_name('付表4-(10) 税率別消費税額計算表'), filer=True)
    full = c['full_deduction']
    rows = [
        H(('課税売上割合の計算', 'Taxable sales ratio')),
        R(1, ('課税売上額 (税抜き)', 'Taxable sales (excl. tax)'), s['excl_8'], s['excl_10'], s['taxable_excl'], keep=True),
        R(2, ('免税売上額', 'Tax-exempt sales'), 0, 0, 0),
        R(3, ('非課税資産の輸出等の金額', 'Exports of non-taxable assets'), 0, 0, 0),
        T(4, ('課税資産の譲渡等の対価の額 (1+2+3)', 'Consideration for taxable sales (1+2+3)'),
          s['excl_8'], s['excl_10'], s['taxable_excl'], keep=True),
        R(5, ('課税資産の譲渡等の対価の額 (4の金額)', 'Taxable sales (amount of line 4)'), None, None, s['taxable_excl']),
        R(6, ('非課税資産の譲渡等の対価の額', 'Non-taxable sales'), None, None, s['nontaxable'], keep=True),
        R(7, ('資産の譲渡等の対価の額 (5+6)', 'Total sales (5+6)'), None, None, s['total_excl'], keep=True),
        R(8, ('課税売上割合 (4/7)', 'Taxable sales ratio (4/7)'), None, None, f"{c['ratio_pct_floor']:.2f}%", keep=True),
        H(('課税仕入れ等の税額', 'Input tax')),
        R(9, ('課税仕入れに係る支払対価の額 (税込み)', 'Consideration for taxable purchases (tax incl.)'),
          col8['purchase_incl'], col10['purchase_incl'], col8['purchase_incl'] + col10['purchase_incl'], keep=True),
        R(10, ('課税仕入れに係る消費税額', 'Consumption tax on taxable purchases'),
          col8['tax'], col10['tax'], col8['tax'] + col10['tax'], keep=True),
        R(11, ('経過措置適用の課税仕入れの支払対価の額 (税込み)', 'Purchases under 80% transitional rule (tax incl.)'),
          col8['trans_incl'], col10['trans_incl'], col8['trans_incl'] + col10['trans_incl']),
        R(12, ('経過措置適用の課税仕入れに係る消費税額 (80%)', 'Tax on transitional purchases (80%)'),
          col8['trans_tax'], col10['trans_tax'], col8['trans_tax'] + col10['trans_tax']),
        *([R('11-2', ('経過措置適用の課税仕入れの支払対価の額 (税込み・50%)', 'Purchases under 50% transitional rule (tax incl.)'),
             col8['trans50_incl'], col10['trans50_incl'], col8['trans50_incl'] + col10['trans50_incl']),
           R('12-2', ('経過措置適用の課税仕入れに係る消費税額 (50%)', 'Tax on transitional purchases (50%)'),
             col8['trans50_tax'], col10['trans50_tax'], col8['trans50_tax'] + col10['trans50_tax'])]
          if p['transitional50_10'] or p['transitional50_8'] else []),
        T(17, ('課税仕入れ等の税額の合計額', 'Total input tax'),
          col8['subtotal'], col10['subtotal'], col8['subtotal'] + col10['subtotal'], keep=True),
        R(18, ('課税売上高が5億円以下かつ課税売上割合が95%以上の場合 (17の金額)', 'Where sales ≤ ¥500m and ratio ≥ 95% (amount of 17)'),
          col8['subtotal'] if full else 0, col10['subtotal'] if full else 0, p['deductible'] if full else 0),
        T(26, ('控除対象仕入税額', 'Deductible input tax'),
          col8['deductible'], col10['deductible'], p['deductible'], keep=True),
    ]
    w.lines_table(cols(3, [('6.24% (軽減)', '6.24% (reduced)'), ('7.8%', '7.8%'), ('合計', 'Total')], value_w=88), rows)
    if not full:
        w.paragraph(('課税売上割合が95%未満のため、一括比例配分方式 (17 × 課税売上割合) で計算しています。',
                     'Ratio below 95%: deduction computed with the lump-sum proportional method (17 x ratio).'), size=7.5)


def draw_transactions(w, c):
    w.begin_form(('課税取引金額計算表', 'Taxable Transaction Summary'), jp_name('課税取引金額計算表'), filer=True)
    rows = [R(t['code'], KIND_LABELS[t['kind']], t['rate'], t['amount'], keep=t['kind'] in ('sales', 'purchase_goods'))
            for t in c['transactions']]
    w.lines_table(cols(2, [('税率', 'Rate'), ('金額 (税込・円)', 'Amount (tax incl., JPY)')],
                    label=('区分', 'Category'), no=('コード', 'Code'), value_w=95), rows)


def draw_ratio(w, c):
    s = c['sales']
    w.begin_form(('課税売上割合の計算', 'Taxable Sales Ratio Calculation'), jp_name('課税売上割合・控除対象仕入税額等の計算表'),
                 filer=True)
    cl = cols(2, [('税込み金額', 'Tax-included'), ('税抜き金額', 'Tax-excluded')], label=('項目', 'Item'), no=('', ''), value_w=110)
    rows = [
        H(('1. 課税売上割合の計算 / イ. 課税資産の譲渡等の対価の額 (分子)', '1. Ratio: (a) Consideration for taxable sales (numerator)')),
        R('[1]', ('課税売上げ 10.0%', 'Taxable sales 10.0%'), s['incl_10'], s['excl_10'], keep=True),
        R('', ('課税売上げ 軽減8.0%', 'Taxable sales reduced 8.0%'), s['incl_8'], s['excl_8']),
        T('', ('課税資産の譲渡等の対価の額 a.', 'Taxable sales  a.'), s['incl_10'] + s['incl_8'], s['taxable_excl'], keep=True),
        H(('ロ. 資産の譲渡等の対価の額 (分母)', '(b) Consideration for all sales (denominator)')),
        R('', ('課税資産の譲渡等の対価の額 a.', 'Taxable sales  a.'), None, s['taxable_excl'], keep=True),
        R('[3]', ('非課税売上げ', 'Non-taxable sales'), s['nontaxable'], s['nontaxable'], keep=True),
        T('', ('資産の譲渡等の対価の額 b.', 'Total sales  b.'), None, s['total_excl'], keep=True),
        H(('ハ. 課税売上割合', '(c) Taxable sales ratio')),
        R('', ('a ÷ b', 'a ÷ b'), None, f"{c['ratio_pct_full']:.9f} %", keep=True),
        H(('2. この課税期間の課税売上高 (税抜き)', '2. Taxable sales for the period (excl. tax)')),
        R('A', ('課税売上高', 'Taxable sales'), None, s['taxable_excl'], keep=True),
        H(('3. 課税売上高5億円超の判定', '3. Test: taxable sales above ¥500 million')),
        R('', ('A ÷ 課税期間の月数 × 12', 'A ÷ months in period × 12'), None, s['taxable_excl'], keep=True),
        R('', ('判定', 'Result'), None,
          ('5億円超 (個別対応/比例配分)' if w.lang == 'ja' else 'Over ¥500m') if c['over_500m'] else
          ('5億円以下' if w.lang == 'ja' else '≤ ¥500m'), keep=True),
    ]
    w.lines_table(cl, rows)
    w.paragraph(('注: 売上等の税抜金額は 税込金額 × 100/(100+税率) で計算しています。',
                 'Note: tax-excluded amounts are computed as tax-included amount x 100/(100 + rate).'), size=7.5)


def draw_worksheet(w, c):
    L = c['lines']
    w.begin_form(('消費税の計算表 (本則課税)', 'Consumption Tax Calculation Worksheet (Regular Taxation)'),
                 jp_name('計算表'), filer=True)
    f = lambda ja, en: (ja, en)
    rows = [
        R(1, ('課税標準額', 'Taxable base'), L[1], f('課税売上高(税抜)を千円未満切捨て', 'Taxable sales, rounded down to ¥1,000'), keep=True),
        R(2, ('消費税額', 'Consumption tax on sales'), L[2], f('(1) × 7.8% (軽減: 6.24%)', '(1) x 7.8% (reduced: 6.24%)'), keep=True),
        R(4, ('控除対象仕入税額', 'Deductible input tax'), L[4], f('付表4-(10) 26', 'Schedule 4-(10) line 26'), keep=True),
        R(7, ('控除税額小計', 'Subtotal of deductions'), L[7], f('(4)+(5)+(6)', '(4)+(5)+(6)'), keep=True),
        R(8, ('控除不足還付税額', 'Refund for excess deduction'), L[8], f('(7)-(2)-(3)', '(7)-(2)-(3)'), keep=True),
        R(9, ('差引税額', 'Tax payable'), L[9], f('(2)+(3)-(7)', '(2)+(3)-(7)'), keep=True),
        R(15, ('課税資産の譲渡等の対価の額', 'Taxable sales'), L[15], f('付表4-(10) 4', 'Schedule 4-(10) line 4'), keep=True),
        R(16, ('資産の譲渡等の対価の額', 'Total sales'), L[16], f('付表4-(10) 7', 'Schedule 4-(10) line 7'), keep=True),
        R(17, ('控除不足還付税額 (地方消費税の課税標準)', 'Refund (local tax base)'), L[17], f('(8)', '(8)'), keep=True),
        R(19, ('譲渡割額 還付額', 'Local refund'), L[19], f('(17) × 22/78', '(17) x 22/78'), keep=True),
        T(26, ('合計 (納付)又は還付税額', 'Total payable / (refund)'), L[26],
          f('(11)+(22)-((8)+(12)+(19)+(23))', '(11)+(22)-((8)+(12)+(19)+(23))'), keep=True),
    ]
    cl = [(('番号', 'No.'), 34, 'c'), (('項目', 'Item'), CONTENT_W - 34 - 110 - 190, 'l'),
          (('金額(円)', 'Amount (JPY)'), 110, 'r'), (('計算式', 'Formula'), 190, 'l')]
    # lines_table formats values as amounts; the formula column is text so pass through tr first
    rows = [r._replace(vals=(r.vals[0], w.t(r.vals[1]))) for r in rows]
    w.lines_table(cl, rows, extra_cmds=[('ALIGN', (3, 1), (3, -1), 'LEFT')])


REFUND_REASONS = [
    ('export', ('輸出取引が多い', 'High export (tax-exempt) sales')),
    ('capex', ('設備投資を行った', 'Capital investment')),
    ('purchase_heavy', ('仕入高が多い', 'High purchases')),
    ('business_start', ('事業を開始した', 'Business started')),
    ('other', ('その他', 'Other')),
]


def draw_refund_detail(w, c, sched, fy):
    if c['refund_total'] <= 0:
        return
    s, p, data = c['sales'], c['purchases'], w.data
    reasons = set(sched['refund_reasons'])
    note = data['_inputs']['tax']['consumption']['refund_note']
    if note:
        reasons.add('other')
    w.begin_form(('消費税の還付申告に関する明細書', 'Statement for Consumption Tax Refund Return'),
                 jp_name('消費税の還付申告に関する明細書'), filer=True)
    w.kv_table([(('1. 還付申告となった主な理由', '1. Main reasons for the refund'),
                 '   '.join(('[x] ' if k in reasons else '[ ] ') + w.t(lbl) for k, lbl in REFUND_REASONS))])

    w.caption(('2. 課税売上げ等に係る事項 (1) 主な課税資産の譲渡等 (100万円以上)',
               '2. Taxable sales - (1) Main sales (¥1,000,000 or more, up to 10)'), size=8)
    sales_rows = [R(i + 1, (o['name'] or '-'), o['date'].strftime('%Y-%m-%d'), o['amount'], keep=True)
                  for i, o in enumerate(sched['top_sales'])] or [R('', ('該当なし', 'None'), '', None, keep=True)]
    w.lines_table(cols(2, [('譲渡年月日', 'Date'), ('取引金額(円)', 'Amount (JPY)')], label=('取引先', 'Counterparty'),
                       value_w=100), sales_rows)
    w.caption(('(2) 主な輸出取引等: なし', '(2) Main export transactions: none'), size=8)

    w.caption(('3. 課税仕入れに係る事項 (1) 仕入金額等の明細 (千円)', '3. Taxable purchases - (1) Purchase detail (thousand yen)'), size=8)
    t = {x['kind']: x['amount'] for x in c['transactions'] if x['rate'] == '10.0%'}
    k = lambda n: round(n / 1000)
    ret = p['returns_10']
    rows = [
        H(('課税仕入れ 10%', 'Taxable purchases 10%')),
        R('', ('棚卸資産(商品)', 'Inventory (merchandise)'), k(t.get('purchase_goods', 0)), 0, k(t.get('purchase_goods', 0)), keep=True),
        R('', ('固定資産等', 'Fixed assets'), k(t.get('purchase_assets', 0)), 0, k(t.get('purchase_assets', 0)), keep=True),
        R('', ('経費等', 'Expenses'), k(t.get('purchase_expenses', 0)), k(ret), k(t.get('purchase_expenses', 0) - ret), keep=True),
        H(('課税仕入れ 軽減8%', 'Taxable purchases 8% (reduced)')),
        R('', ('合計', 'Total'), k(p['incl_8']), k(p['returns_8']), k(p['incl_8'] - p['returns_8']), keep=True),
    ]
    w.lines_table(cols(3, [('支払対価', 'Paid'), ('うち返還等', 'Returned'), ('差引', 'Net')], label=('区分', 'Category'),
                       no=('', ''), value_w=80), rows)

    w.caption(('(2) 主な棚卸資産・原材料等の取得 (100万円以上、上位5件)', '(2) Main inventory / material purchases (¥1,000,000+, top 5)'), size=8)
    prows = [R(i + 1, (o['name'] or '-'), o['date'].strftime('%Y-%m-%d'), o['amount'], keep=True)
             for i, o in enumerate(sched['top_purchases'])] or [R('', ('該当なし', 'None'), '', None, keep=True)]
    w.lines_table(cols(2, [('取得年月日', 'Date'), ('取引金額(円)', 'Amount (JPY)')], label=('取引先', 'Counterparty'),
                       value_w=100), prows)

    w.caption(('(3) 主な固定資産等の取得 (100万円以上)', '(3) Main fixed asset acquisitions (¥1,000,000+)'), size=8)
    assets = [r for r in sched['depreciation']['rows'] if r['cost'] >= 1_000_000 and r['acquired_on'] >= fy.start_date]
    arows = [R(i + 1, a['name'], a['acquired_on'].strftime('%Y-%m-%d'), a['cost'], keep=True)
             for i, a in enumerate(assets)] or [R('', ('該当なし', 'None'), '', None, keep=True)]
    w.lines_table(cols(2, [('取得年月日', 'Date'), ('取得価額(円)', 'Cost (JPY)')], label=('資産', 'Asset'), value_w=100), arows)

    w.kv_table([(('4. 当課税期間中の特殊事情', '4. Special circumstances in the period'), note or '')])


def render(w):
    c, sched, fy = w.data['consumption'], w.data['schedules'], w.data['_fy']
    draw_return(w, c)
    draw_breakdown(w, c)
    draw_appendix_9(w, c)
    draw_appendix_10(w, c)
    draw_transactions(w, c)
    draw_ratio(w, c)
    draw_worksheet(w, c)
    draw_refund_detail(w, c, sched, fy)
    if w.full:
        power_of_attorney(w, ('消費税及び地方消費税の確定申告書の作成・提出に関する一切の件',
                              'Preparation and filing of the final consumption tax and local consumption tax return'),
                          ('税務署', 'District tax office'))

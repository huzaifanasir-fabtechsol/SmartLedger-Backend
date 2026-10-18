"""法人税・地方法人税 / Corporate Tax: 別表一(+次葉), 二, 四, 五(一), 五(二), 六(一), 七, 十五,
十六(一)(二)(六), 委任状.

Line captions follow the official forms as closely as the filed sample allows; lines the app does not
calculate are omitted rather than shown blank. Verify against the current official forms before use.
"""
from reportlab.lib import colors

from .common import cols, jp_name, power_of_attorney
from .i18n import CATEGORY, METHOD
from .layout import CONTENT_W
from .writer import H, R, T


def _chunk(items, n):
    return [items[i:i + n] for i in range(0, len(items), n)]


# ---------------------------------------------------------------- 別表一
def draw_form1(w, c):
    w.begin_form(('別表一  各事業年度の所得に係る申告書', 'Schedule 1: Corporate Tax Return'),
                 jp_name('別表一 各事業年度の所得に係る申告書 ― 内国法人の分'), filer=True)
    f7 = c['form7']
    rows = [
        H(('法人税額の計算', 'Corporate tax calculation')),
        R(1, ('所得金額又は欠損金額 (別表四 52)', 'Taxable income or loss (Schedule 4, line 52)'), c['income'], keep=True),
        R(2, ('法人税額', 'Corporate tax'), c['corp_tax'], keep=True),
        R(3, ('法人税額の特別控除額', 'Special tax credits'), 0),
        T(9, ('法人税額計', 'Total corporate tax'), c['corp_tax'], keep=True),
        R(10, ('所得税額等の控除額 (別表六(一))', 'Withholding tax credit (Schedule 6-(1))'), c['corp_credit']),
        T(12, ('差引所得に対する法人税額 (9-10)', 'Corporate tax after credits (9-10)'), c['corp_net'], keep=True),
        T(15, ('差引確定法人税額', 'Determined corporate tax'), c['corp_net'], keep=True),
        R('', ('中間申告分の法人税額', 'Interim corporate tax paid'), c['corp_interim']),
        R('', ('この申告により納付すべき法人税額', 'Corporate tax payable on this return'), c['corp_payable'], keep=True),
        R('', ('この申告による還付金額', 'Refund on this return'), c['corp_refund']),
        H(('欠損金', 'Loss carry-forward')),
        R(26, ('欠損金等の当期控除額 (別表七(一))', 'Loss deducted this year (Schedule 7-(1))'), f7['used_total']),
        R(27, ('翌期へ繰り越す欠損金又は災害損失金', 'Loss carried forward to next year'), f7['carry_total'], keep=True),
        H(('地方法人税額の計算', 'Local corporate tax calculation')),
        R(28, ('課税標準法人税額', 'Taxable base (corporate tax)'), c['local_base'], keep=True),
        R(29, ('地方法人税額 (28 × 10.3%)', 'Local corporate tax (28 x 10.3%)'), c['local_tax'], keep=True),
        T(34, ('差引地方法人税額', 'Local corporate tax after credits'), c['local_tax'], keep=True),
        R(35, ('中間申告分の地方法人税額', 'Interim local corporate tax paid'), 0),
        T(37, ('この申告により納付すべき地方法人税額', 'Local corporate tax payable'), c['local_payable'], keep=True),
    ]
    w.lines_table(cols(), rows)


def draw_form1_detail(w, c):
    sp = c['form1_split']
    w.begin_form(('別表一 次葉', 'Schedule 1 (continued)'), jp_name('別表一 次葉'), filer=True)
    rows = [
        R(45, ('所得金額のうち年800万円以下の金額', 'Income up to ¥8 million'), sp['low'], keep=True),
        R(46, ('所得金額のうち年800万円を超える金額', 'Income above ¥8 million'), sp['high'], keep=True),
        R(47, ('課税所得金額 (千円未満切捨て)', 'Taxable income (rounded down to ¥1,000)'), c['taxable_income'], keep=True),
        R(48, ('(45) × 15%', '(45) x 15%'), sp['low'] * 15 // 100),
        R(49, ('(46) × 23.2%', '(46) x 23.2%'), sp['high'] * 232 // 1000),
        T(50, ('法人税額 (百円未満切捨て)', 'Corporate tax (rounded down to ¥100)'), c['corp_tax'], keep=True),
        R(51, ('課税標準法人税額', 'Taxable base for local corporate tax'), c['local_base'], keep=True),
        R(53, ('地方法人税額 (51 × 10.3%)', 'Local corporate tax (51 x 10.3%)'), c['local_tax'], keep=True),
    ]
    w.lines_table(cols(), rows)


# ---------------------------------------------------------------- 別表二
def draw_form2(w, c):
    f = c['form2']
    w.begin_form(('別表二  同族会社等の判定に関する明細書', 'Schedule 2: Family-Company Determination'),
                 jp_name('別表二 同族会社等の判定に関する明細書'), filer=True)
    pct = lambda v: f'{v:.1f}%' if v else ''
    rows = [
        H(('判定基準となる株主等の株式数等の明細', 'Basis for the determination')),
        R(1, ('発行済株式の総数又は出資金額', 'Total shares / capital contributions'), f['total_shares'], keep=True),
        R(2, ('上位3順位の株主グループの株式数', 'Shares held by top 3 shareholder groups'), f['top3_shares'], keep=True),
        R(3, ('株式数による判定 (2)/(1)', 'Ratio by shares (2)/(1)'), pct(f['top3_shares'] * 100 / f['total_shares'] if f['total_shares'] else 0), keep=True),
        R(7, ('株主等の総数', 'Total number of shareholders'), f['members_total'], keep=True),
        R(8, ('上位3順位の株主グループの人数', 'Shareholders in top 3 groups'), f['members_top3'], keep=True),
        R(9, ('株主数による判定 (8)/(7)', 'Ratio by headcount (8)/(7)'), pct(f['members_ratio']), keep=True),
        T(10, ('(3)、(6)、(9)のうち最も大きい数', 'Largest of (3), (6), (9)'), pct(f['judgement_ratio']), keep=True),
        R(18, ('同族会社の判定', 'Family company?'),
          (('同族会社' if f['is_family'] else '非同族会社') if w.lang == 'ja' else
           ('Family company' if f['is_family'] else 'Non-family company')) if f['ranked'] else
          ('未登録' if w.lang == 'ja' else 'No shareholders registered'), keep=True),
    ]
    w.lines_table(cols(), rows)
    if f['ranked']:
        w.caption(('株主グループ (株式数順)', 'Shareholder groups (by shares)'), size=8)
        data = [[w.t(h) for h in (('順位', 'Rank'), ('氏名', 'Name'), ('住所', 'Address'), ('続柄', 'Relation'),
                                  ('株式数', 'Shares'), ('割合', 'Share'))]]
        for i, g in enumerate(f['ranked'], 1):
            share = g['shares'] * 100 / f['total_shares'] if f['total_shares'] else 0
            data.append([str(i), w.para(g['name'], 7.5), w.para(g['address'], 7.5), g['relationship'],
                         f"{g['shares']:,}", f'{share:.1f}%'])
        w.table(data, [32, 110, CONTENT_W - 32 - 110 - 60 - 80 - 52, 60, 80, 52],
                [('GRID', (0, 0), (-1, -1), 0.5, colors.black), ('BACKGROUND', (0, 0), (-1, 0), (0.93, 0.93, 0.93)),
                 ('ALIGN', (4, 1), (-1, -1), 'RIGHT')], size=7.5)


# ---------------------------------------------------------------- 別表四
def draw_form4(w, c):
    f = c['form4']
    w.begin_form(('別表四  所得の金額の計算に関する明細書', 'Schedule 4: Calculation of Taxable Income'),
                 jp_name('別表四 所得の金額の計算に関する明細書'), filer=True)
    ent, ni = f['entertainment_excess'], f['net_income']
    ret_add = f['taxes_booked'] + f['other_add']
    retained_23 = ni + ret_add - f['other_ded']
    retained_loss = retained_23 - f['loss_used']
    rows = [
        R(1, ('当期利益又は当期欠損の額', 'Net income or loss for the period'), ni, ni, 0, keep=True),
        H(('加算', 'Additions')),
        R(4, ('損金経理をした納税充当金', 'Provision for taxes booked as expense'), f['taxes_booked'], f['taxes_booked'], 0),
        R(8, ('交際費等の損金不算入額 (別表十五)', 'Non-deductible entertainment (Schedule 15)'), ent, 0, ent),
        R(10, ('その他の加算', 'Other additions'), f['other_add'], f['other_add'], 0),
        T(11, ('小計', 'Subtotal'), f['add_total'], ret_add, ent, keep=True),
        H(('減算', 'Deductions')),
        R(21, ('その他の減算', 'Other deductions'), f['other_ded'], f['other_ded'], 0),
        T(22, ('小計', 'Subtotal'), f['other_ded'], f['other_ded'], 0, keep=True),
        T(23, ('仮計 (1+11-22)', 'Provisional total (1+11-22)'), f['provisional'], retained_23, ent, keep=True),
        R(25, ('法人税額から控除される所得税額', 'Withholding tax credited against corporate tax'), f['withholding'], 0, f['withholding']),
        T(26, ('仮計 (23+24+25)', 'Provisional total (23+24+25)'), f['income_pre'], retained_23, ent + f['withholding'], keep=True),
        T(34, ('合計', 'Total'), f['income_pre'], retained_23, ent + f['withholding'], keep=True),
        R(38, ('欠損金又は災害損失金等の当期控除額 (別表七(一))', 'Loss carry-forward deducted (Schedule 7-(1))'),
          -f['loss_used'], -f['loss_used'], 0),
        T(39, ('差引計 (34-38)', 'Balance (34-38)'), f['income'], retained_loss, ent + f['withholding'], keep=True),
        T(43, ('総計', 'Grand total'), f['income'], retained_loss, ent + f['withholding'], keep=True),
        T(45, ('差引計', 'Balance'), f['income'], retained_loss, ent + f['withholding'], keep=True),
        T(52, ('所得金額又は欠損金額', 'Taxable income or loss'), f['income'], retained_loss, ent + f['withholding'], keep=True),
    ]
    heads = [('総額', 'Total'), ('留保', 'Retained'), ('社外流出', 'Outflow')]
    w.lines_table(cols(3, heads, value_w=88), rows)
    w.paragraph(('※ 欠損の場合、52はマイナス(欠損金額)で表示しています。',
                 'A negative line 52 is a tax loss (欠損金額).'), size=7.5)


# ---------------------------------------------------------------- 別表五
def draw_form5_1(w, c):
    f = c['form5_1']
    w.begin_form(('別表五(一)  利益積立金額及び資本金等の額の計算に関する明細書',
                  'Schedule 5-(1): Retained Earnings and Capital Reserves'),
                 jp_name('別表五(一) 利益積立金額及び資本金等の額の計算に関する明細書'), filer=True)
    rows = [H(('Ⅰ 利益積立金額の計算', 'I. Retained earnings'))]
    for code, label, opening, decrease, increase, closing in f['rows']:
        rows.append(R(code, label, opening, decrease, increase, closing, keep=True))
    rows.append(T(31, ('差引合計額', 'Total'), f['opening_total'], f['decrease_total'], f['increase_total'], f['closing_total'], keep=True))
    cap = c['capital']
    rows += [H(('Ⅱ 資本金等の額の計算', 'II. Capital')),
             R(32, ('資本金又は出資金', 'Capital'), cap, 0, 0, cap, keep=True),
             T(36, ('差引合計額', 'Total'), cap, 0, 0, cap, keep=True)]
    heads = [('期首現在', 'Beginning'), ('減', 'Decrease'), ('増', 'Increase'), ('期末現在', 'Ending')]
    w.lines_table(cols(4, heads, label=('区分', 'Item'), value_w=76), rows)
    if f['difference']:
        w.paragraph((f"注意: 差引合計額と繰越利益剰余金に {f['difference']:,} 円の差があります。未納税額を確認してください。",
                     f"Note: the total differs from retained earnings by JPY {f['difference']:,}. Check the unpaid-tax inputs."),
                    size=7.5)


def draw_form5_2(w, c):
    f = c['form5_2']
    w.begin_form(('別表五(二)  租税公課の納付状況等に関する明細書', 'Schedule 5-(2): Payment Status of Taxes'),
                 jp_name('別表五(二) 租税公課の納付状況等に関する明細書'), filer=True)
    rows = [R(code, label, opening, accrued, paid, closing, keep=True) for code, label, opening, accrued, paid, closing in f['rows']]
    heads = [('期首未納税額', 'Unpaid at start'), ('当期発生税額', 'Accrued'), ('当期納付額', 'Paid'), ('期末未納税額', 'Unpaid at end')]
    w.lines_table(cols(4, heads, label=('税目', 'Tax'), value_w=76), rows)
    p = f['provision']
    prows = [
        H(('納税充当金の計算', 'Provision for taxes')),
        R(30, ('期首納税充当金', 'Beginning balance'), p[30], keep=True),
        R(31, ('損金経理による繰入額', 'Additions booked as expense'), p[31], keep=True),
        T(33, ('計 (30+31+32)', 'Total (30+31+32)'), p[33], keep=True),
        R(34, ('法人税等の納付等による取崩額', 'Used for tax payments / reversed'), p[34], keep=True),
        T(40, ('取崩額計', 'Total used'), p[40], keep=True),
        T(41, ('期末納税充当金 (33-40)', 'Ending balance (33-40)'), p[41], keep=True),
    ]
    w.lines_table(cols(), prows)


def draw_form6(w, c):
    f = c['form6']
    w.begin_form(('別表六(一)  所得税額の控除に関する明細書', 'Schedule 6-(1): Withholding Tax Credit'),
                 jp_name('別表六(一) 所得税額の控除に関する明細書'), filer=True)
    rows = [R(1, ('公社債及び預貯金の利子、合同運用信託・公社債投資信託の収益の分配', 'Interest on bonds and deposits'),
              f['interest_income'], f['withholding'], f['credit'], keep=True),
            T(6, ('計', 'Total'), f['interest_income'], f['withholding'], f['credit'], keep=True)]
    heads = [('収入金額', 'Gross income'), ('所得税額', 'Tax withheld'), ('控除を受ける所得税額', 'Credit claimed')]
    w.lines_table(cols(3, heads, label=('区分', 'Type'), value_w=88), rows)


def draw_form7(w, c):
    f = c['form7']
    w.begin_form(('別表七(一)  欠損金の損金算入等に関する明細書', 'Schedule 7-(1): Loss Carry-forward'),
                 jp_name('別表七(一) 欠損金の損金算入等に関する明細書'), filer=True)
    rows = [H(('控除未済欠損金額', 'Unused prior-year losses'))]
    for r in f['rows']:
        rows.append(R('', r['label'], r['amount'], r['used'], r['carry'], keep=True))
    rows.append(T('', ('計', 'Total'), f['prior_total'], f['used_total'], f['prior_carry_total'], keep=True))
    rows += [R(6, ('当期欠損金額 (別表四 52)', 'Current-year loss (Schedule 4, line 52)'), f['current_loss'], None, f['current_loss'], keep=True),
             T('', ('欠損金額の合計', 'Total losses'), f['prior_total'] + f['current_loss'], f['used_total'], f['carry_total'], keep=True),
             R('', ('控除前の所得金額 (別表四 34)', 'Income before loss deduction (Schedule 4, line 34)'), f['income_for_limit'])]
    heads = [('控除未済欠損金額', 'Unused loss'), ('当期控除額', 'Deducted'), ('翌期繰越額', 'Carried forward')]
    w.lines_table(cols(3, heads, label=('事業年度', 'Fiscal year'), no=('', ''), value_w=92), rows)


def draw_form15(w, c):
    f = c['form15']
    w.begin_form(('別表十五  交際費等の損金算入に関する明細書', 'Schedule 15: Entertainment Expenses'),
                 jp_name('別表十五 交際費等の損金算入に関する明細書'), filer=True)
    rows = [
        R(1, ('支出交際費等の額 (8の計)', 'Entertainment expenses paid (total of 8)'), f[1], keep=True),
        R(2, ('接待飲食費の額の50%相当額', '50% of business-meal entertainment'), f[2], keep=True),
        R(3, (f"定額控除限度額 (800万円 × {f['months']}/12) と (1) の少ない金額",
              f"Lesser of (1) and fixed allowance (¥8m x {f['months']}/12)"), f[3], keep=True),
        R(4, ('損金算入限度額 (2と3のいずれか多い金額)', 'Deductible limit (greater of 2 and 3)'), f[4], keep=True),
        T(5, ('損金不算入額 (1-4)', 'Non-deductible amount (1-4)'), f[5], keep=True),
    ]
    w.lines_table(cols(), rows)
    w.caption(('支出交際費等の額の明細', 'Detail of entertainment expenses'), size=8)
    drows = [R('', ('交際費', 'Entertainment'), f[1], 0, f[1], f['food_half'] * 2, keep=True)]
    heads = [('支出額', 'Paid'), ('控除額', 'Excluded'), ('差引交際費等の額', 'Net'), ('うち接待飲食費', 'Meals')]
    w.lines_table(cols(4, heads, label=('科目', 'Account'), no=('', ''), value_w=76), drows)


# ---------------------------------------------------------------- 別表十六
def _group_header(w, category, method, lives):
    cat, met = w.t(CATEGORY[category]), w.t(METHOD[method])
    life = '/'.join(str(x) for x in sorted(lives) if x)
    return f"{cat}\n{met}" + (f"\n{life}" + ('年' if w.lang == 'ja' else ' yrs') if life else '')


def _depreciation_form(w, groups, method, title, ja_name, rows_fn):
    items = [(k, g) for k, g in groups.items() if k[1] == method and k[0] != 'deferred']
    for part in _chunk(items, 4):
        w.begin_form(title, jp_name(ja_name), filer=True)
        heads = [(_group_header(w, k[0], k[1], g['lives']),) * 2 for k, g in part]
        rows = rows_fn([g for _, g in part])
        w.lines_table(cols(len(part), heads, label=('項目', 'Item'), value_w=min(100, int((CONTENT_W - 200) / len(part)))), rows)


def _rate(g):
    rates = {r for r in g['rates'] if r}
    return f'{next(iter(rates)):g}' if len(rates) == 1 else ('-' if not rates else 'various')


def _rows_straight(groups):
    v = lambda fn: [fn(g) for g in groups]
    return [
        R(7, ('期末現在の取得価額', 'Acquisition cost at year end'), *v(lambda g: g['cost']), keep=True),
        R(8, ('期末現在の積立金計上額', 'Reserve (compressed-entry) amount'), *v(lambda g: 0)),
        R(9, ('差引取得価額 (7-8)', 'Net acquisition cost (7-8)'), *v(lambda g: g['cost']), keep=True),
        R(10, ('期末現在の帳簿記載金額', 'Book value at year end'), *v(lambda g: g['closing']), keep=True),
        T(13, ('計', 'Total'), *v(lambda g: g['closing']), keep=True),
        R(14, ('当期償却額', 'Depreciation booked this year'), *v(lambda g: g['depreciation']), keep=True),
        T(16, ('差引帳簿記載金額 (13+14+15)', 'Book value before depreciation (13+14+15)'),
          *v(lambda g: g['closing'] + g['depreciation']), keep=True),
        R(25, ('取得価額 (9)', 'Acquisition cost (9)'), *v(lambda g: g['cost'])),
        R(26, ('償却率', 'Depreciation rate'), *v(_rate)),
        R(27, ('算出償却額 (月割計算後)', 'Calculated depreciation (prorated)'), *v(lambda g: g['depreciation'])),
        T(30, ('当期分の普通償却限度額等', 'Ordinary depreciation limit for the year'), *v(lambda g: g['depreciation']), keep=True),
        T(34, ('償却限度額合計', 'Total depreciation limit'), *v(lambda g: g['depreciation']), keep=True),
        R(35, ('当期償却額', 'Depreciation booked'), *v(lambda g: g['depreciation']), keep=True),
        R(36, ('償却超過額', 'Excess depreciation'), *v(lambda g: 0)),
        R(37, ('償却不足額', 'Shortfall'), *v(lambda g: 0)),
    ]


def _rows_declining(groups):
    v = lambda fn: [fn(g) for g in groups]
    return [
        R(7, ('期末現在の取得価額', 'Acquisition cost at year end'), *v(lambda g: g['cost']), keep=True),
        R(8, ('期末現在の積立金計上額', 'Reserve (compressed-entry) amount'), *v(lambda g: 0)),
        R(9, ('差引取得価額 (7-8)', 'Net acquisition cost (7-8)'), *v(lambda g: g['cost']), keep=True),
        R(10, ('期末現在の帳簿記載金額', 'Book value at year end'), *v(lambda g: g['closing']), keep=True),
        T(13, ('計', 'Total'), *v(lambda g: g['closing']), keep=True),
        R(14, ('当期償却額', 'Depreciation booked this year'), *v(lambda g: g['depreciation']), keep=True),
        T(16, ('差引帳簿記載金額 (13+14+15)', 'Book value before depreciation (13+14+15)'),
          *v(lambda g: g['closing'] + g['depreciation']), keep=True),
        R(18, ('期首帳簿記載金額 + 当期取得価額', 'Opening book value + additions'), *v(lambda g: g['opening']), keep=True),
        R(25, ('償却率', 'Depreciation rate'), *v(_rate)),
        R(26, ('算出償却額 (月割計算後)', 'Calculated depreciation (prorated)'), *v(lambda g: g['depreciation'])),
        T(34, ('当期分の普通償却限度額等', 'Ordinary depreciation limit for the year'), *v(lambda g: g['depreciation']), keep=True),
        T(38, ('償却限度額合計', 'Total depreciation limit'), *v(lambda g: g['depreciation']), keep=True),
        R(39, ('当期償却額', 'Depreciation booked'), *v(lambda g: g['depreciation']), keep=True),
        R(40, ('償却超過額', 'Excess depreciation'), *v(lambda g: 0)),
        R(41, ('償却不足額', 'Shortfall'), *v(lambda g: 0)),
    ]


def draw_form16_deferred(w, rows):
    deferred = [r for r in rows if r['category'] == 'deferred']
    for part in _chunk(deferred, 4):
        w.begin_form(('別表十六(六)  繰延資産の償却額の計算に関する明細書', 'Schedule 16-(6): Deferred Asset Amortization'),
                     jp_name('別表十六(六) 繰延資産の償却額の計算に関する明細書'), filer=True)
        v = lambda fn: [fn(r) for r in part]
        heads = [(r['name'], r['name']) for r in part]
        lines = [
            R(1, ('繰延資産の種類', 'Type of deferred asset'), *v(lambda r: r['name']), keep=True),
            R(2, ('支出年月日', 'Date incurred'), *v(lambda r: r['acquired_on'].strftime('%Y-%m-%d')), keep=True),
            R(3, ('支出した金額', 'Amount incurred'), *v(lambda r: r['cost']), keep=True),
            R(8, ('期首帳簿記載金額', 'Opening book value'), *v(lambda r: r['opening']), keep=True),
            R(11, ('当期償却額', 'Amortization booked'), *v(lambda r: r['depreciation']), keep=True),
            T(24, ('期末帳簿記載金額', 'Closing book value'), *v(lambda r: r['closing']), keep=True),
            R(26, ('償却累計額', 'Accumulated amortization'), *v(lambda r: r['accumulated'])),
        ]
        w.lines_table(cols(len(part), heads, label=('項目', 'Item'), value_w=min(110, int((CONTENT_W - 200) / len(part)))), lines)


def draw_form16(w, c, sched):
    dep = sched['depreciation']
    if not dep['rows']:
        return
    _depreciation_form(w, dep['groups'], 'straight_line',
                       ('別表十六(一)  定額法による減価償却資産の償却額の計算に関する明細書',
                        'Schedule 16-(1): Straight-line Depreciation'),
                       '別表十六(一) 旧定額法又は定額法による減価償却資産の償却額の計算に関する明細書', _rows_straight)
    _depreciation_form(w, dep['groups'], 'declining_200',
                       ('別表十六(二)  定率法による減価償却資産の償却額の計算に関する明細書',
                        'Schedule 16-(2): Declining-balance Depreciation'),
                       '別表十六(二) 旧定率法又は定率法による減価償却資産の償却額の計算に関する明細書', _rows_declining)
    draw_form16_deferred(w, dep['rows'])


def render(w):
    c, sched = w.data['corporate'], w.data['schedules']
    draw_form1(w, c)
    draw_form1_detail(w, c)
    draw_form2(w, c)
    draw_form4(w, c)
    draw_form5_1(w, c)
    draw_form5_2(w, c)
    draw_form6(w, c)
    draw_form7(w, c)
    draw_form15(w, c)
    draw_form16(w, c, sched)
    if w.full:
        power_of_attorney(w, ('法人税及び地方法人税の確定申告書の作成・提出に関する一切の件',
                              'Preparation and filing of the final corporate tax and local corporate tax return'),
                          ('税務署', 'District tax office'))

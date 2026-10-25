"""消費税及び地方消費税 (consumption tax) — 本則課税, final return.

Rates: standard 10% = 7.8% national + 2.2% local; reduced 8% = 6.24% national + 1.76% local.
Local consumption tax = national tax x 22/78.  Integer arithmetic throughout (floor division),
matching how the statutory forms round.

Scope/assumptions (also shown to the user):
- 一括比例配分方式 is used when the taxable-sales ratio is under 95% (or sales exceed ¥500m).
- 経過措置 (purchases from non-registered suppliers): 80% deduction up to 2026-09-30 (``transitional_incl_*``),
  50% from 2026-10-01 (``transitional50_incl_*``); a year that spans 2026-10-01 uses both.
- Sales and purchase totals are derived from app data unless overridden in ``tax.consumption``.
"""
from decimal import Decimal

from apps.expense.models import Expense

from .depreciation import TANGIBLE

LOCAL_NUM, LOCAL_DEN = 22, 78


def _expense_incl(user, fy):
    """Tax-included totals of expenses that carry consumption tax, by rate bucket."""
    buckets = {'10': 0, '8': 0}
    for exp in Expense.objects.filter(user=user, date__range=(fy.start_date, fy.end_date)):
        amount, tax = exp.amount or Decimal(0), exp.tax_amount or Decimal(0)
        if tax <= 0 or amount <= 0:
            continue
        rate = exp.tax_percent_used or (tax / amount * 100)
        if rate >= 9:
            buckets['10'] += int(round(amount + tax))
        elif rate >= 7:
            buckets['8'] += int(round(amount + tax))
    return buckets['10'], buckets['8']


def compute(user, fy, data):
    inputs, pl = data['_inputs'], data['pl']
    c = inputs['tax']['consumption']
    sources, warnings = {}, []

    def pick(key, derive):
        if c[key] is not None:
            sources[key] = 'input'
            return c[key]
        sources[key] = 'derived'
        return derive()

    # ---- Sales ------------------------------------------------------------------------
    sales_incl_10 = pick('sales_incl_10', lambda: int(round(pl['sales'] * 1.10)))
    sales_incl_8 = pick('sales_incl_8', lambda: 0)
    nontaxable = pick('nontaxable_sales', lambda: sum(
        i['amount'] for i in pl['non_op_income_items'] if '利息' in i['label'] or 'interest' in i['label'].lower()))

    excl_10 = sales_incl_10 * 100 // 110
    excl_8 = sales_incl_8 * 100 // 108
    taxable_excl = excl_10 + excl_8
    base_10, base_8 = excl_10 // 1000 * 1000, excl_8 // 1000 * 1000     # 課税標準額 (per rate, ¥1,000 floor)
    base = base_10 + base_8
    sales_tax_10 = base_10 * 78 // 1000        # 7.8%
    sales_tax_8 = base_8 * 624 // 10000        # 6.24%
    sales_tax = sales_tax_10 + sales_tax_8

    total_excl = taxable_excl + nontaxable
    ratio = (taxable_excl / total_excl) if total_excl else 1.0
    ratio_pct_floor = int(ratio * 10000) / 100          # 99.99 style (付表4-(10))
    full_deduction = ratio >= 0.95 and taxable_excl <= 500_000_000

    # ---- Purchases --------------------------------------------------------------------
    exp10, exp8 = _expense_incl(user, fy)
    assets10 = int(round(sum(r['asset'].cost for r in data['_dep_rows']
                             if r['asset'].category in TANGIBLE and r['asset'].acquired_on >= fy.start_date) * 1.10))
    goods10 = int(round(pl['purchases'] * 1.10))
    p10 = pick('purchase_incl_10', lambda: exp10 + goods10 + assets10)
    p8 = pick('purchase_incl_8', lambda: exp8)
    ret10, ret8 = c['purchase_returns_10'], c['purchase_returns_8']
    tr10, tr8 = c['transitional_incl_10'], c['transitional_incl_8']
    tr50_10, tr50_8 = c['transitional50_incl_10'], c['transitional50_incl_8']

    net10, net8 = max(0, p10 - ret10), max(0, p8 - ret8)
    tax_p10 = net10 * 78 // 1100               # 7.8/110
    tax_p8 = net8 * 624 // 10800               # 6.24/108
    trans_tax_10 = tr10 * 624 // 11000         # 7.8/110 x 80%
    trans_tax_8 = tr8 * 4992 // 108000         # 6.24/108 x 80%
    trans50_tax_10 = tr50_10 * 390 // 11000    # 7.8/110 x 50%
    trans50_tax_8 = tr50_8 * 3120 // 108000    # 6.24/108 x 50%

    def apply_ratio(amount):
        return amount if full_deduction else int(amount * ratio)

    col = {
        '6.24': {'purchase_incl': net8, 'tax': tax_p8, 'trans_incl': tr8, 'trans_tax': trans_tax_8,
                 'trans50_incl': tr50_8, 'trans50_tax': trans50_tax_8},
        '7.8': {'purchase_incl': net10, 'tax': tax_p10, 'trans_incl': tr10, 'trans_tax': trans_tax_10,
                'trans50_incl': tr50_10, 'trans50_tax': trans50_tax_10},
    }
    for v in col.values():
        v['subtotal'] = v['tax'] + v['trans_tax'] + v['trans50_tax']
        v['deductible'] = apply_ratio(v['subtotal'])
    deductible = col['6.24']['deductible'] + col['7.8']['deductible']
    if not full_deduction:
        warnings.append(('課税売上割合が95%未満(または売上5億円超)のため、一括比例配分方式で計算しています。',
                         'The taxable-sales ratio is under 95% (or sales exceed ¥500m), so the lump-sum '
                         'proportional method is used for input tax.'))

    # ---- Return lines (申告書 GK0306) ---------------------------------------------------
    L = {}
    L[1], L[2], L[3], L[4], L[5], L[6] = base, sales_tax, 0, deductible, 0, 0
    L[7] = L[4] + L[5] + L[6]
    L[8] = max(0, L[7] - L[2] - L[3])
    L[9] = max(0, L[2] + L[3] - L[7])
    L[10] = c['interim_paid']
    L[11] = max(0, L[9] - L[10])
    L[12] = max(0, L[10] - L[9])
    L[13] = 0
    L[14] = L[11]
    L[15], L[16] = taxable_excl, total_excl
    L[17], L[18] = L[8], L[9]
    L[19] = L[17] * LOCAL_NUM // LOCAL_DEN
    L[20] = L[18] * LOCAL_NUM // LOCAL_DEN
    L[21] = c['interim_paid_local']
    L[22] = max(0, L[20] - L[21])
    L[23] = max(0, L[21] - L[20])
    L[24] = 0
    L[25] = L[22]
    L[26] = (L[11] + L[22]) - (L[8] + L[12] + L[19] + L[23])

    # ---- Per-rate table (付表4-(9)): columns 6.24% / 7.8% / total --------------------------
    rate_rows = {}
    for name, b, tax_s, excl, d in (
            ('6.24', base_8, sales_tax_8, excl_8, col['6.24']['deductible']),
            ('7.8', base_10, sales_tax_10, excl_10, col['7.8']['deductible'])):
        rate_rows[name] = {
            1: b, '1-1': excl, '1-2': 0, 2: tax_s, 3: 0, 4: d, 5: 0, '5-1': 0, '5-2': 0, 6: 0,
            7: d, }
    rate_rows['total'] = {k: rate_rows['6.24'][k] + rate_rows['7.8'][k] for k in rate_rows['6.24']}
    rate_rows['total'].update({8: L[8], 9: L[9], 10: L[8], 11: L[9],
                               12: L[19], 13: L[20]})

    # ---- Transaction summary (課税取引金額計算表) ------------------------------------------
    assets_incl = min(assets10, p10)
    goods_incl = min(goods10, p10 - assets_incl)
    expense_incl = p10 - assets_incl - goods_incl
    transactions = [
        {'code': '1', 'kind': 'sales', 'rate': '10.0%', 'amount': sales_incl_10},
        {'code': '1', 'kind': 'sales', 'rate': '8.0% (reduced)', 'amount': sales_incl_8},
        {'code': '3', 'kind': 'nontaxable_sales', 'rate': '', 'amount': nontaxable},
        {'code': '5', 'kind': 'purchase_assets', 'rate': '10.0%', 'amount': assets_incl},
        {'code': '5', 'kind': 'purchase_goods', 'rate': '10.0%', 'amount': goods_incl},
        {'code': '5', 'kind': 'purchase_expenses', 'rate': '10.0%', 'amount': expense_incl},
        {'code': '5', 'kind': 'purchase_reduced', 'rate': '8.0% (reduced)', 'amount': p8},
        {'code': '51', 'kind': 'purchase_returns', 'rate': '10.0%', 'amount': ret10},
        {'code': '51', 'kind': 'purchase_returns', 'rate': '8.0% (reduced)', 'amount': ret8},
        {'code': '52', 'kind': 'transitional', 'rate': '10.0% x 80%', 'amount': tr10},
        {'code': '52', 'kind': 'transitional', 'rate': '8.0% (reduced) x 80%', 'amount': tr8},
    ]
    if tr50_10 or tr50_8:
        transactions += [
            {'code': '52', 'kind': 'transitional50', 'rate': '10.0% x 50%', 'amount': tr50_10},
            {'code': '52', 'kind': 'transitional50', 'rate': '8.0% (reduced) x 50%', 'amount': tr50_8},
        ]

    refund_total = -L[26] if L[26] < 0 else 0
    return {
        'sources': sources, 'warnings': warnings,
        'components': {'expenses_10': exp10, 'goods_10': goods10, 'assets_10': assets10, 'expenses_8': exp8},
        'sales': {'incl_10': sales_incl_10, 'incl_8': sales_incl_8, 'excl_10': excl_10, 'excl_8': excl_8,
                  'taxable_excl': taxable_excl, 'nontaxable': nontaxable, 'total_excl': total_excl,
                  'base_10': base_10, 'base_8': base_8, 'base': base,
                  'tax_10': sales_tax_10, 'tax_8': sales_tax_8, 'tax': sales_tax},
        'ratio': ratio, 'ratio_pct_floor': ratio_pct_floor, 'ratio_pct_full': ratio * 100,
        'full_deduction': full_deduction, 'over_500m': taxable_excl > 500_000_000,
        'purchases': {'incl_10': p10, 'incl_8': p8, 'returns_10': ret10, 'returns_8': ret8,
                      'transitional_10': tr10, 'transitional_8': tr8,
                      'transitional50_10': tr50_10, 'transitional50_8': tr50_8, 'cols': col,
                      'deductible': deductible},
        'lines': L, 'rate_rows': rate_rows, 'transactions': transactions,
        'refund_total': refund_total, 'payable_total': max(0, L[26]),
    }

"""Compute the 決算報告書 figures (P&L, balance sheet, equity statement, notes).

Pure calculation: no PDF code. Amounts are whole yen (int).

Data sources
- Derived from existing app data when the matching input is ``None``:
  sales (Order type=sale), purchases (Order type=purchase), cash (latest bank
  Transaction balance per CompanyAccount), SG&A (Expense grouped by category).
- Everything else comes from StatementInput / FixedAsset.
``sources`` in the result says which figures were derived vs entered, so the UI can
show the user what to double-check.
"""
from collections import OrderedDict

from django.db.models import Sum

from apps.expense.models import Expense
from apps.hr.models import Salary
from apps.revenue.models import CompanyAccount, Order, Transaction

from .depreciation import TANGIBLE, depreciate
from .inputs import normalize_inputs

CATEGORY_LABELS = {
    'building': '建物',
    'equipment': '工具器具備品',
    'vehicle': '車両運搬具',
    'other_tangible': 'その他有形固定資産',
}


def _yen(value):
    return int(round(value or 0))


def _order_total(user, fy, transaction_type):
    qs = Order.objects.filter(
        user=user, transaction_type=transaction_type,
        transaction_date__range=(fy.start_date, fy.end_date),
    )
    return _yen(qs.aggregate(t=Sum('total_amount'))['t'])


def _bank_cash(user, end_date):
    total = 0
    for account in CompanyAccount.objects.filter(user=user):
        last = (Transaction.objects
                .filter(company_account=account, date__lte=end_date)
                .order_by('-date', '-id').first())
        if last:
            total += _yen(last.balance)
    return total


def _sga_from_expenses(user, fy):
    totals = OrderedDict()
    expenses = (Expense.objects
                .filter(user=user, date__range=(fy.start_date, fy.end_date))
                .select_related('category').order_by('category_id', 'id'))
    for exp in expenses:
        label = exp.category.name if exp.category_id else '雑費'
        totals[label] = totals.get(label, 0) + _yen(exp.amount)
    return [{'label': k, 'amount': v} for k, v in totals.items()]


def _salaries(user, fy):
    start, end = fy.start_date.strftime('%Y-%m'), fy.end_date.strftime('%Y-%m')
    qs = Salary.objects.filter(admin=user, salary_month__gte=start, salary_month__lte=end)
    return _yen(qs.aggregate(t=Sum('gross_payment'))['t'])


def _total(items):
    return sum(i['amount'] for i in items)


def _nonzero(items):
    return [i for i in items if i['amount'] != 0]


def compute_statements(user, fy):
    inputs = normalize_inputs(getattr(getattr(fy, 'inputs', None), 'data', None))
    sources, warnings = {}, []

    def pick(key, derive):
        if inputs[key] is not None:
            sources[key] = 'input'
            return inputs[key]
        sources[key] = 'derived'
        return derive()

    # ---- Fixed assets / depreciation -------------------------------------------------
    dep_rows = [depreciate(a, fy.start_date, fy.end_date) for a in fy.fixed_assets.all()]
    tangible = [r for r in dep_rows if r['asset'].category in TANGIBLE]
    deferred = [r for r in dep_rows if r['asset'].category == 'deferred']
    depreciation_total = sum(r['depreciation'] for r in tangible)
    deferred_amortization = sum(r['depreciation'] for r in deferred)

    # ---- Profit & loss ---------------------------------------------------------------
    sales = pick('sales', lambda: _order_total(user, fy, 'sale'))
    purchases = pick('purchases', lambda: _order_total(user, fy, 'purchase'))
    net_purchases = purchases - inputs['purchase_discounts']
    cost_of_sales = inputs['opening_inventory'] + net_purchases - inputs['closing_inventory']
    gross_profit = sales - cost_of_sales

    sga = _sga_from_expenses(user, fy)
    sources['sga'] = 'derived'
    if inputs['include_salaries']:
        salaries = _salaries(user, fy)
        if salaries:
            sga.append({'label': '給料手当', 'amount': salaries})
    sga += inputs['extra_sga']
    if depreciation_total:
        sga.append({'label': '減価償却費', 'amount': depreciation_total})
    if deferred_amortization:
        sga.append({'label': '繰延資産償却', 'amount': deferred_amortization})
    sga = _nonzero(sga)
    sga_total = _total(sga)
    operating_income = gross_profit - sga_total

    non_op_income = _nonzero(inputs['non_operating_income'])
    non_op_expenses = _nonzero(inputs['non_operating_expenses'])
    ordinary_income = operating_income + _total(non_op_income) - _total(non_op_expenses)
    pretax_income = ordinary_income
    taxes_total = inputs['income_taxes'] + inputs['prior_year_taxes']
    net_income = pretax_income - taxes_total

    pl = {
        'sales': sales, 'purchases': purchases,
        'purchase_discounts': inputs['purchase_discounts'], 'net_purchases': net_purchases,
        'opening_inventory': inputs['opening_inventory'], 'closing_inventory': inputs['closing_inventory'],
        'cost_of_sales': cost_of_sales, 'gross_profit': gross_profit,
        'sga_items': sga, 'sga_total': sga_total, 'operating_income': operating_income,
        'non_op_income_items': non_op_income, 'non_op_income_total': _total(non_op_income),
        'non_op_expense_items': non_op_expenses, 'non_op_expense_total': _total(non_op_expenses),
        'ordinary_income': ordinary_income, 'pretax_income': pretax_income,
        'income_taxes': inputs['income_taxes'], 'prior_year_taxes': inputs['prior_year_taxes'],
        'taxes_total': taxes_total, 'net_income': net_income,
    }

    # ---- Balance sheet ---------------------------------------------------------------
    cash = pick('cash', lambda: _bank_cash(user, fy.end_date))
    current_assets = []
    if cash:
        current_assets.append({'label': '現金及び預金', 'amount': cash})
    if inputs['closing_inventory']:
        current_assets.append({'label': '商品', 'amount': inputs['closing_inventory']})
    current_assets += _nonzero(inputs['other_current_assets'])

    tangible_assets = []
    for key, label in CATEGORY_LABELS.items():
        value = sum(r['closing'] for r in tangible if r['asset'].category == key)
        if value:
            tangible_assets.append({'label': label, 'amount': value})
    investments = _nonzero(inputs['investments'])
    deferred_assets = [{'label': r['asset'].name, 'amount': r['closing']} for r in deferred if r['closing']]

    current_total = _total(current_assets)
    fixed_total = _total(tangible_assets) + _total(investments)
    deferred_total = _total(deferred_assets)
    assets_total = current_total + fixed_total + deferred_total

    current_liabilities = _nonzero(inputs['current_liabilities'])
    fixed_liabilities = _nonzero(inputs['fixed_liabilities'])
    liabilities_total = _total(current_liabilities) + _total(fixed_liabilities)

    retained_earnings = inputs['opening_retained_earnings'] - inputs['dividends'] + net_income
    equity_total = inputs['capital'] + retained_earnings
    difference = assets_total - (liabilities_total + equity_total)
    if difference:
        liab_eq = liabilities_total + equity_total
        warnings.append((
            f'貸借が一致しません (資産 {assets_total:,} − 負債・純資産 {liab_eq:,} = {difference:,})。入力値を確認してください。',
            f'The balance sheet does not balance (assets {assets_total:,} - liabilities and net assets {liab_eq:,} = '
            f'{difference:,}). Check your inputs.'))

    bs = {
        'current_assets': current_assets, 'current_assets_total': current_total,
        'tangible_assets': tangible_assets, 'investments': investments, 'fixed_assets_total': fixed_total,
        'tangible_total': _total(tangible_assets), 'investments_total': _total(investments),
        'deferred_assets': deferred_assets, 'deferred_total': deferred_total,
        'assets_total': assets_total,
        'current_liabilities': current_liabilities, 'current_liabilities_total': _total(current_liabilities),
        'fixed_liabilities': fixed_liabilities, 'fixed_liabilities_total': _total(fixed_liabilities),
        'liabilities_total': liabilities_total,
        'capital': inputs['capital'], 'retained_earnings': retained_earnings, 'equity_total': equity_total,
        'liabilities_and_equity_total': liabilities_total + equity_total,
        'difference': difference, 'balanced': difference == 0,
    }

    # ---- Statement of changes in equity ---------------------------------------------
    equity = {
        'opening_capital': inputs['capital'],
        'opening_retained': inputs['opening_retained_earnings'],
        'opening_total': inputs['capital'] + inputs['opening_retained_earnings'],
        'dividends': inputs['dividends'],
        'net_income': net_income,
        'change_total': net_income - inputs['dividends'],
        'closing_capital': inputs['capital'],
        'closing_retained': retained_earnings,
        'closing_total': equity_total,
    }

    return {
        'company': _company(user),
        'period': {'term_no': fy.term_no, 'start_date': fy.start_date, 'end_date': fy.end_date},
        'pl': pl, 'bs': bs, 'equity': equity,
        'notes': _notes(inputs, dep_rows, tangible),
        'sources': sources, 'warnings': warnings,
        # Private (underscore) keys feed the tax calculators and are stripped from API output.
        '_inputs': inputs, '_dep_rows': dep_rows,
    }


def _company(user):
    profile = getattr(user, 'company_profile', None)
    name = (profile.legal_name if profile and profile.legal_name else None) or user.company_name or ''
    address = (profile.address if profile and profile.address else None) or user.company_address or ''
    return {'name': name, 'address': address}


def _notes(inputs, dep_rows, tangible):
    """Notes to the financial statements as (japanese, english) pairs."""
    methods = {r['asset'].method for r in tangible}
    dep = []
    if 'declining_200' in methods and 'straight_line' in methods:
        dep = [('　　　定率法を採用しています。', '     The declining-balance method is applied.'),
               ('　　　ただし、建物、附属設備及び構築物については定額法を採用しています。',
                '     However, buildings, attached facilities and structures use the straight-line method.')]
    elif 'declining_200' in methods:
        dep = [('　　　定率法を採用しています。', '     The declining-balance method is applied.')]
    elif 'straight_line' in methods:
        dep = [('　　　定額法を採用しています。', '     The straight-line method is applied.')]

    lines = [('1.　この計算書類は、「中小企業の会計に関する基本要領」によって作成しています。',
              '1.  These financial statements are prepared in accordance with the "Guidelines for Accounting of '
              'Small and Medium-sized Enterprises".'),
             ('', ''),
             ('2.　重要な会計方針に係る事項に関する注記', '2.  Notes on significant accounting policies')]
    if dep:
        lines += [('(1)　固定資産の減価償却の方法', '(1) Depreciation of fixed assets'),
                  ('　　有形固定資産', '    Tangible fixed assets')] + dep
    lines += [('(2)　費用・収益の計上基準', '(2) Recognition of revenue and expenses'),
              ('　　収益は実現主義、費用は発生主義', '    Revenue on a realization basis; expenses on an accrual basis'),
              ('(3)　消費税等の会計処理', '(3) Accounting for consumption tax'),
              ('　　消費税等の会計処理は、税抜方式によっています。',
               '    Consumption tax is accounted for using the tax-excluded method.'),
              ('', ''),
              ('3.　貸借対照表に関する注記', '3.  Notes to the balance sheet')]
    executive = sum(i['amount'] for i in inputs['other_current_assets'] if i.get('executive'))
    accumulated = sum(r['accumulated'] for r in tangible)
    bs_notes = []
    if executive:
        bs_notes.append((f'業務執行社員等に対する金銭債権　　{executive:,}円',
                         f'Monetary claims on executive members:  JPY {executive:,}'))
    if accumulated:
        bs_notes.append((f'有形固定資産の減価償却累計額　　　{accumulated:,}円',
                         f'Accumulated depreciation of tangible fixed assets:  JPY {accumulated:,}'))
    for letter, (ja, en) in zip('abcdefgh', bs_notes):
        lines.append((f'　　({letter}){ja}', f'    ({letter}) {en}'))
    for extra in inputs['notes_extra']:
        lines.append((extra, extra))
    return lines

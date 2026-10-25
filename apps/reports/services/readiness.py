"""Readiness checklist: what is still missing or needs confirming before the statements can be relied on.

Each item is ``{key, title, status, detail, tab}`` with status ``ok`` | ``todo`` (must fix) | ``check``
(confirm it is right). Text is English because it is shown in the app UI, which has its own translation toggle.
"""
from apps.expense.models import Expense
from apps.revenue.models import CompanyAccount, Order

REQUIRED_PROFILE = (
    ('legal_name', 'company name'), ('address', 'address'), ('corporate_number', 'corporate number'),
    ('representative_name', 'representative'), ('tax_office', 'tax office'),
)


def _months(fy):
    return (fy.end_date.year - fy.start_date.year) * 12 + fy.end_date.month - fy.start_date.month + 1


def compute(user, fy, data, profile):
    inputs, pl, bs, ct = data['_inputs'], data['pl'], data['bs'], data['consumption']
    items = []

    def add(key, title, status, detail, tab):
        items.append({'key': key, 'title': title, 'status': status, 'detail': detail, 'tab': tab})

    # 1. Company details
    missing = [label for field, label in REQUIRED_PROFILE if not (profile and getattr(profile, field))]
    add('company', 'Company details',
        'todo' if missing else 'ok',
        f"Missing: {', '.join(missing)}." if missing else 'Name, address, corporate number, representative and tax office are set.',
        'company')

    # 2. Period
    months = _months(fy)
    if months != 12 and fy.term_no > 1:
        add('period', 'Fiscal period', 'check',
            f'This period is {months} months. A full tax year is 12 months; a shorter one is only right for a '
            'year-to-date report or a company\'s first term.', 'year')
    else:
        add('period', 'Fiscal period', 'ok', f'{fy.start_date} to {fy.end_date} ({months} months).', 'year')

    # 3. Opening balances
    if fy.term_no > 1 and inputs['capital'] == 0 and inputs['opening_retained_earnings'] == 0:
        add('opening', 'Opening balances', 'todo',
            'Capital and opening retained earnings are 0. Use "Start next term" on the previous year, or enter them.',
            'year')
    else:
        add('opening', 'Opening balances', 'ok',
            f"Capital ¥{inputs['capital']:,}; opening retained earnings ¥{inputs['opening_retained_earnings']:,}.",
            'inputs')

    # 4. Bank accounts
    accounts = CompanyAccount.objects.filter(user=user).count()
    if inputs['cash'] is not None:
        add('cash', 'Cash and bank balances', 'ok', 'Cash was entered manually.', 'inputs')
    elif accounts > 1 and inputs['cash_accounts'] is None:
        add('cash', 'Cash and bank balances', 'todo',
            f'You have {accounts} bank accounts and all are counted. Tick only the accounts on the company\'s books.',
            'inputs')
    elif accounts == 0:
        add('cash', 'Cash and bank balances', 'check', 'No bank accounts recorded. Enter the cash balance.', 'inputs')
    else:
        add('cash', 'Cash and bank balances', 'ok', f"Cash and deposits: ¥{sum(i['amount'] for i in bs['current_assets'] if i['label'] == '現金及び預金'):,}.", 'inputs')

    # 4b. Balances carried over from last year: each must be updated to its 31 Dec position
    carried = (inputs['other_current_assets'] + inputs['investments'] + inputs['current_liabilities']
               + inputs['fixed_liabilities'])
    if fy.term_no > 1 and carried:
        names = ', '.join(f"{i['label']} ¥{i['amount']:,}" for i in carried)
        tax_c = inputs['tax']['corporate']
        unpaid = tax_c['opening_unpaid_corporate'] + tax_c['opening_unpaid_pref'] + tax_c['opening_unpaid_city']
        paid = tax_c['paid_corporate'] + tax_c['paid_pref'] + tax_c['paid_city']
        extra = (f" Last year's taxes of ¥{unpaid:,} were unpaid at the start of the year: enter what was paid under "
                 'Tax settings.') if unpaid and not paid else ''
        add('carried', 'Balances carried over from last year', 'check',
            f'Update each to its position on the last day of the year: {names}.{extra}', 'inputs')

    # 5. Sales
    if inputs['sales'] is not None:
        add('sales', 'Sales', 'ok', f"Sales entered manually: ¥{pl['sales']:,}.", 'inputs')
    else:
        orders = Order.objects.filter(user=user, transaction_type='sale',
                                      transaction_date__range=(fy.start_date, fy.end_date)).count()
        add('sales', 'Sales', 'check',
            f"¥{pl['sales']:,} from {orders} sale orders. Confirm this matches your sales records, or enter the "
            'correct total.', 'inputs')

    # 6. Purchases and inventory
    if pl['purchases'] > 0 and inputs['closing_inventory'] == 0:
        add('inventory', 'Purchases and unsold inventory', 'todo',
            f"Purchases are ¥{pl['purchases']:,} but closing inventory is 0. Enter the cost of vehicles still unsold "
            'at the period end.', 'inputs')
    else:
        add('inventory', 'Purchases and unsold inventory', 'ok',
            f"Purchases ¥{pl['purchases']:,}; closing inventory ¥{inputs['closing_inventory']:,}.", 'inputs')

    # 7. Fixed assets
    rows = data['_dep_rows']
    if not rows:
        add('assets', 'Fixed assets', 'check',
            'No fixed assets entered. Add computers, equipment, vehicles or buildings the company owns.', 'assets')
    else:
        add('assets', 'Fixed assets', 'ok',
            f"{len(rows)} assets; depreciation ¥{sum(r['depreciation'] for r in rows):,}.", 'assets')

    # 8. Consumption tax
    taxed = Expense.objects.filter(user=user, date__range=(fy.start_date, fy.end_date), tax_amount__gt=0).count()
    if ct['sources'].get('purchase_incl_10') == 'input':
        add('consumption', 'Consumption tax', 'ok', 'Purchase totals were entered.', 'tax')
    elif taxed == 0:
        add('consumption', 'Consumption tax', 'todo',
            'No expense has consumption tax recorded, so deductible input tax cannot be estimated. Enter the '
            'tax-included purchase totals (from your tax software or invoices).', 'tax')
    else:
        add('consumption', 'Consumption tax', 'check',
            f'Estimated from {taxed} expenses with tax recorded. Compare with your invoices.', 'tax')

    # 9-11. Offices, shareholders, accountant
    add('offices', 'Offices (local taxes)', 'ok' if profile and profile.offices else 'check',
        'Offices are registered.' if profile and profile.offices else
        'No offices registered; local taxes assume the head office only.', 'company')
    add('shareholders', 'Shareholders / members', 'ok' if profile and profile.shareholders else 'check',
        'Shareholders are registered.' if profile and profile.shareholders else
        'None registered; the family-company schedule will be blank.', 'company')
    named = bool(profile and profile.accountant_name)
    add('accountant', 'Tax accountant details', 'ok' if named else 'check',
        'Set.' if named else 'Needed for the power-of-attorney pages.', 'company')

    # 12-13. Reconciliation
    if bs['balanced']:
        add('balance', 'Balance sheet reconciles', 'ok', 'Assets equal liabilities plus net assets.', 'inputs')
    else:
        add('balance', 'Balance sheet reconciles', 'todo',
            f"Off by ¥{abs(bs['difference']):,}. Check cash, inventory, liabilities and opening balances.", 'inputs')
    notes = [n[1] if isinstance(n, (tuple, list)) else n for n in data['tax_notes']]
    if notes:
        add('consistency', 'Tax figures agree with each other', 'check', ' '.join(notes[:2]), 'tax')
    else:
        add('consistency', 'Tax figures agree with each other', 'ok', 'No differences found.', 'tax')
    return items

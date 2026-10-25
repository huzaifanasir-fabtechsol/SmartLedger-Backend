"""Compute everything needed for the full filing package in one dict."""
import datetime

from . import consumption_tax, corporate_tax, local_tax, readiness, schedules
from apps.revenue.models import CompanyAccount, OrderItem, Transaction

from .inputs import normalize_inputs
from .statements import compute_statements, expense_categories


def _profile(user):
    return getattr(user, 'company_profile', None)


def compute_package(user, fy, raw_inputs=None):
    data = compute_statements(user, fy, raw_inputs)
    profile = _profile(user)
    data['profile'] = profile
    data['_fy'] = fy
    data['consumption'] = consumption_tax.compute(user, fy, data)
    corp = corporate_tax.compute(user, fy, data, profile)
    local = local_tax.compute(user, fy, data, corp, profile)
    corporate_tax.finish_schedule5(data, corp, local)
    data['corporate'], data['local'] = corp, local
    data['schedules'] = schedules.compute(user, fy, data, corp, local, data['consumption'], profile)

    notes = []
    if corp['estimated_taxes'] != data['pl']['income_taxes']:
        calc, booked = corp['estimated_taxes'], data['pl']['income_taxes']
        notes.append((f'計算上の法人税等 {calc:,} と損益計算書の法人税・住民税及び事業税 {booked:,} が異なります。',
                      f'Calculated taxes ({calc:,}) differ from the corporate, inhabitant and enterprise taxes on the '
                      f'income statement ({booked:,}).'))
    if corp['form5_1']['difference']:
        diff = corp['form5_1']['difference']
        notes.append((f'別表五(一)の差引合計と繰越利益剰余金に {diff:,} の差があります。未納税額を入力してください。',
                      f'Schedule 5-(1) total differs from retained earnings by {diff:,}. Enter the unpaid tax balances.'))
    data['tax_notes'] = notes + corp['warnings'] + local['warnings'] + data['consumption']['warnings']
    data['readiness'] = readiness.compute(user, fy, data, profile)
    return data


def public_view(data):
    """JSON-safe subset for the preview API: drops private (_) keys and model objects."""
    out = {k: v for k, v in data.items() if not k.startswith('_') and k != 'profile'}
    out['schedules'] = {k: v for k, v in data['schedules'].items() if k in ('monthly', 'refund_reasons')}
    out['local'] = {k: v for k, v in data['local'].items() if k != 'offices'}
    out['corporate'] = {k: v for k, v in data['corporate'].items() if not k.startswith('form')}
    out['corporate']['carry_total'] = data['corporate']['form7']['carry_total']
    # The UI is English-only (it has its own translation toggle): expose the English message of each warning.
    english = lambda items: [i[1] if isinstance(i, (tuple, list)) else i for i in items]
    out['warnings'] = english(data['warnings'])
    out['tax_notes'] = english(data['tax_notes'])
    out['consumption'] = {**out['consumption'], 'warnings': english(out['consumption']['warnings'])}
    out['notes'] = [n[1] if isinstance(n, (tuple, list)) else n for n in data['notes']]
    return out


TOP_OVERRIDES = ('sales', 'purchases', 'cash')
CONSUMPTION_OVERRIDES = ('sales_incl_10', 'sales_incl_8', 'nontaxable_sales', 'purchase_incl_10', 'purchase_incl_8')
CORPORATE_OVERRIDES = ('entertainment_expenses', 'unpaid_corporate', 'unpaid_pref', 'unpaid_city')


def unsold_cars(user, fy):
    """Reference list: cars with a recorded *purchase* on/before the period end and no recorded sale by then.

    This is only as complete as the orders in the system (cars are often entered only on the sale invoice),
    so it is shown for comparison with the physical stock, never used automatically.
    """
    sold_ids = set(OrderItem.objects.filter(
        order__user=user, order__transaction_type='sale', order__transaction_date__lte=fy.end_date,
        vehicle_price__gt=0).values_list('car_id', flat=True))
    bought = (OrderItem.objects
              .filter(order__user=user, order__transaction_type='purchase', order__transaction_date__lte=fy.end_date,
                      vehicle_price__gt=0)
              .exclude(car_id__in=sold_ids).select_related('car', 'car__category', 'order')
              .order_by('order__transaction_date', 'id'))
    cars, seen = [], set()
    for item in bought:
        if item.car_id in seen:
            continue
        seen.add(item.car_id)
        parts = [item.vehicle_price, item.successful_bid, item.listing_fee, item.commission_fee,
                 item.transport_fee, item.registration_fee, item.recycle_fee]
        category = item.car.category
        cars.append({
            'id': item.car_id, 'chassis': item.car.chassis_number,
            'name': f'{category.company} {category.model}'.strip() if category else '',
            'bought_on': item.order.transaction_date.isoformat(), 'order': item.order.order_number,
            'cost_excl_tax': int(round(sum(p or 0 for p in parts))), 'invoice_total': int(round(item.subtotal or 0)),
        })
    return cars


def auto_values(user, fy):
    """What every overridable figure would be if left on Auto, plus the pieces it is made of.

    Two passes so each figure is derived from the user's *actual* upstream numbers: the first clears
    the top-level overrides (sales/purchases/cash); the second clears the tax-setting overrides but
    keeps whatever sales/purchases the user entered (the consumption tax estimate builds on those).
    """
    raw = normalize_inputs(getattr(getattr(fy, 'inputs', None), 'data', None))
    first = compute_package(user, fy, {**raw, **{k: None for k in TOP_OVERRIDES}})
    tax = raw['tax']
    cleared = {**raw, 'tax': {
        **tax,
        'consumption': {**tax['consumption'], **{k: None for k in CONSUMPTION_OVERRIDES}},
        'corporate': {**tax['corporate'], **{k: None for k in CORPORATE_OVERRIDES}},
    }}
    second = compute_package(user, fy, cleared)

    pl, ct, corp = first['pl'], second['consumption'], second['corporate']
    tax_c = raw['tax']['corporate']
    cash = next((i['amount'] for i in first['bs']['current_assets'] if i['label'] == '現金及び預金'), 0)
    comp, s = ct['components'], ct['sales']
    unpaid = corp['form5_1']['unpaid']
    selected = raw['cash_accounts']
    accounts = []
    for account in CompanyAccount.objects.filter(user=user).order_by('id'):
        last = (Transaction.objects.filter(company_account=account, date__lte=fy.end_date)
                .order_by('-date', '-id').first())
        accounts.append({'id': account.id, 'label': f'{account.bank_name} {account.account_number}'.strip(),
                         'balance': int(round(last.balance)) if last else 0,
                         'transactions': account.transactions.count(),
                         'selected': selected is None or account.id in selected})
    ent_lines = [[i['label'], i['amount']] for i in second['pl']['sga_items'] if '交際' in i['label']]
    return {
        'sales': pl['sales'], 'purchases': pl['purchases'], 'cash': cash, 'accounts': accounts,
        'unsold_cars': unsold_cars(user, fy),
        'categories': expense_categories(user, fy, raw['category_accounts']) if raw['app_expenses'] else [],
        'consumption': {
            'sales_incl_10': s['incl_10'], 'sales_incl_8': s['incl_8'], 'nontaxable_sales': s['nontaxable'],
            'purchase_incl_10': ct['purchases']['incl_10'], 'purchase_incl_8': ct['purchases']['incl_8'],
        },
        'corporate': {
            'entertainment_expenses': corp['form15'][1], 'unpaid_corporate': unpaid['corporate'],
            'unpaid_pref': unpaid['pref'], 'unpaid_city': unpaid['city'],
        },
        # Human-readable pieces so the user can verify each figure: [[label, amount], ...]
        'details': {
            'sales': [['Sale orders in the period', pl['sales']]],
            'purchases': [['Purchase orders in the period', pl['purchases']]],
            'cash': [[f"{d['name']} {d['account_no']}".strip() or 'Bank', d['amount']] for d in first['schedules']['deposits']],
            'consumption.sales_incl_10': [['Sales x 1.10', s['incl_10']]],
            'consumption.nontaxable_sales': [['Interest income', s['nontaxable']]],
            'consumption.purchase_incl_10': [
                ['Expenses carrying 10% tax', comp['expenses_10']],
                ['Merchandise purchases x 1.10', comp['goods_10']],
                ['Fixed assets acquired this year x 1.10', comp['assets_10']]],
            'consumption.purchase_incl_8': [['Expenses carrying 8% tax', comp['expenses_8']]],
            'corporate.entertainment_expenses': ent_lines,
            'corporate.unpaid_corporate': [['Unpaid at start of year', tax_c['opening_unpaid_corporate']],
                                           ['Corporate tax payable', corp['corp_payable']],
                                           ['Local corporate tax payable', corp['local_payable']],
                                           ['Paid this year', -tax_c['paid_corporate']]],
            'corporate.unpaid_pref': [['Unpaid at start of year', tax_c['opening_unpaid_pref']],
                                      ['Accrued this year', second['local']['pref_total_payable']],
                                      ['Paid this year', -tax_c['paid_pref']]],
            'corporate.unpaid_city': [['Unpaid at start of year', tax_c['opening_unpaid_city']],
                                      ['Accrued this year', second['local']['city_total_payable']],
                                      ['Paid this year', -tax_c['paid_city']]],
        },
    }


def _next_period(fy):
    """The 12 months following ``fy`` (start = day after the end; end = last day of the same month next year)."""
    start = fy.end_date + datetime.timedelta(days=1)
    end = datetime.date(start.year + 1, start.month, 1) - datetime.timedelta(days=1)
    return start, end


def roll_forward(user, fy):
    """Create the next fiscal year seeded with ``fy``'s closing balances.

    Carried: capital, retained earnings, inventory, balance-sheet lists (receivables, deposits, loans,
    payables ...), the provision for taxes, fixed assets at their closing book value, and loss
    carry-forwards. Not carried: sales/purchases/cash overrides, one-off flows (extra SG&A, non-operating
    items, taxes booked) and tax-period settings. Settled items (e.g. last year's taxes payable or a tax
    refund received) still need to be edited by the user, which is why the lists are copied, not guessed.
    """
    from django.db import transaction

    from apps.reports.models import FiscalYear, FixedAsset, StatementInput

    if FiscalYear.objects.filter(user=user, term_no=fy.term_no + 1).exists():
        raise ValueError(f'Term {fy.term_no + 1} already exists.')
    data = compute_package(user, fy)
    inputs, bs, corp = data['_inputs'], data['bs'], data['corporate']
    start, end = _next_period(fy)

    unpaid = corp['form5_1']['unpaid']
    losses = [{'label': r['label'], 'amount': r['carry']} for r in corp['form7']['rows'] if r['carry']]
    if corp['form7']['current_loss']:
        losses.append({'label': f"{fy.start_date:%Y-%m-%d} to {fy.end_date:%Y-%m-%d}",
                       'amount': corp['form7']['current_loss']})
    seed = normalize_inputs({
        'capital': bs['capital'],
        'opening_retained_earnings': bs['retained_earnings'],
        'opening_inventory': inputs['closing_inventory'],
        'other_current_assets': inputs['other_current_assets'],
        'investments': inputs['investments'],
        'current_liabilities': inputs['current_liabilities'],
        'fixed_liabilities': inputs['fixed_liabilities'],
        # who the landlords are carries over; the amounts and periods are this year's to enter
        'rent_details': [{**r, 'amount': 0, 'note': ''} for r in inputs['rent_details']],
        'include_salaries': inputs['include_salaries'],
        'tax': {'corporate': {'prior_losses': losses,
                              'opening_provision': corp['form5_2']['provision'][41],
                              'opening_unpaid_corporate': unpaid['corporate'],
                              'opening_unpaid_pref': unpaid['pref'],
                              'opening_unpaid_city': unpaid['city']}},
    })
    with transaction.atomic():
        new_fy = FiscalYear.objects.create(user=user, term_no=fy.term_no + 1, start_date=start, end_date=end)
        StatementInput.objects.create(fiscal_year=new_fy, data=seed)
        for row in data['_dep_rows']:
            asset = row['asset']
            if row['closing'] <= 0:
                continue                                     # fully written off
            FixedAsset.objects.create(
                fiscal_year=new_fy, name=asset.name, category=asset.category, acquired_on=asset.acquired_on,
                cost=asset.cost, method=asset.method, useful_life=asset.useful_life,
                opening_book_value=row['closing'])
    return new_fy

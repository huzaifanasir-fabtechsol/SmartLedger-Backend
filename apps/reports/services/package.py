"""Compute everything needed for the full filing package in one dict."""
from . import consumption_tax, corporate_tax, local_tax, schedules
from .inputs import normalize_inputs
from .statements import compute_statements


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
    cash = next((i['amount'] for i in first['bs']['current_assets'] if i['label'] == '現金及び預金'), 0)
    comp, s = ct['components'], ct['sales']
    unpaid = corp['form5_1']['unpaid']
    ent_lines = [[i['label'], i['amount']] for i in second['pl']['sga_items'] if '交際' in i['label']]
    return {
        'sales': pl['sales'], 'purchases': pl['purchases'], 'cash': cash,
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
            'corporate.unpaid_corporate': [['Corporate tax payable', corp['corp_payable']],
                                           ['Local corporate tax payable', corp['local_payable']]],
            'corporate.unpaid_pref': [['Prefectural inhabitant tax payable', second['local']['pref_total_payable']]],
            'corporate.unpaid_city': [['Municipal inhabitant tax payable', second['local']['city_total_payable']]],
        },
    }

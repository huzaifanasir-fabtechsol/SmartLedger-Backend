"""地方税 (prefectural/municipal inhabitant tax, enterprise tax, special corporate enterprise tax)
allocated across the offices in ``CompanyProfile.offices``, plus the 納付一覧 due date.

Defaults (all overridable per office in the profile):
- 均等割 from the standard tables by capital and employee count, prorated by months (¥100 floor).
- 法人税割 rates: prefecture 1.0%, municipality 6.0% (standard rates).
- 事業税 (所得割) for a small company: 3.5% / 5.3% / 7.0% on ≤¥4m / ¥4–8m / >¥8m; 特別法人事業税 = 37%.
Income and corporate-tax bases are allocated by employee count.
"""
import calendar
import datetime
import re
from decimal import Decimal

PREF_LEVY = ((10_000_000, 20_000), (100_000_000, 50_000), (1_000_000_000, 130_000),
             (5_000_000_000, 540_000), (None, 800_000))
CITY_LEVY_SMALL = ((10_000_000, 50_000), (100_000_000, 130_000), (1_000_000_000, 160_000),
                   (5_000_000_000, 410_000), (None, 410_000))       # employees ≤ 50
CITY_LEVY_LARGE = ((10_000_000, 120_000), (100_000_000, 150_000), (1_000_000_000, 400_000),
                   (5_000_000_000, 1_750_000), (None, 3_000_000))   # employees > 50


def _table(table, capital):
    for limit, amount in table:
        if limit is None or capital <= limit:
            return amount


def _floor(n, unit):
    return n // unit * unit


def _split_address(address):
    match = re.match(r'^(.{2,3}?[都道府県])(.+?[市区町村])', address or '')
    return (match.group(1), match.group(2)) if match else ('', '')


def _business_tax(income):
    low = min(income, 4_000_000)
    mid = min(max(income - 4_000_000, 0), 4_000_000)
    high = max(income - 8_000_000, 0)
    return _floor(low * 35 // 1000 + mid * 53 // 1000 + high * 70 // 1000, 100)


def due_date(end_date):
    """Last day of the 2nd month after year end, moved to Monday if it falls on a weekend."""
    month = end_date.month + 2
    year = end_date.year + (month - 1) // 12
    month = (month - 1) % 12 + 1
    day = datetime.date(year, month, calendar.monthrange(year, month)[1])
    while day.weekday() >= 5:
        day += datetime.timedelta(days=1)
    return day


def _num(office, key, default):
    """Blank/missing -> default, but an explicit 0 stays 0 (e.g. no per-capita levy in a dormant year)."""
    value = office.get(key)
    return default if value in (None, '') else int(value)


def _offices(profile, capital, override=None):
    raw = list(override) if override else (list(profile.offices) if profile and profile.offices else [])
    if not raw:
        pref, city = _split_address(profile.address if profile else '')
        raw = [{'prefecture': pref, 'municipality': city, 'employees': 1}]
    total_emp = sum(int(o.get('employees') or 0) for o in raw)
    offices = []
    for o in raw:
        emp = int(o.get('employees') or 0)
        months = _num(o, 'months', 12)
        city_table = CITY_LEVY_LARGE if total_emp > 50 else CITY_LEVY_SMALL
        offices.append({
            'prefecture': o.get('prefecture', ''), 'prefecture_office': o.get('prefecture_office', ''),
            'municipality': o.get('municipality', ''), 'employees': emp, 'months': months,
            # the prefectural levy is owed once per prefecture, so it can have its own month count
            'pref_months': _num(o, 'pref_months', months),
            'pref_levy_annual': _num(o, 'pref_levy', _table(PREF_LEVY, capital)),
            'city_levy_annual': _num(o, 'city_levy', _table(city_table, capital)),
            'pref_rate': Decimal(str(o.get('pref_rate') or '1.0')),
            'city_rate': Decimal(str(o.get('city_rate') or '6.0')),
        })
    if total_emp == 0:                       # no counts given: treat the first office as the only one
        offices[0]['employees'] = 1
    return offices


def compute(user, fy, data, corp, profile=None):
    inputs = data['_inputs']
    l_in = inputs['tax']['local']
    capital = corp['capital']
    offices = _offices(profile, capital, inputs['offices'])
    total_emp = sum(o['employees'] for o in offices) or 1

    total_business = _business_tax(corp['taxable_income'])
    for o in offices:
        share = Decimal(o['employees']) / Decimal(total_emp)
        o['share'] = float(share)
        o['income_base'] = _floor(int(corp['taxable_income'] * share), 1000)
        o['corp_tax_base'] = _floor(int(corp['local_base'] * share), 1000)
        o['pref_levy'] = _floor(o['pref_levy_annual'] * o['pref_months'] // 12, 100)
        o['city_levy'] = _floor(o['city_levy_annual'] * o['months'] // 12, 100)
        o['pref_corp_tax'] = _floor(int(o['corp_tax_base'] * o['pref_rate'] / 100), 100)
        o['city_corp_tax'] = _floor(int(o['corp_tax_base'] * o['city_rate'] / 100), 100)
        o['business_tax'] = _floor(int(total_business * share), 100)
        o['special_tax'] = _floor(o['business_tax'] * 37 // 100, 100)
        o['pref_total'] = o['pref_levy'] + o['pref_corp_tax']
        o['city_total'] = o['city_levy'] + o['city_corp_tax']
        # bracket split of this office's income (for 第六号様式)
        o['income_bracket'] = {'low': min(o['income_base'], 4_000_000),
                               'mid': min(max(o['income_base'] - 4_000_000, 0), 4_000_000),
                               'high': max(o['income_base'] - 8_000_000, 0)}

    pref_levy = sum(o['pref_levy'] for o in offices)
    city_levy = sum(o['city_levy'] for o in offices)
    pref_corp = sum(o['pref_corp_tax'] for o in offices)
    city_corp = sum(o['city_corp_tax'] for o in offices)
    pref_inhabitant = pref_levy + pref_corp
    city_total = city_levy + city_corp
    business = sum(o['business_tax'] for o in offices)
    special = sum(o['special_tax'] for o in offices)

    due = due_date(fy.end_date)
    warnings = []
    if not (inputs['offices'] or (profile and profile.offices)):
        warnings.append(('事務所(事業所)が未登録のため、会社の住所を唯一の事務所として地方税を計算しています。',
                         'No offices are registered, so local taxes are calculated with the company address as the '
                         'only office.'))

    return {
        'offices': offices, 'total_employees': total_emp, 'due_date': due,
        'pref_levy_total': pref_levy, 'city_levy_total': city_levy, 'levy_total': pref_levy + city_levy,
        'pref_corp_total': pref_corp, 'city_corp_total': city_corp, 'corp_based_total': pref_corp + city_corp,
        'pref_inhabitant_total': pref_inhabitant, 'city_total': city_total,
        'business_total': business, 'special_total': special,
        'business_tax_unallocated': total_business,
        'interim_pref': l_in['interim_pref'], 'interim_city': l_in['interim_city'],
        'pref_total_payable': max(0, pref_inhabitant - l_in['interim_pref']),
        'city_total_payable': max(0, city_total - l_in['interim_city']),
        'warnings': warnings,
    }

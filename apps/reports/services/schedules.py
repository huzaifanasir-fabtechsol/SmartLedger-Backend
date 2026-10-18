"""Supporting data: 内訳書 lists, depreciation detail/aggregates, monthly figures (事業概況説明書),
refund-return detail (還付申告に関する明細書) and next-year estimates (翌期見込)."""
import datetime
from collections import OrderedDict
from types import SimpleNamespace

from django.db.models import Sum

from apps.hr.models import Salary
from apps.revenue.models import CompanyAccount, Order, Transaction

from .depreciation import TANGIBLE, depreciate

ASSET_KINDS = (('立替', 'advance'), ('前渡', 'advance'), ('仮払', 'advance'), ('未収', 'receivable'),
               ('売掛', 'receivable'), ('貸付', 'loan'), ('保証金', 'deposit_paid'))
LIABILITY_KINDS = (('未払法人税', 'tax_payable'), ('借入', 'borrowing'), ('未払', 'payable'),
                   ('買掛', 'payable'), ('預り', 'deposit_received'), ('前受', 'deposit_received'),
                   ('仮受', 'deposit_received'))


def _kind(item, table):
    if item.get('kind'):
        return item['kind']
    for needle, kind in table:
        if needle in item['label']:
            return kind
    return ''


def _row(item):
    return {'name': item.get('counterparty') or item['label'], 'address': item.get('address', ''),
            'amount': item['amount'], 'note': item.get('note') or (item['label'] if item.get('counterparty') else ''),
            'rate': item.get('rate', ''), 'registration': item.get('registration', ''),
            'label': item['label']}


def _bank_rows(user, fy, cash_total):
    rows, listed = [], 0
    for account in CompanyAccount.objects.filter(user=user):
        last = (Transaction.objects.filter(company_account=account, date__lte=fy.end_date)
                .order_by('-date', '-id').first())
        if last:
            balance = int(round(last.balance))
            listed += balance
            rows.append({'name': account.bank_name, 'branch': account.branch_code,
                         'type': '', 'account_no': account.account_number, 'amount': balance, 'note': ''})
    if cash_total - listed:
        rows.append({'name': '', 'branch': '', 'type': '', 'account_no': '',
                     'amount': cash_total - listed, 'note': 'cash on hand / other'})
    return rows


def _orders(user, fy, kind):
    return Order.objects.filter(user=user, transaction_type=kind,
                                transaction_date__range=(fy.start_date, fy.end_date))


def _monthly(user, fy):
    months, d = [], fy.start_date.replace(day=1)
    while d <= fy.end_date:
        months.append(d)
        d = (d.replace(day=28) + datetime.timedelta(days=4)).replace(day=1)
    rows = []
    for m in months:
        end = (m.replace(day=28) + datetime.timedelta(days=4)).replace(day=1) - datetime.timedelta(days=1)
        sales = _orders(user, fy, 'sale').filter(transaction_date__range=(m, end)).aggregate(t=Sum('total_amount'))['t']
        purchases = _orders(user, fy, 'purchase').filter(transaction_date__range=(m, end)).aggregate(t=Sum('total_amount'))['t']
        rows.append({'month': m, 'sales': int(round(sales or 0)), 'purchases': int(round(purchases or 0))})
    return rows


def _withholding(user, fy):
    start, end = fy.start_date.strftime('%Y-%m'), fy.end_date.strftime('%Y-%m')
    totals = OrderedDict()
    for s in Salary.objects.filter(admin=user, salary_month__gte=start, salary_month__lte=end).order_by('salary_month'):
        totals[s.salary_month] = totals.get(s.salary_month, 0) + int(round(s.income_tax or 0))
    return [{'month': k, 'amount': v} for k, v in totals.items()]


def _top_orders(user, fy, kind, limit):
    qs = _orders(user, fy, kind).filter(total_amount__gte=1_000_000).order_by('-total_amount')[:limit]
    return [{'date': o.transaction_date, 'name': o.customer_name, 'amount': int(round(o.total_amount))} for o in qs]


def depreciation_detail(dep_rows):
    rows, by_category, by_method = [], OrderedDict(), OrderedDict()
    for r in dep_rows:
        a = r['asset']
        row = {'name': a.name, 'category': a.category, 'method': a.method, 'acquired_on': a.acquired_on,
               'life': a.useful_life, 'rate': r['rate'], 'months': r['months'], 'cost': a.cost,
               'opening': r['opening'], 'depreciation': r['depreciation'], 'closing': r['closing'],
               'accumulated': r['accumulated']}
        rows.append(row)
        for store, key in ((by_category, a.category), (by_method, a.method)):
            g = store.setdefault(key, {'cost': 0, 'opening': 0, 'depreciation': 0, 'closing': 0,
                                       'accumulated': 0, 'count': 0})
            for k in ('cost', 'opening', 'depreciation', 'closing', 'accumulated'):
                g[k] += row[k]
            g['count'] += 1
    groups = OrderedDict()           # (category, method) -> sums, for 別表十六
    for row in rows:
        g = groups.setdefault((row['category'], row['method']),
                              {'cost': 0, 'opening': 0, 'depreciation': 0, 'closing': 0, 'rates': set(), 'lives': set()})
        for k in ('cost', 'opening', 'depreciation', 'closing'):
            g[k] += row[k]
        g['rates'].add(row['rate'])
        g['lives'].add(row['life'])
    return {'rows': rows, 'by_category': by_category, 'by_method': by_method, 'groups': groups,
            'total': {k: sum(r[k] for r in rows) for k in ('cost', 'opening', 'depreciation', 'closing', 'accumulated')}}


def _next_year(fy, dep_rows, corp, local):
    start = fy.end_date + datetime.timedelta(days=1)
    end = datetime.date(fy.end_date.year + 1, fy.end_date.month, 1)
    end = (end.replace(day=28) + datetime.timedelta(days=4)).replace(day=1) - datetime.timedelta(days=1)
    rows = []
    for r in dep_rows:
        a = r['asset']
        clone = SimpleNamespace(cost=a.cost, acquired_on=a.acquired_on, method=a.method,
                                useful_life=a.useful_life, opening_book_value=r['closing'])
        nxt = depreciate(clone, start, end)
        rows.append({'name': a.name, 'category': a.category, 'cost': a.cost, 'opening': nxt['opening'],
                     'depreciation': nxt['depreciation'], 'closing': nxt['closing'],
                     'accumulated': a.cost - nxt['closing'], 'tangible': a.category in TANGIBLE})
    total_dep = sum(r['depreciation'] for r in rows)
    # 中間申告: required when the prior corporate tax exceeds ¥200,000 (half of last year's tax).
    required = corp['corp_tax'] > 200_000
    interim = {'corporate': corp['corp_tax'] * 6 // 12 // 100 * 100 if required else 0,
               'local_corporate': corp['local_tax'] * 6 // 12 // 100 * 100 if required else 0,
               'pref': local['pref_inhabitant_total'] * 6 // 12 // 100 * 100 if required else 0,
               'city': local['city_total'] * 6 // 12 // 100 * 100 if required else 0}
    return {'start': start, 'end': end, 'rows': rows, 'depreciation_total': total_dep,
            'interim_required': required, 'interim': interim}


def compute(user, fy, data, corp, local, consumption, profile=None):
    inputs, bs, pl = data['_inputs'], data['bs'], data['pl']
    assets = [(i, _kind(i, ASSET_KINDS)) for i in inputs['other_current_assets'] + inputs['investments']]
    liabilities = [(i, _kind(i, LIABILITY_KINDS)) for i in inputs['current_liabilities'] + inputs['fixed_liabilities']]

    def pick(pairs, *kinds):
        return [_row(i) for i, k in pairs if k in kinds and i['amount']]

    cash_total = next((i['amount'] for i in bs['current_assets'] if i['label'] == '現金及び預金'), 0)
    rent = [_row(i) for i in inputs['rent_details'] if i['amount']]
    if not rent:
        rent = [{'name': '', 'address': '', 'amount': i['amount'], 'note': i['label'], 'label': i['label'],
                 'registration': '', 'rate': ''} for i in pl['sga_items'] if '地代家賃' in i['label'] or 'rent' in i['label'].lower()]
    interest_rows = [_row(i) for i in inputs['non_operating_income'] if '利息' in i['label'] and i['amount']]
    misc_income = [_row(i) for i in inputs['non_operating_income'] if '利息' not in i['label'] and i['amount']]
    misc_loss = [_row(i) for i in inputs['non_operating_expenses'] if i['amount']]
    inventory = ([{'name': '商品', 'qty': '', 'unit': '', 'amount': inputs['closing_inventory'], 'note': ''}]
                 if inputs['closing_inventory'] else [])

    dep = depreciation_detail(data['_dep_rows'])
    refund_reasons = []
    if consumption['refund_total'] > 0:
        refund_reasons.append('purchase_heavy')
        if fy.term_no <= 2:
            refund_reasons.append('business_start')

    return {
        'deposits': _bank_rows(user, fy, cash_total),
        'receivables': pick(assets, 'receivable'),
        'advances': pick(assets, 'advance'),
        'loans': pick(assets, 'loan'),
        'inventory': inventory,
        'guarantees': pick(assets, 'deposit_paid'),
        'payables': pick(liabilities, 'payable'),
        'deposits_received': pick(liabilities, 'deposit_received'),
        'borrowings': pick(liabilities, 'borrowing'),
        'withholding': _withholding(user, fy),
        'rent': rent, 'interest_income': interest_rows,
        'misc_income': misc_income, 'misc_loss': misc_loss,
        'depreciation': dep,
        'monthly': _monthly(user, fy),
        'top_sales': _top_orders(user, fy, 'sale', 10),
        'top_purchases': _top_orders(user, fy, 'purchase', 5),
        'refund_reasons': refund_reasons,
        'next_year': _next_year(fy, data['_dep_rows'], corp, local),
    }

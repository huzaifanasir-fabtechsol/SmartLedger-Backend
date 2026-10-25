import datetime

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from decimal import Decimal

from apps.account.models import User
from apps.expense.models import Expense, ExpenseCategory
from apps.revenue.models import Order
from apps.reports.models import CompanyProfile, FiscalYear, StatementInput
from apps.reports.pdf.i18n import tr
from apps.reports.pdf.package import UnknownPart, build_package
from apps.reports.services.corporate_tax import corporate_tax_amount
from apps.reports.services.local_tax import _business_tax, due_date
from apps.reports.services.package import compute_package
from apps.reports.tests import SAMPLE_INPUTS, make_sample_year

D = datetime.date
ALL_PARTS = ['kessan', 'shohizei', 'hojinzei', 'schedules', 'chihozei', 'other']
OFFICES = [
    {'prefecture': '愛知県', 'prefecture_office': '知多県税事務所', 'municipality': '大府市', 'employees': 1, 'months': 1,
     'pref_levy': 21000, 'city_levy': 50000},
    {'prefecture': '大阪府', 'prefecture_office': '大阪北河内府税事務所', 'municipality': '寝屋川市', 'employees': 1,
     'months': 11, 'pref_levy': 20000, 'city_levy': 60000},
]


def setup(test):
    test.user = User.objects.create_user(username='u', email='u@example.com', password='x',
                                         company_name='ILYAS SONS 合同会社')
    test.profile = CompanyProfile.objects.create(
        user=test.user, legal_name='ILYAS SONS 合同会社', legal_name_en='ILYAS SONS LLC',
        address='愛知県大府市共栄町二丁目366番', capital=5000000, offices=OFFICES,
        shareholders=[{'name': 'A', 'address': 'x', 'shares': 5000000, 'relationship': 'self'}])
    test.fy = make_sample_year(test.user)


def with_inputs(fy, **changes):
    record = fy.inputs
    record.data = {**SAMPLE_INPUTS, **changes}
    record.save()


class ConsumptionTaxTests(TestCase):
    def setUp(self):
        setup(self)

    def test_matches_filed_return(self):
        c = compute_package(self.user, self.fy)['consumption']
        L = c['lines']
        self.assertEqual(L[1], 28680000)
        self.assertEqual(L[2], 2237040)
        self.assertEqual(L[4], 2669701)
        self.assertEqual(L[8], 432661)
        self.assertEqual(L[19], 122032)
        self.assertEqual(L[26], -554693)
        self.assertEqual(c['refund_total'], 554693)
        self.assertEqual(c['rate_rows']['6.24'][4], 4226)
        self.assertEqual(c['rate_rows']['7.8'][4], 2665475)
        self.assertEqual(c['ratio_pct_floor'], 99.99)
        self.assertTrue(c['full_deduction'])

    def test_low_taxable_ratio_uses_proportional_deduction(self):
        consumption = {**SAMPLE_INPUTS['tax']['consumption'], 'nontaxable_sales': 28680682}
        with_inputs(self.fy, tax={'consumption': consumption})
        c = compute_package(self.user, self.fy)['consumption']
        self.assertFalse(c['full_deduction'])
        self.assertAlmostEqual(c['ratio'], 0.5, places=3)
        self.assertLess(c['lines'][4], 2669701 * 0.51)
        self.assertTrue(c['warnings'])

    def test_payable_when_sales_exceed_purchases(self):
        with_inputs(self.fy, tax={'consumption': {'sales_incl_10': 110000000, 'purchase_incl_10': 11000000,
                                                  'interim_paid': 100000}})
        L = compute_package(self.user, self.fy)['consumption']['lines']
        self.assertEqual(L[1], 100000000)
        self.assertEqual(L[2], 7800000)
        self.assertEqual(L[4], 780000)
        self.assertEqual(L[9], 7020000)
        self.assertEqual(L[11], 6920000)
        self.assertGreater(L[26], 0)


class CorporateTaxTests(TestCase):
    def setUp(self):
        setup(self)

    def test_tax_rates(self):
        self.assertEqual(corporate_tax_amount(0), 0)
        self.assertEqual(corporate_tax_amount(10_000_000), 1_664_000)   # 8m x 15% + 2m x 23.2%

    def test_loss_year_matches_filing(self):
        c = compute_package(self.user, self.fy)['corporate']
        self.assertEqual(c['income'], -6657535)
        self.assertEqual(c['corp_tax'], 0)
        self.assertEqual(c['form7']['prior_total'], 464100)
        self.assertEqual(c['form7']['current_loss'], 6657535)
        self.assertEqual(c['form7']['carry_total'], 7121635)
        self.assertEqual(c['form15'][1], 268420)
        self.assertEqual(c['form15'][5], 0)
        self.assertEqual(c['form4']['taxes_booked'], 229100)
        self.assertTrue(c['form2']['is_family'])

    def test_profit_uses_prior_losses_then_taxes_remainder(self):
        with_inputs(self.fy, sales=36000000)
        c = compute_package(self.user, self.fy)['corporate']
        self.assertGreater(c['income_pre'], 464100)
        self.assertEqual(c['form7']['used_total'], 464100)
        self.assertEqual(c['form7']['carry_total'], 0)
        self.assertEqual(c['income'], c['income_pre'] - 464100)
        self.assertEqual(c['taxable_income'], c['income'] // 1000 * 1000)
        self.assertEqual(c['corp_tax'], c['taxable_income'] * 15 // 100 // 100 * 100)
        self.assertEqual(c['local_tax'], c['corp_tax'] // 1000 * 1000 * 103 // 1000 // 100 * 100)

    def test_excess_entertainment_is_added_back(self):
        corporate = {**SAMPLE_INPUTS['tax']['corporate'], 'entertainment_expenses': 9_000_000}
        with_inputs(self.fy, tax={'corporate': corporate})
        c = compute_package(self.user, self.fy)['corporate']
        self.assertEqual(c['form15'][5], 1_000_000)
        self.assertEqual(c['form4']['entertainment_excess'], 1_000_000)


class LocalTaxTests(TestCase):
    def setUp(self):
        setup(self)

    def test_levies_match_filing(self):
        l = compute_package(self.user, self.fy)['local']
        self.assertEqual(l['pref_levy_total'], 1700 + 18300)
        self.assertEqual(l['city_levy_total'], 4100 + 55000)
        self.assertEqual(l['levy_total'], 79100)
        self.assertEqual(l['due_date'], D(2026, 3, 2))

    def test_no_tax_difference_noted_when_inputs_match(self):
        data = compute_package(self.user, self.fy)
        self.assertEqual(data['corporate']['estimated_taxes'], 79100)
        self.assertFalse(any('differ from' in n[1] for n in data['tax_notes']))

    def test_business_tax_brackets_and_due_date(self):
        self.assertEqual(_business_tax(10_000_000), 492_000)
        self.assertEqual(due_date(D(2025, 12, 31)), D(2026, 3, 2))   # 28 Feb 2026 is a Saturday
        self.assertEqual(due_date(D(2025, 3, 31)), D(2025, 6, 2))    # 31 May 2025 is a Saturday

    def test_default_office_comes_from_address(self):
        self.profile.offices = []
        self.profile.save()
        offices = compute_package(self.user, self.fy)['local']['offices']
        self.assertEqual(len(offices), 1)
        self.assertEqual((offices[0]['prefecture'], offices[0]['municipality']), ('愛知県', '大府市'))


class PackageTests(TestCase):
    def setUp(self):
        setup(self)
        self.data = compute_package(self.user, self.fy)

    @staticmethod
    def pages(pdf):
        return pdf.count(b'/Type /Page\n') + pdf.count(b'/Type /Page ')

    def test_every_language_and_style_renders(self):
        sizes = {}
        for lang in ('ja', 'en'):
            for mode in ('full', 'simple'):
                pdf = build_package(self.data, ALL_PARTS, lang, mode).getvalue()
                self.assertTrue(pdf.startswith(b'%PDF'))
                sizes[(lang, mode)] = self.pages(pdf)
        self.assertGreater(sizes[('en', 'full')], 40)
        self.assertLess(sizes[('en', 'simple')], sizes[('en', 'full')])
        self.assertEqual(sizes[('en', 'full')], sizes[('ja', 'full')])

    def test_each_part_renders_alone(self):
        for part in ALL_PARTS:
            pdf = build_package(self.data, [part], 'en', 'full').getvalue()
            self.assertGreaterEqual(self.pages(pdf), 1, part)

    def test_unknown_part_and_bad_options(self):
        with self.assertRaises(UnknownPart):
            build_package(self.data, ['nope'])
        with self.assertRaises(ValueError):
            build_package(self.data, ['kessan'], 'fr')
        with self.assertRaises(ValueError):
            build_package(self.data, ['kessan'], 'en', 'tiny')

    def test_works_without_any_profile_or_inputs(self):
        other = User.objects.create_user(username='o', email='o@example.com', password='x')
        fy = FiscalYear.objects.create(user=other, term_no=1, start_date=D(2025, 1, 1), end_date=D(2025, 12, 31))
        data = compute_package(other, fy)
        for lang in ('ja', 'en'):
            self.assertTrue(build_package(data, ALL_PARTS, lang, 'full').getvalue().startswith(b'%PDF'))

    def test_translation_helper(self):
        self.assertEqual(tr(('消費税', 'Consumption tax'), 'en'), 'Consumption tax')
        self.assertEqual(tr('現金及び預金', 'en'), 'Cash and deposits')
        self.assertEqual(tr('現金及び預金', 'ja'), '現金及び預金')
        self.assertEqual(tr('Custom label', 'en'), 'Custom label')


class EndpointTests(TestCase):
    def setUp(self):
        setup(self)
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.url = f'/api/reports/fiscal-years/{self.fy.id}/pdf/'

    def test_language_style_and_parts_options(self):
        resp = self.client.get(self.url, {'parts': 'kessan,shohizei', 'lang': 'en', 'mode': 'simple'})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.content.startswith(b'%PDF'))
        self.assertIn('term5_en_simple.pdf', resp['Content-Disposition'])

    def test_rejects_bad_language_or_style(self):
        self.assertEqual(self.client.get(self.url, {'lang': 'fr'}).status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.client.get(self.url, {'mode': 'x'}).status_code, status.HTTP_400_BAD_REQUEST)

    def test_preview_is_json_serialisable_and_has_tax_summary(self):
        resp = self.client.get(f'/api/reports/fiscal-years/{self.fy.id}/preview/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['consumption']['lines'][26], -554693)
        self.assertNotIn('_inputs', resp.data)

    def test_inputs_roundtrip_keeps_tax_settings(self):
        payload = {'data': {**SAMPLE_INPUTS, 'other_current_assets': [
            {'label': '立替金', 'amount': 5, 'kind': 'advance', 'counterparty': 'X'}]}}
        url = f'/api/reports/fiscal-years/{self.fy.id}/inputs/'
        self.assertEqual(self.client.put(url, payload, format='json').status_code, status.HTTP_200_OK)
        got = self.client.get(url).data['data']
        self.assertEqual(got['tax']['consumption']['transitional_incl_10'], 3187439)
        self.assertEqual(got['other_current_assets'][0]['kind'], 'advance')
        bad = self.client.put(url, {'data': {'investments': [{'label': 'x', 'amount': 1, 'kind': 'bogus'}]}},
                              format='json')
        self.assertEqual(bad.status_code, status.HTTP_400_BAD_REQUEST)


class AutoValueTests(TestCase):
    """The auto-values endpoint reports what each field would calculate, ignoring saved overrides."""

    def setUp(self):
        setup(self)
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.url = f'/api/reports/fiscal-years/{self.fy.id}/auto-values/'

    def test_top_level_auto_ignores_saved_override(self):
        Order.objects.create(user=self.user, order_number='S1', transaction_type='sale', transaction_catagory='local',
                             transaction_date=D(2025, 6, 1), total_amount=1000000)
        Order.objects.create(user=self.user, order_number='P1', transaction_type='purchase',
                             transaction_catagory='local', transaction_date=D(2025, 7, 1), total_amount=400000)
        data = self.client.get(self.url).data
        self.assertEqual(SAMPLE_INPUTS['sales'], 28680691)          # the saved override is different
        self.assertEqual(data['sales'], 1000000)
        self.assertEqual(data['purchases'], 400000)
        self.assertEqual(data['details']['sales'], [['Sale orders in the period', 1000000]])

    def test_consumption_auto_builds_on_the_users_sales_and_shows_its_parts(self):
        category = ExpenseCategory.objects.create(name='fuel', user=self.user)
        Expense.objects.create(user=self.user, title='gas', amount=1000, tax_amount=Decimal('100'),
                               tax_percent_used=Decimal('10'), date=D(2025, 3, 3), category=category)
        data = self.client.get(self.url).data
        c = data['consumption']
        self.assertEqual(c['sales_incl_10'], round(28680691 * 1.10))       # from the user's sales figure
        self.assertEqual(c['nontaxable_sales'], 6)
        parts = dict(data['details']['consumption.purchase_incl_10'])
        self.assertEqual(parts['Expenses carrying 10% tax'], 1100)
        self.assertEqual(c['purchase_incl_10'], sum(parts.values()))
        self.assertNotEqual(c['purchase_incl_10'], SAMPLE_INPUTS['tax']['consumption']['purchase_incl_10'])

    def test_corporate_auto_values(self):
        data = self.client.get(self.url).data
        self.assertEqual(data['corporate']['entertainment_expenses'], 268420)
        self.assertEqual(data['corporate']['unpaid_pref'], 20000)
        self.assertEqual(data['corporate']['unpaid_city'], 59100)
        self.assertEqual(data['corporate']['unpaid_corporate'], 0)

    def test_requires_ownership(self):
        other = User.objects.create_user(username='o', email='o@example.com', password='x')
        fy = FiscalYear.objects.create(user=other, term_no=1, start_date=D(2025, 1, 1), end_date=D(2025, 12, 31))
        self.assertEqual(self.client.get(f'/api/reports/fiscal-years/{fy.id}/auto-values/').status_code, 404)


class RollForwardTests(TestCase):
    """Starting the next term must carry closing balances so the new balance sheet can reconcile."""

    def setUp(self):
        setup(self)
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.url = f'/api/reports/fiscal-years/{self.fy.id}/roll-forward/'

    def test_carries_balances_assets_and_losses(self):
        resp = self.client.post(self.url)
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        new_fy = FiscalYear.objects.get(id=resp.data['id'])
        self.assertEqual((new_fy.term_no, new_fy.start_date, new_fy.end_date), (6, D(2026, 1, 1), D(2026, 12, 31)))
        data = new_fy.inputs.data
        self.assertEqual(data['capital'], 5000000)
        self.assertEqual(data['opening_retained_earnings'], -10950735)
        self.assertEqual(data['opening_inventory'], 2377190)
        self.assertEqual(sum(i['amount'] for i in data['current_liabilities']), 10834858)
        self.assertEqual(sum(i['amount'] for i in data['tax']['corporate']['prior_losses']), 7121635)
        self.assertEqual(data['tax']['corporate']['opening_provision'], 204100)
        self.assertEqual(data['sales'], None)                         # flows are not carried
        self.assertEqual(data['extra_sga'], [])
        assets = {a.name: a.opening_book_value for a in new_fy.fixed_assets.all()}
        self.assertEqual(assets['簡易建物'], 704031)
        self.assertEqual(assets['iPhone'], 58842)
        self.assertEqual(assets['創立費'], 184700)

    def test_new_term_balances_once_cash_and_inventory_are_entered(self):
        new_fy = FiscalYear.objects.get(id=self.client.post(self.url).data['id'])
        record = new_fy.inputs
        record.data = {**record.data, 'cash': 84973, 'closing_inventory': 2377190, 'sales': 0, 'purchases': 0}
        record.save()
        data = compute_package(self.user, new_fy)
        self.assertTrue(data['bs']['balanced'], data['bs']['difference'])
        self.assertEqual(data['pl']['cost_of_sales'], 0)
        self.assertEqual(data['bs']['equity_total'], -5950735 - data['pl']['sga_total'])

    def test_second_roll_forward_and_foreign_year_rejected(self):
        self.assertEqual(self.client.post(self.url).status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.client.post(self.url).status_code, status.HTTP_400_BAD_REQUEST)
        other = User.objects.create_user(username='o', email='o@example.com', password='x')
        fy = FiscalYear.objects.create(user=other, term_no=1, start_date=D(2025, 1, 1), end_date=D(2025, 12, 31))
        self.assertEqual(self.client.post(f'/api/reports/fiscal-years/{fy.id}/roll-forward/').status_code, 404)


class ReconciliationWarningTests(TestCase):
    def setUp(self):
        setup(self)

    def test_unseeded_later_term_is_flagged_and_the_pdf_is_marked_draft(self):
        fy = FiscalYear.objects.create(user=self.user, term_no=6, start_date=D(2026, 1, 1), end_date=D(2026, 12, 31))
        StatementInput.objects.create(fiscal_year=fy, data={'cash': 1066214, 'sales': 0, 'purchases': 496430})
        data = compute_package(self.user, fy)
        text = ' '.join(w[1] for w in data['warnings'])
        self.assertIn('Capital and opening retained earnings are both 0', text)
        self.assertIn('closing inventory is 0', text)
        self.assertIn('does not balance', text)
        self.assertFalse(data['bs']['balanced'])
        # still renders, with the draft banner drawn (smoke): the unbalanced data must not break the writer
        self.assertTrue(build_package(data, ['kessan'], 'en', 'full').getvalue().startswith(b'%PDF'))

    def test_reconciled_filing_year_has_no_warnings(self):
        data = compute_package(self.user, self.fy)
        self.assertEqual(data['warnings'], [])


class CashAccountSelectionTests(TestCase):
    """Only the bank accounts that are on the company's books should count as cash."""

    def setUp(self):
        setup(self)
        from apps.revenue.models import CompanyAccount, Transaction
        self.company_acct = CompanyAccount.objects.create(user=self.user, bank_name='GMO', account_number='1',
                                                          branch_code='1', account_holder='co')
        self.other_acct = CompanyAccount.objects.create(user=self.user, bank_name='Personal', account_number='2',
                                                        branch_code='1', account_holder='me')
        Transaction.objects.create(user=self.user, company_account=self.company_acct, date=D(2025, 12, 29),
                                   balance=84973, description='t')
        Transaction.objects.create(user=self.user, company_account=self.other_acct, date=D(2025, 12, 30),
                                   balance=469176, description='t')
        record = self.fy.inputs
        record.data = {k: v for k, v in SAMPLE_INPUTS.items() if k != 'cash'}
        record.save()
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def cash(self):
        return compute_package(self.user, self.fy)['bs']['current_assets'][0]['amount']

    def test_all_accounts_count_by_default(self):
        self.assertEqual(self.cash(), 84973 + 469176)

    def test_selection_limits_cash_and_the_deposit_schedule(self):
        record = self.fy.inputs
        record.data = {**record.data, 'cash_accounts': [self.company_acct.id]}
        record.save()
        data = compute_package(self.user, self.fy)
        self.assertEqual(self.cash(), 84973)
        self.assertEqual([d['amount'] for d in data['schedules']['deposits']], [84973])
        self.assertTrue(data['bs']['balanced'])          # matches the filed balance sheet

    def test_auto_values_list_accounts_and_ignore_nothing_else(self):
        record = self.fy.inputs
        record.data = {**record.data, 'cash_accounts': [self.company_acct.id]}
        record.save()
        data = self.client.get(f'/api/reports/fiscal-years/{self.fy.id}/auto-values/').data
        by_id = {a['id']: a for a in data['accounts']}
        self.assertEqual(by_id[self.company_acct.id]['balance'], 84973)
        self.assertTrue(by_id[self.company_acct.id]['selected'])
        self.assertFalse(by_id[self.other_acct.id]['selected'])
        self.assertEqual(data['cash'], 84973)

    def test_invalid_selection_rejected(self):
        resp = self.client.put(f'/api/reports/fiscal-years/{self.fy.id}/inputs/',
                               {'data': {'cash_accounts': ['x']}}, format='json')
        self.assertEqual(resp.status_code, 400)


class ReadinessTests(TestCase):
    def setUp(self):
        setup(self)

    def statuses(self, fy):
        return {i['key']: i['status'] for i in compute_package(self.user, fy)['readiness']}

    def test_filing_year_is_mostly_ready(self):
        s = self.statuses(self.fy)
        for key in ('opening', 'inventory', 'assets', 'consumption', 'balance', 'period', 'sales'):
            self.assertIn(s[key], ('ok', 'check'), key)
        self.assertEqual(s['balance'], 'ok')
        self.assertEqual(s['consumption'], 'ok')           # purchase totals were entered
        self.assertEqual(s['opening'], 'ok')
        self.assertEqual(s['company'], 'todo')              # no tax office / corporate number in the fixture

    def test_unseeded_year_lists_what_to_fix(self):
        fy = FiscalYear.objects.create(user=self.user, term_no=6, start_date=D(2026, 1, 19), end_date=D(2026, 10, 19))
        StatementInput.objects.create(fiscal_year=fy, data={'purchases': 500000})
        items = {i['key']: i for i in compute_package(self.user, fy)['readiness']}
        self.assertEqual(items['opening']['status'], 'todo')
        self.assertEqual(items['opening']['tab'], 'year')
        self.assertEqual(items['inventory']['status'], 'todo')
        self.assertEqual(items['period']['status'], 'check')
        self.assertEqual(items['balance']['status'], 'todo')
        self.assertEqual(items['consumption']['status'], 'todo')

    def test_readiness_is_in_the_preview_api(self):
        client = APIClient()
        client.force_authenticate(user=self.user)
        resp = client.get(f'/api/reports/fiscal-years/{self.fy.id}/preview/')
        self.assertEqual(resp.status_code, 200)
        keys = [i['key'] for i in resp.data['readiness']]
        self.assertEqual(keys[:3], ['company', 'period', 'opening'])
        self.assertEqual(len(keys), 14)
        self.assertIn('carried', keys)           # a term after the first carries last year's balances


class UnsoldCarsTests(TestCase):
    """Reference list of cars bought but not (yet) recorded as sold."""

    def setUp(self):
        setup(self)
        from apps.revenue.models import Car, CarCategory, OrderItem
        category = CarCategory.objects.create(user=self.user, company='TOYOTA', model='Roomy')
        self.stock = Car.objects.create(user=self.user, category=category, chassis_number='A1', year=2020)
        self.sold = Car.objects.create(user=self.user, category=category, chassis_number='B2', year=2021)
        self.later = Car.objects.create(user=self.user, category=category, chassis_number='C3', year=2022)

        def order(number, kind, day):
            return Order.objects.create(user=self.user, order_number=number, transaction_type=kind,
                                        transaction_catagory='local', transaction_date=day, total_amount=1)
        buy_stock, buy_sold = order('P1', 'purchase', D(2025, 3, 1)), order('P2', 'purchase', D(2025, 4, 1))
        sell = order('S1', 'sale', D(2025, 9, 1))
        buy_later, sell_later = order('P3', 'purchase', D(2025, 6, 1)), order('S2', 'sale', D(2026, 2, 1))
        OrderItem.objects.create(order=buy_stock, car=self.stock, vehicle_price=430000, successful_bid=13000,
                                 subtotal=496430)
        OrderItem.objects.create(order=buy_sold, car=self.sold, vehicle_price=500000, subtotal=550000)
        OrderItem.objects.create(order=sell, car=self.sold, vehicle_price=700000, subtotal=770000)
        OrderItem.objects.create(order=buy_later, car=self.later, vehicle_price=300000, subtotal=330000)
        OrderItem.objects.create(order=sell_later, car=self.later, vehicle_price=400000, subtotal=440000)
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_lists_only_cars_without_a_sale_by_period_end(self):
        cars = self.client.get(f'/api/reports/fiscal-years/{self.fy.id}/auto-values/').data['unsold_cars']
        by_chassis = {c['chassis']: c for c in cars}
        self.assertEqual(set(by_chassis), {'A1', 'C3'})     # B2 sold in 2025; C3 sold only in 2026
        self.assertEqual(by_chassis['A1']['cost_excl_tax'], 443000)
        from apps.revenue.models import OrderItem
        stored = OrderItem.objects.get(car=self.stock).subtotal      # the model computes the subtotal itself
        self.assertEqual(by_chassis['A1']['invoice_total'], int(stored))
        self.assertEqual(by_chassis['A1']['name'], 'TOYOTA Roomy')

    def test_reference_only_never_changes_the_statements(self):
        before = compute_package(self.user, self.fy)['pl']['closing_inventory']
        self.client.get(f'/api/reports/fiscal-years/{self.fy.id}/auto-values/')
        self.assertEqual(compute_package(self.user, self.fy)['pl']['closing_inventory'], before)

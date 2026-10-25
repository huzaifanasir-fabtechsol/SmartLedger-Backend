from django.test import TestCase

from apps.account.models import User
from apps.reports.filed_history import TERMS, load
from apps.reports.models import FiscalYear
from apps.reports.services.package import compute_package


class FiledHistoryTests(TestCase):
    """Each loaded term must reproduce the figures printed on the filed returns."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username='u', email='u@example.com', password='x')
        load(cls.user, log=lambda *_: None)

    def package(self, term_no):
        return compute_package(self.user, FiscalYear.objects.get(user=self.user, term_no=term_no))

    def test_every_filed_term_matches_its_return(self):
        for term in TERMS:
            data = self.package(term['term_no'])
            exp, corp, local = term['expect'], data['corporate'], data['local']
            ctx = f"term {term['term_no']}"
            self.assertTrue(data['bs']['balanced'], f"{ctx}: balance sheet off by {data['bs']['difference']}")
            self.assertEqual(data['bs']['assets_total'], exp['assets_total'], ctx)
            self.assertEqual(data['pl']['net_income'], exp['net_income'], ctx)
            self.assertEqual(corp['income'], exp['income'], ctx)
            self.assertEqual(corp['corp_tax'], 0, ctx)
            self.assertEqual(local['levy_total'], exp['levy_total'], ctx)
            self.assertEqual(corp['form7']['carry_total'], exp.get('carry_total', 0), ctx)
            unpaid = corp['form5_1']['unpaid']
            self.assertEqual(unpaid['pref'], exp.get('unpaid_pref', 0), ctx)
            self.assertEqual(unpaid['city'], exp.get('unpaid_city', 0), ctx)
            self.assertEqual(data['consumption']['refund_total'], exp.get('consumption_refund', 0), ctx)

    def test_schedule_5_1_ties_out_in_2025(self):
        f = self.package(5)['corporate']['form5_1']
        rows = {r[0]: r for r in f['rows']}
        self.assertEqual(rows[29][2:], (-40_000, 0, -20_000, -60_000))          # 未納道府県民税
        self.assertEqual(rows[30][2:], (-110_000, -25_000, -59_100, -144_100))   # 未納市町村民税
        self.assertEqual(rows[26][2:], (0, 25_000, 229_100, 204_100))            # 納税充当金
        self.assertEqual(f['difference'], 0)

    def test_2024_and_2023_unpaid_levies_accumulate(self):
        rows = {r[0]: r for r in self.package(4)['corporate']['form5_1']['rows']}
        self.assertEqual(rows[29][2:], (-20_000, 0, -20_000, -40_000))
        self.assertEqual(rows[30][2:], (-50_000, 0, -60_000, -110_000))

    def test_closed_terms_ignore_app_expenses(self):
        from apps.expense.models import Expense
        import datetime
        Expense.objects.create(user=self.user, amount=500_000, date=datetime.date(2023, 5, 1), description='stray')
        self.assertEqual(self.package(3)['pl']['sga_total'], 3_136_500)

    def test_term_6_opens_with_the_closing_balances(self):
        fy = FiscalYear.objects.get(user=self.user, term_no=6)
        self.assertEqual((str(fy.start_date), str(fy.end_date)), ('2026-01-01', '2026-12-31'))
        data = self.package(6)
        inputs = data['_inputs']
        self.assertEqual(inputs['capital'], 5_000_000)
        self.assertEqual(inputs['opening_retained_earnings'], -10_950_735)
        self.assertEqual(inputs['opening_inventory'], 2_377_190)
        self.assertTrue(inputs['app_expenses'])
        corp = inputs['tax']['corporate']
        self.assertEqual(sum(l['amount'] for l in corp['prior_losses']), 7_121_635)
        self.assertEqual((corp['opening_unpaid_pref'], corp['opening_unpaid_city']), (60_000, 144_100))
        self.assertEqual(corp['opening_provision'], 204_100)
        labels = [i['label'] for i in inputs['other_current_assets']]
        self.assertNotIn('未収還付法人税等', labels)             # refunded on 2026-04-10
        self.assertIn('役員貸付金', labels)
        self.assertEqual(sorted(a.name for a in fy.fixed_assets.all()),
                         sorted(['簡易建物', 'iPhone', 'パソコン (ASUS M3604YA)', 'エアコン', '創立費', '開業費']))

    def test_loading_twice_is_harmless(self):
        again = load(self.user, log=lambda *_: None)
        self.assertEqual(again, [])
        self.assertEqual(FiscalYear.objects.filter(user=self.user).count(), 6)


class ExpenseAccountTests(TestCase):
    def test_categories_are_reported_under_standard_accounts(self):
        import datetime
        from apps.expense.models import Expense, ExpenseCategory
        from apps.reports.models import StatementInput
        from apps.reports.services.statements import account_for, compute_statements

        user = User.objects.create_user(username='a', email='a@example.com', password='x')
        fy = FiscalYear.objects.create(user=user, term_no=1, start_date=datetime.date(2026, 1, 1),
                                       end_date=datetime.date(2026, 12, 31))
        StatementInput.objects.create(fiscal_year=fy, data={})
        for name, amount in [('FOOD', 1000), ('FAMILY MART', 500), ('RENT 家賃', 7000), ('SHESHA FALVOUR', 300),
                             ('消耗品費', 40)]:
            cat = ExpenseCategory.objects.create(user=user, name=name)
            Expense.objects.create(user=user, title='x', amount=amount, date=datetime.date(2026, 3, 1), category=cat)
        items = {i['label']: i['amount'] for i in compute_statements(user, fy)['pl']['sga_items']}
        self.assertEqual(items, {'会議費': 1500, '地代家賃': 7000, '雑費': 300, '消耗品費': 40})
        fy.inputs.data = {'category_accounts': {'FOOD': '接待交際費', 'SHESHA FALVOUR': '消耗品費'}}
        fy.inputs.save()
        items = {i['label']: i['amount'] for i in compute_statements(user, fy)['pl']['sga_items']}
        self.assertEqual(items, {'接待交際費': 1000, '会議費': 500, '地代家賃': 7000, '消耗品費': 340})
        self.assertEqual(account_for('', None), '雑費')

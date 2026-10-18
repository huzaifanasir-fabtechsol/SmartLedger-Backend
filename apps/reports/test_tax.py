import datetime

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.account.models import User
from apps.reports.models import CompanyProfile, FiscalYear
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
        self.assertFalse(any('計算上の法人税等' in n for n in data['tax_notes']))

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

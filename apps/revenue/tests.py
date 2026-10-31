from datetime import date
from decimal import Decimal
from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from openpyxl import Workbook
from rest_framework.test import APIClient

from apps.account.models import User
from apps.expense.models import Expense, ExpenseCategory
from apps.revenue.models import Auction, Car, CarCategory, CompanyAccount, Order, OrderItem, Transaction

URL = '/api/revenue/orders/dashboard/'


class DashboardTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='owner', email='owner@example.com', password='x')
        self.other = User.objects.create_user(username='other', email='other@example.com', password='x')
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        category = CarCategory.objects.create(company='Toyota', model='Aqua', user=self.user)
        self.car = Car.objects.create(category=category, chassis_number='C-1', year=2020, user=self.user)
        self.n = 0

    def order(self, kind, total, status='completed', day=date(2026, 3, 10), user=None, tax=0):
        self.n += 1
        order = Order.objects.create(
            user=user or self.user, order_number=f'ORD-{self.n}', transaction_type=kind,
            transaction_catagory='local', transaction_date=day, total_amount=Decimal(total),
            payment_status=status,
        )
        OrderItem.objects.create(order=order, car=self.car, vehicle_price_tax=Decimal(tax),
                                 transport_fee_tax=Decimal(tax))
        return order

    def expense(self, amount, tax=None, percent=None, day=date(2026, 3, 12), user=None, title='Item'):
        return Expense.objects.create(
            user=user or self.user, title=title, amount=Decimal(amount), date=day,
            tax_amount=None if tax is None else Decimal(tax),
            tax_percent_used=None if percent is None else Decimal(percent),
        )

    def get(self, **params):
        response = self.client.get(URL, params)
        self.assertEqual(response.status_code, 200)
        return response.json()

    def test_purchases_are_a_cost_and_failed_invoices_are_ignored(self):
        self.order('sale', '1000')
        self.order('nagare', '500')
        self.order('sale', '300', status='pending')
        self.order('sale', '9999', status='failed')
        self.order('purchase', '400')
        self.order('purchase', '200', status='pending')
        self.order('purchase', '7777', status='failed')
        self.expense('100')

        data = self.get()

        self.assertEqual(data['approved_amount'], 1500)
        self.assertEqual(data['pending_amount'], 300)
        self.assertEqual(data['total_purchase'], 600)
        self.assertEqual(data['invoice_total'], 2400)
        self.assertEqual(data['invoice_count'], 5)
        # revenue 1500 - completed purchases 400 - expenses 100
        self.assertEqual(data['net_profit'], 1000)

    def test_expense_totals_split_tax_out(self):
        self.expense('1000', tax='100')
        self.expense('500', tax='0')
        self.expense('200')                      # no tax at all
        self.expense('300', percent='8')         # older row: only a rate -> 24
        self.expense('50', tax='5', user=self.other)

        data = self.get()

        self.assertEqual(data['total_expense'], 2000)
        self.assertEqual(data['expense_tax'], 124)
        self.assertEqual(data['expense_total_with_tax'], 2124)
        self.assertEqual(data['expense_count'], 4)

    def test_invoice_tax_adds_up_every_tax_column(self):
        self.order('sale', '1000', tax='30')
        self.order('purchase', '500', tax='20', status='pending')
        self.order('sale', '800', tax='99', status='failed')
        self.order('sale', '800', tax='99', user=self.other)

        # each item carries the tax twice (vehicle + transport): (30 + 20) * 2
        self.assertEqual(self.get()['invoice_tax'], 100)

    def test_latest_expenses_are_the_newest_ten_with_their_tax(self):
        for i in range(12):
            self.expense('100', tax='10', day=date(2026, 1, i + 1), title=f'E{i}')
        self.expense('300', percent='10', day=date(2026, 2, 1), title='Newest')

        rows = self.get()['latest_expenses']

        self.assertEqual(len(rows), 10)
        self.assertEqual(rows[0]['title'], 'Newest')
        self.assertEqual(rows[0]['tax_amount'], 30)
        self.assertEqual(rows[0]['total_amount'], 330)
        self.assertEqual(rows[1]['title'], 'E11')
        self.assertEqual(rows[1]['category_name'], '')

    def test_category_name_and_filters(self):
        cat = ExpenseCategory.objects.create(name='Fuel', user=self.user)
        Expense.objects.create(user=self.user, title='Gas', amount=Decimal('100'), date=date(2026, 3, 1),
                               category=cat, tax_amount=Decimal('10'))
        self.expense('400', tax='40', day=date(2025, 3, 1))
        self.expense('50', tax='5', day=date(2026, 4, 1))

        data = self.get(year='2026', month='3')

        self.assertEqual(data['total_expense'], 100)
        self.assertEqual(data['expense_tax'], 10)
        self.assertEqual([e['category_name'] for e in data['latest_expenses']], ['Fuel'])

    def test_chart_matches_the_cards(self):
        self.order('sale', '1000')
        self.order('purchase', '400')
        self.expense('100')

        march = self.get(year='2026')['monthly_chart'][2]

        self.assertEqual((march['rev'], march['exp'], march['profit']), (1000, 500, 500))

    def test_empty_account(self):
        data = self.get()
        for key in ('approved_amount', 'pending_amount', 'total_expense', 'expense_tax', 'invoice_tax',
                    'invoice_total', 'net_profit', 'total_purchase'):
            self.assertEqual(data[key], 0, key)
        self.assertEqual(data['latest_expenses'], [])


class AuctionTypeTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='au', email='au@example.com', password='x')
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_crud_filter_and_types(self):
        res = self.client.post('/api/revenue/auctions/', {'name': 'USS Tokyo', 'auction_type': '  USS '}, format='json')
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.json()['auction_type'], 'USS')
        taa = self.client.post('/api/revenue/auctions/', {'name': 'TAA Kansai', 'auction_type': 'TAA'}, format='json').json()
        self.client.post('/api/revenue/auctions/', {'name': 'Untyped'}, format='json')
        other = User.objects.create_user(username='o', email='o@example.com', password='x')
        Auction.objects.create(user=other, name='Theirs', auction_type='Secret')

        res = self.client.patch(f"/api/revenue/auctions/{taa['id']}/", {'auction_type': 'Online'}, format='json')
        self.assertEqual(res.json()['auction_type'], 'Online')

        names = [a['name'] for a in self.client.get('/api/revenue/auctions/?auction_type=uss').json()['results']]
        self.assertEqual(names, ['USS Tokyo'])
        self.assertEqual(self.client.get('/api/revenue/auctions/?search=online').json()['count'], 1)
        self.assertEqual(self.client.get('/api/revenue/auctions/types/').json(), ['Online', 'USS'])


class TransactionBalanceTests(TestCase):
    """The balance is whatever the user enters; the backend never recalculates it."""
    URL = '/api/revenue/transactions/'

    def setUp(self):
        self.user = User.objects.create_user(username='owner', email='owner@example.com', password='x')
        self.account = CompanyAccount.objects.create(
            user=self.user, bank_name='Bank', account_number='1', branch_code='1', account_holder='Owner'
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def create(self, **fields):
        data = {'date': '2026-01-10', 'withdraw': 0, 'deposit': 1000, 'balance': 5000,
                'description': 'd', 'company_account': self.account.id, **fields}
        return self.client.post(self.URL, data, format='json')

    def test_balance_is_required(self):
        response = self.create(balance=None)
        self.assertEqual(response.status_code, 400)
        self.assertIn('balance', response.data)

    def test_crud_keeps_the_entered_balances(self):
        later = self.create(date='2026-01-20', balance=7777)
        self.assertEqual(later.status_code, 201, later.data)
        earlier = self.create(date='2026-01-05', deposit=300, balance=-250.5)
        self.assertEqual(earlier.status_code, 201, earlier.data)
        self.assertEqual(Decimal(earlier.data['balance']), Decimal('-250.50'))

        response = self.client.patch(f"{self.URL}{earlier.data['id']}/", {'deposit': 900, 'balance': 1234}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(Decimal(response.data['balance']), Decimal('1234.00'))

        self.assertEqual(self.client.delete(f"{self.URL}{earlier.data['id']}/").status_code, 204)
        self.assertEqual(Transaction.objects.get(pk=later.data['id']).balance, Decimal('7777.00'))

    def upload(self, headers, rows):
        wb = Workbook()
        ws = wb.active
        ws.append(headers)
        for row in rows:
            ws.append(row)
        buffer = BytesIO()
        wb.save(buffer)
        return self.client.post(self.URL + 'bulk_upload/', {
            'file': SimpleUploadedFile('tx.xlsx', buffer.getvalue()),
            'company_account': self.account.id,
        }, format='multipart')

    def test_bulk_upload_requires_the_balance_column(self):
        response = self.upload(['date', 'withdraw amount', 'deposit amount', 'description'],
                               [['2026-01-10', 100, None, 'x']])
        self.assertEqual(response.status_code, 400)
        self.assertIn('balance', response.data['error'])
        self.assertEqual(Transaction.objects.count(), 0)

    def test_bulk_upload_rejects_rows_without_a_balance(self):
        response = self.upload(['date', 'withdraw amount', 'deposit amount', 'balance', 'description'],
                               [['2026-01-10', 100, None, 900, 'ok'], ['2026-01-11', 100, None, None, 'x'],
                                ['2026-01-12', 100, None, 'abc', 'y']])
        self.assertEqual(response.status_code, 400)
        self.assertEqual([e.split(':')[0] for e in response.data['row_errors']], ['Row 3', 'Row 4'])
        self.assertEqual(Transaction.objects.count(), 0)

    def test_bulk_upload_stores_the_file_balances(self):
        Transaction.objects.create(user=self.user, company_account=self.account, date=date(2026, 1, 1),
                                   deposit=10000, balance=10000, description='Opening')
        response = self.upload(['date', 'transection id', 'withdraw amount', 'depostie amount', 'balance', 'description'],
                               [['2026-01-10', 'T1', 100, None, '1,234', 'a'], ['2026-01-11', 'T2', None, 50, -20.25, 'b']])
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(list(Transaction.objects.order_by('date').values_list('balance', flat=True)),
                         [Decimal('10000.00'), Decimal('1234.00'), Decimal('-20.25')])

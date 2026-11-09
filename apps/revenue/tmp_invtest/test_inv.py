from django.test import TestCase
from rest_framework.test import APIClient
from apps.account.models import User
from apps.revenue.models import Order

class InvoiceTest(TestCase):
    def test_invoice(self):
        u = User.objects.create_user(username='a', email='a@b.com', password='x', company_name='Test Co')
        fields = {f.name for f in Order._meta.fields}
        o = Order.objects.create(user=u, order_number='INV1', transaction_date='2026-01-01', total_amount=1000)
        c = APIClient(); c.force_authenticate(u)
        r = c.get(f'/api/revenue/orders/{o.id}/generate_invoice/')
        print(r.status_code, r.get('Content-Type'))

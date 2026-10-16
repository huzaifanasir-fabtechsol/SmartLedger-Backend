from rest_framework.test import APITestCase

from apps.account.models import Letterhead, User


class LetterheadApiTests(APITestCase):
    url = '/api/account/letterheads/'

    def setUp(self):
        self.user = User.objects.create_user(username='a', email='a@example.com', password='pw-12345!')
        self.other = User.objects.create_user(username='b', email='b@example.com', password='pw-12345!')
        self.client.force_authenticate(self.user)

    def test_requires_login(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get(self.url).status_code, 401)

    def test_create_update_delete(self):
        res = self.client.post(self.url, {'name': ' Safeer Motors ', 'template': 'wave', 'color1': '#112233'}, format='json')
        self.assertEqual(res.status_code, 201, res.content)
        self.assertEqual(res.data['name'], 'Safeer Motors')
        item = f"{self.url}{res.data['id']}/"
        res = self.client.patch(item, {'color2': '#abcdef', 'tagline': 'Group'}, format='json')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(Letterhead.objects.get().color2, '#abcdef')
        self.assertEqual(self.client.delete(item).status_code, 204)
        self.assertEqual(Letterhead.objects.count(), 0)

    def test_only_own_records_visible(self):
        Letterhead.objects.create(user=self.other, name='Theirs')
        mine = Letterhead.objects.create(user=self.user, name='Mine')
        res = self.client.get(self.url)
        results = res.data['results'] if isinstance(res.data, dict) else res.data
        self.assertEqual([r['id'] for r in results], [mine.id])
        theirs = Letterhead.objects.get(name='Theirs')
        self.assertEqual(self.client.delete(f'{self.url}{theirs.id}/').status_code, 404)

    def test_validation(self):
        bad = [
            {'name': '   '},
            {'name': 'X', 'color1': 'red'},
            {'name': 'X', 'template': 'nope'},
            {'name': 'X', 'logo': 'http://evil/x.png'},
        ]
        for payload in bad:
            self.assertEqual(self.client.post(self.url, payload, format='json').status_code, 400, payload)

    def test_export_docx_from_payload(self):
        """Test exporting letterhead as editable docx directly from JSON payload."""
        import docx
        import io

        payload = {
            'companyName': 'ILYAS SONS 合同会社',
            'tagline': 'Automotive Group',
            'address': 'Tokyo, Japan',
            'phone': '+81 90-1234-5678',
            'email': 'contact@ilyassons.jp',
            'template': 'angles',
            'color1': '#1e3a8a',
            'color2': '#3b82f6',
            'showDate': True,
        }
        res = self.client.post(f"{self.url}export-docx/", payload, format='json')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(
            res['Content-Type'],
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )
        self.assertIn('.docx', res['Content-Disposition'])

        # Verify it is a valid Word document
        doc = docx.Document(io.BytesIO(res.content))
        self.assertTrue(len(doc.paragraphs) > 0)
        found_name = any('ILYAS SONS' in p.text for p in doc.paragraphs)
        self.assertTrue(found_name)

    def test_export_docx_from_saved(self):
        """Test exporting saved letterhead by ID as editable docx."""
        lh = Letterhead.objects.create(
            user=self.user,
            name='My Saved Letterhead',
            tagline='Corporate Group',
            address='Osaka, Japan',
            color1='#0f172a',
            color2='#10b981'
        )
        res = self.client.get(f"{self.url}{lh.id}/export-docx/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(
            res['Content-Type'],
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )
        self.assertIn('My_Saved_Letterhead', res['Content-Disposition'])

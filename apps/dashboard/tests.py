import hmac
import hashlib
import decimal
import json
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.conf import settings
from apps.dashboard.models import Wallet, Transaction, Notification

class DashboardTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='tester', email='tester@example.com', password='password123')
        self.wallet = self.user.wallet
        self.wallet.set_pin('1234')
        self.wallet.credit_balance(decimal.Decimal('1000.00'))
        
        self.client = Client()
        self.client.force_login(self.user)

    def test_wallet_balance_operations(self):
        """Test safe debiting and crediting balance methods."""
        # Success debit
        self.wallet.deduct_balance(decimal.Decimal('200.00'), pin_provided='1234')
        self.assertEqual(self.wallet.balance, decimal.Decimal('800.00'))

        # Incorrect PIN debit failure
        with self.assertRaises(ValueError):
            self.wallet.deduct_balance(decimal.Decimal('100.00'), pin_provided='9999')

        # Insufficient balance debit failure
        with self.assertRaises(ValueError):
            self.wallet.deduct_balance(decimal.Decimal('5000.00'), pin_provided='1234')

        # Credit balance
        self.wallet.credit_balance(decimal.Decimal('500.00'))
        self.assertEqual(self.wallet.balance, decimal.Decimal('1300.00'))

    def test_drf_purchase_endpoint(self):
        """Test REST API endpoint for VTU purchases."""
        url = reverse('api_vtu_purchase')
        payload = {
            "service": "airtime",
            "phone": "08012345678",
            "network": "MTN",
            "amount": "100.00",
            "pin": "1234"
        }
        response = self.client.post(url, data=json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 202)  # Accepted
        
        # Verify transaction record was created in database
        self.assertTrue(Transaction.objects.filter(user=self.user, type='purchase', status='pending').exists())
        # Verify amount was debited
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, decimal.Decimal('1200.00'))  # 1300 initially inside test context if run sequentially, wait, test is isolated! So 1000 - 100 = 900.
        self.assertEqual(self.wallet.balance, decimal.Decimal('900.00'))

    def test_paystack_webhook_signature_verification(self):
        """Test Paystack webhook signature validation and credit action."""
        url = reverse('webhook_paystack')
        payload = {
            "event": "charge.success",
            "data": {
                "reference": "PAY-REF-10023",
                "amount": 250000,  # 2500.00 NGN in Kobo
                "customer": {
                    "email": "tester@example.com"
                }
            }
        }
        raw_body = json.dumps(payload).encode('utf-8')
        secret_key = getattr(settings, 'PAYSTACK_SECRET_KEY', 'paystack_mock_secret_key')
        sig = hmac.new(secret_key.encode('utf-8'), raw_body, hashlib.sha512).hexdigest()

        # Send request with invalid signature
        response = self.client.post(url, data=raw_body, content_type='application/json', HTTP_X_PAYSTACK_SIGNATURE='invalid')
        self.assertEqual(response.status_code, 400)

        # Send request with valid signature
        response = self.client.post(url, data=raw_body, content_type='application/json', HTTP_X_PAYSTACK_SIGNATURE=sig)
        self.assertEqual(response.status_code, 200)

        # Verify wallet balance credited (1000 + 2500 = 3500)
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, decimal.Decimal('3500.00'))
        # Cashback (1% of 2500 = 25)
        self.assertEqual(self.wallet.cashback_balance, decimal.Decimal('25.00'))

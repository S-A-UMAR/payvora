from django.test import TestCase
from django.contrib.auth.models import User
from apps.auth.models import Profile, generate_referral_code

class AuthTestCase(TestCase):
    def setUp(self):
        self.user_a = User.objects.create_user(username='usera', email='usera@example.com', password='password123')

    def test_profile_creation_signal(self):
        """Verify profile and referral code are automatically created."""
        self.assertTrue(hasattr(self.user_a, 'profile'))
        self.assertIsNotNone(self.user_a.profile.referral_code)
        self.assertTrue(self.user_a.profile.referral_code.startswith('PV-'))

    def test_referral_assignment(self):
        """Verify referral mapping works correctly when user registers with code."""
        ref_code = self.user_a.profile.referral_code
        
        # User B registers with User A's referral code
        user_b = User.objects.create_user(username='userb', email='userb@example.com', password='password123')
        user_b.profile.phone = '08012345678'
        user_b.profile.referred_by = self.user_a
        user_b.profile.save()

        self.assertEqual(user_b.profile.referred_by, self.user_a)
        self.assertIn(user_b.profile, self.user_a.referred_users.all())

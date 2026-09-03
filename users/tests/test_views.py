"""
Tests for the users app — registration, login (including the
open-redirect fix and rate limiting), logout, and profile editing.
"""
from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from users.models import Profile


class RegisterViewTests(TestCase):
    def valid_data(self, **overrides):
        data = {
            'first_name': 'Alice', 'last_name': 'Smith', 'username': 'alice',
            'email': 'alice@example.com', 'password1': 'Str0ngPassw0rd!', 'password2': 'Str0ngPassw0rd!',
        }
        data.update(overrides)
        return data

    def test_successful_registration_creates_user_and_logs_in(self):
        response = self.client.post(reverse('users:register'), self.valid_data())
        self.assertTrue(User.objects.filter(username='alice').exists())
        self.assertEqual(response.status_code, 302)
        # Registration should log the user in immediately
        self.assertTrue(response.wsgi_request.user.is_authenticated)

    def test_registration_creates_a_profile_via_signal(self):
        self.client.post(reverse('users:register'), self.valid_data())
        user = User.objects.get(username='alice')
        self.assertTrue(Profile.objects.filter(user=user).exists())

    def test_password_mismatch_is_rejected(self):
        response = self.client.post(reverse('users:register'), self.valid_data(password2='DifferentPassword1!'))
        self.assertFalse(User.objects.filter(username='alice').exists())
        self.assertEqual(response.status_code, 200)  # re-rendered with errors, not redirected

    def test_duplicate_username_is_rejected(self):
        User.objects.create_user(username='alice', password='pw12345')
        response = self.client.post(reverse('users:register'), self.valid_data())
        self.assertEqual(User.objects.filter(username='alice').count(), 1)

    def test_missing_email_is_rejected(self):
        response = self.client.post(reverse('users:register'), self.valid_data(email=''))
        self.assertFalse(User.objects.filter(username='alice').exists())

    def test_already_authenticated_user_is_redirected_away(self):
        User.objects.create_user(username='bob', password='pw12345')
        self.client.login(username='bob', password='pw12345')
        response = self.client.get(reverse('users:register'))
        self.assertEqual(response.status_code, 302)


class LoginViewTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(username='alice', password='pw12345')

    def test_valid_login_succeeds(self):
        response = self.client.post(reverse('users:login'), {'username': 'alice', 'password': 'pw12345'})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.wsgi_request.user.is_authenticated)

    def test_invalid_password_is_rejected(self):
        response = self.client.post(reverse('users:login'), {'username': 'alice', 'password': 'wrong-password'})
        self.assertFalse(response.wsgi_request.user.is_authenticated)
        self.assertEqual(response.status_code, 200)

    def test_already_authenticated_user_is_redirected_away(self):
        self.client.login(username='alice', password='pw12345')
        response = self.client.get(reverse('users:login'))
        self.assertEqual(response.status_code, 302)

    def test_default_redirect_goes_to_dashboard(self):
        response = self.client.post(reverse('users:login'), {'username': 'alice', 'password': 'pw12345'})
        self.assertEqual(response.url, '/dashboard/')

    def test_safe_next_param_is_honored(self):
        url = reverse('users:login') + '?next=/portfolio/'
        response = self.client.post(url, {'username': 'alice', 'password': 'pw12345'})
        self.assertEqual(response.url, '/portfolio/')

    def test_open_redirect_via_external_next_is_blocked(self):
        """
        Regression test for the open-redirect fix: ?next=https://evil.com
        must NOT be honored — login should fall back to /dashboard/ instead
        of sending the user to an attacker-controlled external site.
        """
        url = reverse('users:login') + '?next=https://evil.com/phish'
        response = self.client.post(url, {'username': 'alice', 'password': 'pw12345'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/dashboard/')
        self.assertNotIn('evil.com', response.url)

    def test_protocol_relative_next_is_blocked(self):
        # //evil.com is a classic open-redirect bypass attempt (no scheme,
        # browsers treat it as same-protocol to evil.com)
        url = reverse('users:login') + '?next=//evil.com'
        response = self.client.post(url, {'username': 'alice', 'password': 'pw12345'})
        self.assertEqual(response.url, '/dashboard/')

    def test_login_is_rate_limited_after_repeated_attempts(self):
        for _ in range(10):
            self.client.post(reverse('users:login'), {'username': 'alice', 'password': 'wrong'})
        response = self.client.post(reverse('users:login'), {'username': 'alice', 'password': 'wrong'})
        self.assertEqual(response.status_code, 429)

    def test_rate_limit_does_not_block_a_different_client(self):
        # Exhaust the limit as one "IP" (default test client IP), then
        # verify a request tagged with a different IP still gets through.
        for _ in range(10):
            self.client.post(reverse('users:login'), {'username': 'alice', 'password': 'wrong'})
        response = self.client.post(
            reverse('users:login'),
            {'username': 'alice', 'password': 'pw12345'},
            REMOTE_ADDR='203.0.113.99',
        )
        self.assertNotEqual(response.status_code, 429)


class LogoutViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='alice', password='pw12345')

    def test_logout_requires_login(self):
        response = self.client.get(reverse('users:logout'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_post_logout_clears_session(self):
        self.client.login(username='alice', password='pw12345')
        response = self.client.post(reverse('users:logout'))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(response.wsgi_request.user.is_authenticated if hasattr(response, 'wsgi_request') else False)
        # Follow-up request should be anonymous again
        dash_response = self.client.get(reverse('portfolio:dashboard'))
        self.assertEqual(dash_response.status_code, 302)

    def test_get_logout_does_not_log_out(self):
        # View only logs out on POST — GET just redirects without ending the session
        self.client.login(username='alice', password='pw12345')
        self.client.get(reverse('users:logout'))
        response = self.client.get(reverse('portfolio:dashboard'))
        self.assertEqual(response.status_code, 200)  # still logged in


class ProfileViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='alice', password='pw12345', email='alice@old.com',
            first_name='Alice', last_name='Smith',
        )
        self.client.login(username='alice', password='pw12345')

    def test_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse('users:profile'))
        self.assertEqual(response.status_code, 302)

    def test_profile_page_loads(self):
        response = self.client.get(reverse('users:profile'))
        self.assertEqual(response.status_code, 200)

    def test_updating_email_and_bio(self):
        response = self.client.post(reverse('users:profile'), {
            'first_name': 'Alice', 'last_name': 'Smith',
            'username': 'alice', 'email': 'alice@new.com',
            'bio': 'Software developer.',
        })
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, 'alice@new.com')
        self.assertEqual(self.user.profile.bio, 'Software developer.')

    def test_invalid_email_is_rejected(self):
        response = self.client.post(reverse('users:profile'), {
            'first_name': 'Alice', 'last_name': 'Smith',
            'username': 'alice', 'email': 'not-an-email',
            'bio': '',
        })
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, 'alice@old.com')  # unchanged
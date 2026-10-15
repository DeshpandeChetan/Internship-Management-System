from unittest.mock import patch

from allauth.account.models import EmailAddress
from allauth.socialaccount.models import SocialAccount, SocialApp, SocialLogin
from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.test import RequestFactory, TestCase

from apps.authentication.adapter import CustomSocialAccountAdapter
from apps.authentication.models import UserProfile


class AccountAuthorizationTests(TestCase):
    def test_login_status_messages_and_session(self):
        from allauth.account.internal.flows.login import perform_login
        from allauth.account.models import Login
        from allauth.core.context import request_context
        from django.contrib.auth import SESSION_KEY
        from django.contrib.auth.models import AnonymousUser
        from django.contrib.messages import get_messages
        from django.contrib.messages.middleware import MessageMiddleware
        from django.contrib.sessions.middleware import SessionMiddleware
        from django.urls import reverse

        cases = [
            ('student', True, False, True, 'pending admin approval', False),
            ('student', False, True, True, 'deactivated', False),
            ('faculty_mentor', False, True, True, 'deactivated', False),
            ('student', True, True, False, 'deactivated', False),
            ('student', True, True, True, None, True),
            ('faculty_mentor', True, False, True, None, True),
        ]
        for index, (role, active, approved, user_active, status, allowed) in enumerate(cases):
            with self.subTest(role=role, active=active, approved=approved, user_active=user_active):
                user = User.objects.create_user(
                    username=f'login-test-{index}', email=f'login-{index}@example.com',
                    is_active=user_active,
                )
                UserProfile.objects.create(user=user, role=role, is_active=active, is_approved=approved)
                request = RequestFactory().get('/accounts/google/login/callback/')
                SessionMiddleware(lambda r: None).process_request(request)
                MessageMiddleware(lambda r: None).process_request(request)
                request.user = AnonymousUser()
                with request_context(request):
                    response = perform_login(request, Login(user=user, email_verification='none'))
                queued = list(get_messages(request))
                self.assertEqual(SESSION_KEY in request.session, allowed)
                self.assertEqual(request.user.is_authenticated, allowed)
                self.assertEqual(len(queued), 1)
                if allowed:
                    self.assertEqual(queued[0].level, 25)
                    self.assertEqual(response.url, '/dashboard/')
                else:
                    self.assertIn(status, str(queued[0]))
                    self.assertNotEqual(queued[0].level, 25)
                    self.assertEqual(response.url, reverse('login'))


class CustomSocialAccountAdapterTests(TestCase):
    def setUp(self):
        self.adapter = CustomSocialAccountAdapter()
        self.request = RequestFactory().get('/accounts/google/login/callback/')
        self.request.session = {}
        site = Site.objects.get_current()
        app = SocialApp.objects.create(
            provider='google',
            name='Google',
            client_id='test-client-id',
            secret='test-secret',
        )
        app.sites.add(site)

    def _google_login(self, email, uid='google-uid-1'):
        return SocialLogin(
            user=User(email=email),
            account=SocialAccount(
                provider='google',
                uid=uid,
                extra_data={'email': email},
            ),
            email_addresses=[
                EmailAddress(email=email, verified=True, primary=True),
            ],
        )

    @patch('apps.authentication.adapter.CustomSocialAccountAdapter.send_notification_mail')
    def test_existing_admin_created_user_is_linked_by_google_email(self, _send_mail):
        user = User.objects.create_user(
            username='mentor',
            email='mentor@example.com',
            first_name='Faculty',
            last_name='Mentor',
        )
        UserProfile.objects.create(
            user=user,
            role='faculty_mentor',
            is_active=True,
            is_approved=True,
        )
        sociallogin = self._google_login('MENTOR@example.com')

        self.adapter.pre_social_login(self.request, sociallogin)

        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(SocialAccount.objects.count(), 1)
        self.assertTrue(sociallogin.is_existing)
        self.assertEqual(sociallogin.user, user)

        account = SocialAccount.objects.get()
        self.assertEqual(account.user, user)
        self.assertEqual(account.provider, 'google')

        user.profile.refresh_from_db()
        self.assertEqual(user.profile.role, 'faculty_mentor')
        self.assertTrue(user.profile.is_approved)

    def test_new_google_user_still_uses_existing_signup_flow(self):
        sociallogin = self._google_login('new.student@example.com')

        self.adapter.pre_social_login(self.request, sociallogin)

        self.assertEqual(User.objects.count(), 0)
        self.assertEqual(SocialAccount.objects.count(), 0)
        self.assertFalse(sociallogin.is_existing)

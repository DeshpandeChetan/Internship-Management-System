from unittest.mock import patch

from allauth.account.models import EmailAddress
from allauth.socialaccount.models import SocialAccount, SocialApp, SocialLogin
from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.test import RequestFactory, TestCase

from apps.authentication.adapter import CustomSocialAccountAdapter
from apps.authentication.models import UserProfile


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

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core import mail
from rest_framework.test import APIClient
from rest_framework import status

User = get_user_model()


class RegisterTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = '/api/auth/register/'
        self.valid_payload = {
            'email': 'test@example.com',
            'first_name': 'Test',
            'last_name': 'User',
            'phone': '+639123456789',
            'password': 'StrongPass123!',
            'password2': 'StrongPass123!',
        }

    def test_register_creates_user(self):
        response = self.client.post(self.url, self.valid_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(email='test@example.com').exists())

    def test_register_sends_verification_email(self):
        self.client.post(self.url, self.valid_payload, format='json')
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('verify', mail.outbox[0].subject.lower())

    def test_register_duplicate_email_fails(self):
        # The view intentionally returns 201 for duplicate emails to prevent
        # user-enumeration attacks (see RegisterView docstring).
        self.client.post(self.url, self.valid_payload, format='json')
        response = self.client.post(self.url, self.valid_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['detail'], 'Account created. Please check your email to verify your account.')

    def test_register_password_mismatch_fails(self):
        payload = {**self.valid_payload, 'password2': 'WrongPass123!'}
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_weak_password_fails(self):
        payload = {**self.valid_payload, 'password': '123', 'password2': '123'}
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class LoginTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = '/api/auth/login/'
        self.user = User.objects.create_user(
            email='login@example.com',
            username='login',
            first_name='Login',
            last_name='Test',
            password='StrongPass123!',
            is_verified=True,
        )

    def test_login_success(self):
        response = self.client.post(self.url, {
            'email': 'login@example.com',
            'password': 'StrongPass123!',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        # Refresh token is in httpOnly cookie, not in JSON body
        self.assertIn('refresh_token', response.cookies)
        self.assertIn('user', response.data)

    def test_login_wrong_password_fails(self):
        response = self.client.post(self.url, {
            'email': 'login@example.com',
            'password': 'WrongPass123!',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_nonexistent_email_fails(self):
        response = self.client.post(self.url, {
            'email': 'nobody@example.com',
            'password': 'StrongPass123!',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_missing_fields_fails(self):
        response = self.client.post(self.url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class MeEndpointTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='me@example.com',
            username='me',
            first_name='Me',
            last_name='Test',
            password='StrongPass123!',
        )

    def test_me_authenticated(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/auth/me/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], 'me@example.com')

    def test_me_unauthenticated_fails(self):
        response = self.client.get('/api/auth/me/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class TokenRefreshTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='refresh@example.com',
            username='refresh',
            password='StrongPass123!',
        )
        # Use force_authenticate to avoid rate-limiting login endpoint
        self.client.force_authenticate(user=self.user)

    def test_token_refresh(self):
        # Get a refresh token for the user
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(self.user)

        # CookieTokenRefreshView reads from httpOnly cookie, not request body
        self.client.cookies['refresh_token'] = str(refresh)
        response = self.client.post('/api/auth/token/refresh/', {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)

    def test_token_refresh_invalid_fails(self):
        self.client.cookies['refresh_token'] = 'invalid-token'
        response = self.client.post('/api/auth/token/refresh/', {}, format='json')
        # CookieTokenRefreshView returns 401 for invalid/expired tokens
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class LogoutTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='logout@example.com',
            username='logout',
            password='StrongPass123!',
        )

    def test_logout_blacklists_token(self):
        # Use force_authenticate + direct token creation to avoid login rate limit
        self.client.force_authenticate(user=self.user)
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(self.user)

        # LogoutView reads refresh token from request body
        response = self.client.post('/api/auth/logout/', {
            'refresh': str(refresh),
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify token is blacklisted — refresh via cookie should fail
        self.client.cookies['refresh_token'] = str(refresh)
        refresh_resp = self.client.post('/api/auth/token/refresh/', {}, format='json')
        self.assertEqual(refresh_resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_unauthenticated_fails(self):
        response = self.client.post('/api/auth/logout/', {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

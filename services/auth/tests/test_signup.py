from django.test import TestCase
from rest_framework.test import APIClient
from users.models import User
import json

class SignUpTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.signup_url = '/auth/signup/'
    
    def test_valid_signup(self):
        data = {
            'email': 'test@example.com',
            'password': 'securepassword123',
            'password_confirm': 'securepassword123',
            'name': 'Test User'
        }
        response = self.client.post(self.signup_url, data)
        self.assertEqual(response.status_code, 201)
        self.assertTrue(User.objects.filter(email='test@example.com').exists())
        user = User.objects.get(email='test@example.com')
        self.assertFalse(user.email_verified)
        self.assertIsNotNone(user.email_verification_token)
    
    def test_duplicate_email(self):
        User.objects.create(email='existing@example.com', name='Existing')
        data = {
            'email': 'existing@example.com',
            'password': 'securepassword123',
            'password_confirm': 'securepassword123',
            'name': 'Test User'
        }
        response = self.client.post(self.signup_url, data)
        self.assertEqual(response.status_code, 400)
        self.assertIn('email', response.json())
    
    def test_invalid_password_short(self):
        data = {
            'email': 'test@example.com',
            'password': 'short',
            'password_confirm': 'short',
            'name': 'Test User'
        }
        response = self.client.post(self.signup_url, data)
        self.assertEqual(response.status_code, 400)
        self.assertIn('password', response.json())
    
    def test_invalid_email(self):
        data = {
            'email': 'notanemail',
            'password': 'securepassword123',
            'password_confirm': 'securepassword123',
            'name': 'Test User'
        }
        response = self.client.post(self.signup_url, data)
        self.assertEqual(response.status_code, 400)
        self.assertIn('email', response.json())

class SignUpIntegrationTest(TestCase):
    def test_full_signup_flow(self):
        """Integration test for full signup flow"""
        client = APIClient()
        data = {
            'email': 'integration@test.com',
            'password': 'integrationpass123',
            'password_confirm': 'integrationpass123',
            'name': 'Integration Test'
        }
        response = client.post('/auth/signup/', data)
        self.assertEqual(response.status_code, 201)
        user = User.objects.get(email='integration@test.com')
        self.assertIsNotNone(user.email_verification_token)
        # Would continue with email verification in KRV-010
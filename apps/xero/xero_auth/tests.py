"""
Unit tests for Xero authentication views (v3).
Tests OAuth flow initiation and callback handling.
"""
import sys
from unittest.mock import MagicMock, patch, Mock
sys.modules['apscheduler'] = MagicMock()
sys.modules['apscheduler.schedulers'] = MagicMock()
sys.modules['apscheduler.schedulers.background'] = MagicMock()

from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from django.utils import timezone
import datetime

from apps.xero.xero_auth.models import XeroClientCredentials, XeroTenantToken, XeroAuthSettings
from apps.xero.xero_core.models import XeroTenant

User = get_user_model()


class XeroAuthInitiateViewTest(TestCase):
    """Test XeroAuthInitiateView."""
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)
        
        self.credentials = XeroClientCredentials.objects.create(
            user=self.user,
            client_id='test-client-id',
            client_secret='test-client-secret',
            scope=['accounting.transactions'],
            active=True
        )
        
        self.auth_settings = XeroAuthSettings.objects.create(
            auth_url='https://login.xero.com/identity/connect/authorize',
            access_token_url='https://identity.xero.com/connect/token',
            refresh_url='https://identity.xero.com/connect/token'
        )
    
    def test_auth_initiate_success(self):
        """Test successful auth initiation."""
        response = self.client.get('/xero/auth/initiate/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('auth_url', response.data)
        self.assertIn('test-client-id', response.data['auth_url'])
        self.assertIn('accounting.transactions', response.data['auth_url'])
    
    def test_auth_initiate_no_credentials(self):
        """Test auth initiation without credentials."""
        self.credentials.delete()
        response = self.client.get('/xero/auth/initiate/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('error', response.data)
    
    def test_auth_initiate_no_settings(self):
        """Test auth initiation without auth settings."""
        self.auth_settings.delete()
        response = self.client.get('/xero/auth/initiate/')
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertIn('error', response.data)
    
    def test_auth_initiate_unauthenticated(self):
        """Test auth initiation without authentication."""
        client = APIClient()
        response = client.get('/xero/auth/initiate/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class XeroCallbackViewTest(TestCase):
    """Test XeroCallbackView."""
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)
        
        self.credentials = XeroClientCredentials.objects.create(
            user=self.user,
            client_id='test-client-id',
            client_secret='test-client-secret',
            scope=['accounting.transactions'],
            active=True
        )
        
        self.auth_settings = XeroAuthSettings.objects.create(
            auth_url='https://login.xero.com/identity/connect/authorize',
            access_token_url='https://identity.xero.com/connect/token',
            refresh_url='https://identity.xero.com/connect/token'
        )
    
    @patch('apps.xero.xero_auth.views.requests.post')
    @patch('apps.xero.xero_auth.views.IdentityApi')
    @patch('apps.xero.xero_auth.views.XeroApiClient')
    def test_callback_success(self, mock_api_client, mock_identity_api, mock_post):
        """Test successful OAuth callback."""
        # Mock token exchange
        mock_response = Mock()
        mock_response.json.return_value = {
            'access_token': 'test-token',
            'refresh_token': 'test-refresh',
            'expires_in': 3600
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response
        
        # Mock identity API
        mock_identity_instance = Mock()
        mock_connection = Mock()
        mock_connection.tenant_id = 'test-tenant-123'
        mock_connection.tenant_name = 'Test Tenant'
        mock_identity_instance.get_connections.return_value = [mock_connection]
        mock_identity_api.return_value = mock_identity_instance
        
        # Mock API client
        mock_client_instance = Mock()
        mock_api_client.return_value = mock_client_instance
        mock_client_instance.api_client = Mock()
        
        response = self.client.get('/xero/callback/', {'code': 'test-code'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('message', response.data)
        self.assertIn('tenant_ids', response.data)
        self.assertEqual(response.data['tenant_ids'], ['test-tenant-123'])
        
        # Verify tenant was created
        tenant = XeroTenant.objects.get(tenant_id='test-tenant-123')
        self.assertEqual(tenant.tenant_name, 'Test Tenant')
        
        # Verify token was created
        token = XeroTenantToken.objects.get(tenant=tenant, credentials=self.credentials)
        self.assertIsNotNone(token)
    
    def test_callback_no_code(self):
        """Test callback without authorization code."""
        response = self.client.get('/xero/callback/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_callback_no_credentials(self):
        """Test callback without credentials."""
        self.credentials.delete()
        response = self.client.get('/xero/callback/', {'code': 'test-code'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

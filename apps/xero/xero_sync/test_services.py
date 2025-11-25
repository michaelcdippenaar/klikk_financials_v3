"""
Unit tests for Xero sync services (v3).
Tests data synchronization service functions.
"""
import sys
from unittest.mock import MagicMock, patch
sys.modules['apscheduler'] = MagicMock()
sys.modules['apscheduler.schedulers'] = MagicMock()
sys.modules['apscheduler.schedulers.background'] = MagicMock()

from django.test import TestCase
from django.contrib.auth import get_user_model

from apps.xero.xero_core.models import XeroTenant
from apps.xero.xero_auth.models import XeroClientCredentials
from apps.xero.xero_sync.services import update_xero_models

User = get_user_model()


class UpdateXeroModelsServiceTest(TestCase):
    """Test update_xero_models service function."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.tenant = XeroTenant.objects.create(
            tenant_id='test-tenant-123',
            tenant_name='Test Tenant'
        )
        self.credentials = XeroClientCredentials.objects.create(
            user=self.user,
            client_id='test-client-id',
            client_secret='test-client-secret',
            scope=['accounting.transactions'],
            active=True
        )
    
    @patch('apps.xero.xero_sync.services.XeroApiClient')
    @patch('apps.xero.xero_sync.services.XeroAccountingApi')
    def test_update_xero_models_success(self, mock_api_class, mock_client_class):
        """Test update_xero_models with successful execution."""
        # Mock API responses
        mock_api = MagicMock()
        mock_api_class.return_value = mock_api
        
        # Mock the API methods to return empty results
        accounts_mock = MagicMock()
        accounts_mock.get.return_value = None
        mock_api.accounts.return_value = accounts_mock
        
        tracking_mock = MagicMock()
        tracking_mock.get.return_value = None
        mock_api.tracking_categories.return_value = tracking_mock
        
        contacts_mock = MagicMock()
        contacts_mock.get.return_value = None
        mock_api.contacts.return_value = contacts_mock
        
        bank_transactions_mock = MagicMock()
        bank_transactions_mock.get.return_value = None
        mock_api.bank_transactions.return_value = bank_transactions_mock
        
        invoices_mock = MagicMock()
        invoices_mock.get.return_value = None
        mock_api.invoices.return_value = invoices_mock
        
        payments_mock = MagicMock()
        payments_mock.get.return_value = None
        mock_api.payments.return_value = payments_mock
        
        journals_mock = MagicMock()
        journals_mock.get.return_value = None
        mock_api.journals.return_value = journals_mock
        
        # Call the function
        result = update_xero_models(self.tenant.tenant_id, user=self.user)
        
        # Assertions
        self.assertTrue(result['success'])
        self.assertIn('message', result)
        self.assertIn('stats', result)
        self.assertEqual(len(result.get('errors', [])), 0)
        self.assertIn('duration_seconds', result['stats'])
    
    @patch('apps.xero.xero_sync.services.XeroApiClient')
    @patch('apps.xero.xero_sync.services.XeroAccountingApi')
    def test_update_xero_models_with_errors(self, mock_api_class, mock_client_class):
        """Test update_xero_models with some API errors."""
        mock_api = MagicMock()
        mock_api_class.return_value = mock_api
        
        # Mock one failing call
        accounts_mock = MagicMock()
        accounts_mock.get.side_effect = Exception("API Error")
        mock_api.accounts.return_value = accounts_mock
        
        tracking_mock = MagicMock()
        tracking_mock.get.return_value = None
        mock_api.tracking_categories.return_value = tracking_mock
        
        contacts_mock = MagicMock()
        contacts_mock.get.return_value = None
        mock_api.contacts.return_value = contacts_mock
        
        # Call the function
        result = update_xero_models(self.tenant.tenant_id, user=self.user)
        
        # Should have errors but still return result
        self.assertFalse(result['success'])
        self.assertGreater(len(result.get('errors', [])), 0)
    
    def test_update_xero_models_tenant_not_found(self):
        """Test update_xero_models with non-existent tenant."""
        with self.assertRaises(ValueError) as context:
            update_xero_models('non-existent-tenant', user=self.user)
        
        self.assertIn('not found', str(context.exception).lower())


class XeroApiClientTest(TestCase):
    """Test XeroApiClient from xero_core."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_api_client_initialization(self):
        """Test XeroApiClient can be initialized."""
        from apps.xero.xero_core.services import XeroApiClient
        # Create credentials first
        credentials = XeroClientCredentials.objects.create(
            user=self.user,
            client_id='test-client-id',
            client_secret='test-client-secret',
            scope=['accounting.transactions'],
            active=True
        )
        client = XeroApiClient(self.user)
        self.assertIsNotNone(client)
        self.assertEqual(client.user, self.user)


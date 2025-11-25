"""
Base test classes for Xero apps.
"""
from django.test import TestCase
from rest_framework.test import APIClient
from apps.xero.tests.factories import (
    UserFactory, XeroTenantFactory, XeroClientCredentialsFactory,
    XeroAuthSettingsFactory
)


class XeroTestCase(TestCase):
    """Base test case with common setup for Xero tests."""
    
    def setUp(self):
        """Set up common test data."""
        self.user = UserFactory()
        self.tenant = XeroTenantFactory()
        self.credentials = XeroClientCredentialsFactory(user=self.user)
        self.auth_settings = XeroAuthSettingsFactory()
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)


class XeroAPITestCase(XeroTestCase):
    """Base test case for API endpoint tests."""
    
    def setUp(self):
        """Set up API test data."""
        super().setUp()
        # Additional API-specific setup can go here


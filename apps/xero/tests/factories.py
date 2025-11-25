"""
Test factories for Xero apps using Factory Boy.
Usage: pip install factory-boy
"""
import factory
from factory.django import DjangoModelFactory
from django.contrib.auth import get_user_model
from django.utils import timezone
import datetime

from apps.user.models import User
from apps.xero.xero_core.models import XeroTenant
from apps.xero.xero_auth.models import (
    XeroClientCredentials, XeroTenantToken, XeroAuthSettings
)
from apps.xero.xero_sync.models import XeroTenantSchedule, XeroTaskExecutionLog

UserModel = get_user_model()


class UserFactory(DjangoModelFactory):
    """Factory for User model."""
    class Meta:
        model = UserModel
        django_get_or_create = ('username',)
    
    username = factory.Sequence(lambda n: f"testuser{n}")
    email = factory.LazyAttribute(lambda obj: f"{obj.username}@example.com")
    password = factory.PostGenerationMethodCall('set_password', 'testpass123')


class XeroTenantFactory(DjangoModelFactory):
    """Factory for XeroTenant model."""
    class Meta:
        model = XeroTenant
        django_get_or_create = ('tenant_id',)
    
    tenant_id = factory.Sequence(lambda n: f"tenant-{n}")
    tenant_name = factory.Faker('company')


class XeroAuthSettingsFactory(DjangoModelFactory):
    """Factory for XeroAuthSettings model."""
    class Meta:
        model = XeroAuthSettings
    
    auth_url = 'https://login.xero.com/identity/connect/authorize'
    access_token_url = 'https://identity.xero.com/connect/token'
    refresh_url = 'https://identity.xero.com/connect/token'


class XeroClientCredentialsFactory(DjangoModelFactory):
    """Factory for XeroClientCredentials model."""
    class Meta:
        model = XeroClientCredentials
    
    user = factory.SubFactory(UserFactory)
    client_id = factory.Faker('uuid4')
    client_secret = factory.Faker('uuid4')
    scope = ['accounting.transactions']
    active = True


class XeroTenantTokenFactory(DjangoModelFactory):
    """Factory for XeroTenantToken model."""
    class Meta:
        model = XeroTenantToken
    
    tenant = factory.SubFactory(XeroTenantFactory)
    credentials = factory.SubFactory(XeroClientCredentialsFactory)
    token = {'access_token': 'test-token', 'expires_in': 3600}
    refresh_token = factory.Faker('uuid4')
    expires_at = factory.LazyFunction(
        lambda: timezone.now() + datetime.timedelta(hours=1)
    )


class XeroTenantScheduleFactory(DjangoModelFactory):
    """Factory for XeroTenantSchedule model."""
    class Meta:
        model = XeroTenantSchedule
    
    tenant = factory.SubFactory(XeroTenantFactory)
    enabled = True
    update_interval_minutes = 60
    update_start_time = datetime.time(0, 0)


class XeroTaskExecutionLogFactory(DjangoModelFactory):
    """Factory for XeroTaskExecutionLog model."""
    class Meta:
        model = XeroTaskExecutionLog
    
    tenant = factory.SubFactory(XeroTenantFactory)
    task_type = 'update_models'
    status = 'running'


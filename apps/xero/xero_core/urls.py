from django.urls import path
from apps.xero.xero_core import views

app_name = 'xero_core'

urlpatterns = [
    path('tenants/', views.XeroTenantListView.as_view(), name='xero-tenant-list'),
]

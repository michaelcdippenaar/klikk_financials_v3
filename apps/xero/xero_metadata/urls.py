from django.urls import path
from apps.xero.xero_metadata import views

app_name = 'xero_metadata'

urlpatterns = [
    path('update/', views.XeroUpdateMetadataView.as_view(), name='update_metadata'),
    path('accounts/search/', views.account_search, name='account_search'),
]

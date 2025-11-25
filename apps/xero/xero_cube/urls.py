from django.urls import path
from apps.xero.xero_cube import views

app_name = 'xero_cube'

urlpatterns = [
    path('process/', views.XeroProcessDataView.as_view(), name='xero-process-data'),
    path('summary/', views.XeroDataSummaryView.as_view(), name='xero-data-summary'),
]

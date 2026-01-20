from django.urls import path
from apps.deployment import views

app_name = 'deployment'

urlpatterns = [
    path('webhook/github/', views.github_webhook, name='github_webhook'),
]

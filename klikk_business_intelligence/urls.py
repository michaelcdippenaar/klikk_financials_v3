"""
URL configuration for klikk_business_intelligence project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from rest_framework.authtoken.views import obtain_auth_token

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Authentication endpoints
    path('api/auth/', include('apps.user.urls')),  # JWT registration/login
    path('api-token-auth/', obtain_auth_token, name='api_token_auth'),  # Legacy token auth
    path('login/', auth_views.LoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    
    # Xero endpoints
    path('xero/auth/', include('apps.xero.xero_auth.urls')),
    path('xero/core/', include('apps.xero.xero_core.urls')),
    path('xero/sync/', include('apps.xero.xero_sync.urls')),
    path('xero/data/', include('apps.xero.xero_data.urls')),
    path('xero/cube/', include('apps.xero.xero_cube.urls')),
    path('xero/metadata/', include('apps.xero.xero_metadata.urls')),
    path('xero/validation/', include('apps.xero.xero_validation.urls')),
]

"""
Xero authentication views.
"""
import base64
import datetime
import logging
import requests
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from xero_python.identity import IdentityApi
from xero_python.exceptions import AccountingBadRequestException as ApiException

from apps.xero.xero_auth.models import XeroClientCredentials, XeroTenantToken, XeroAuthSettings
from apps.xero.xero_core.models import XeroTenant
from apps.xero.xero_core.services import XeroApiClient

logger = logging.getLogger(__name__)
User = get_user_model()


class XeroAuthInitiateView(APIView):
    permission_classes = [AllowAny]  # TODO: Change to IsAuthenticated for production

    def get(self, request):
        """Initiate Xero OAuth2 flow by returning the authorization URL."""
        # TODO: When adding authentication back, filter by request.user
        # For now, get first active credentials (development only)
        try:
            if request.user.is_authenticated:
                credentials = XeroClientCredentials.objects.get(user=request.user, active=True)
            else:
                # For development: get first active credentials
                credentials = XeroClientCredentials.objects.filter(active=True).first()
                if not credentials:
                    return Response({"error": "No active Xero credentials found"}, status=status.HTTP_403_FORBIDDEN)
        except XeroClientCredentials.DoesNotExist:
            return Response({"error": "No active Xero credentials found"}, status=status.HTTP_403_FORBIDDEN)

        auth_settings = XeroAuthSettings.objects.first()
        if not auth_settings:
            return Response({"error": "Xero authentication settings not configured"},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        scope = " ".join(credentials.scope) if credentials.scope else "accounting.transactions"
        redirect_uri = request.build_absolute_uri('/xero/auth/callback/')
        auth_url = (
            f"{auth_settings.auth_url}?response_type=code"
            f"&client_id={credentials.client_id}"
            f"&redirect_uri={redirect_uri}"
            f"&scope={scope}"
        )
        return Response({"auth_url": auth_url})


class XeroCallbackView(APIView):
    permission_classes = [AllowAny]  # TODO: Change to IsAuthenticated for production

    def get(self, request):
        # TODO: When adding authentication back, use request.user
        user_info = request.user.username if request.user.is_authenticated else "anonymous"
        logger.info(f"Processing callback for user {user_info}")
        code = request.query_params.get('code')
        if not code:
            logger.error("No code provided")
            return Response({"error": "No authorization code provided"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # TODO: When adding authentication back, filter by request.user
            # For now, get first active credentials (development only)
            if request.user.is_authenticated:
                credentials = XeroClientCredentials.objects.get(user=request.user, active=True)
            else:
                # For development: get first active credentials
                credentials = XeroClientCredentials.objects.filter(active=True).first()
                if not credentials:
                    logger.error("No active credentials found")
                    return Response({"error": "No active Xero credentials found"}, status=status.HTTP_403_FORBIDDEN)
            logger.info(f"Credentials found: client_id={credentials.client_id}")
        except XeroClientCredentials.DoesNotExist:
            logger.error(f"No active credentials found")
            return Response({"error": "No active Xero credentials found"}, status=status.HTTP_403_FORBIDDEN)

        auth_settings = XeroAuthSettings.objects.first()
        if not auth_settings:
            logger.error("XeroAuthSettings not configured")
            return Response({"error": "Xero authentication settings not configured"},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Exchange code for token
        token_url = auth_settings.access_token_url
        tokenb4 = f"{credentials.client_id}:{credentials.client_secret}"
        basic_token = base64.urlsafe_b64encode(tokenb4.encode()).decode()
        headers = {
            'Authorization': f"Basic {basic_token}",
            'Content-Type': 'application/x-www-form-urlencoded',
        }
        data = {
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': request.build_absolute_uri('/xero/auth/callback/'),
        }
        logger.info(f"Exchanging code: {code}")
        try:
            response = requests.post(token_url, headers=headers, data=data)
            response.raise_for_status()
            token_data = response.json()
            logger.info(f"Token data: {token_data}")
        except requests.RequestException as e:
            logger.error(f"Token exchange failed: {str(e)}")
            return Response({"error": f"Token exchange failed: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        if 'error' in token_data:
            logger.error(f"Token exchange error: {token_data['error']}")
            return Response({"error": token_data['error']}, status=status.HTTP_400_BAD_REQUEST)

        required_fields = ['access_token', 'expires_in']
        for field in required_fields:
            if field not in token_data:
                logger.error(f"Missing required field in token_data: {field}")
                return Response({"error": f"Invalid token data: missing {field}"},
                                status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Configure ApiClient with temporary token
        # Note: We don't have a tenant_id yet, so we create a temporary token object
        # and manually set it on the api_client
        # Create a minimal tenant object for the temp token (won't be saved to DB)
        temp_tenant = XeroTenant(tenant_id='temp', tenant_name='Temp')
        temp_tenant_token = XeroTenantToken(
            tenant=temp_tenant,
            credentials=credentials,
            token=token_data,
            refresh_token=token_data.get('refresh_token'),
            expires_at=timezone.now() + datetime.timedelta(seconds=token_data.get('expires_in'))
        )
        
        # TODO: When adding authentication back, use request.user
        # For now, use credentials.user (development only)
        api_client = XeroApiClient(credentials.user)
        # Set tenant_token BEFORE configure_api_client so the token getter can find it
        api_client.tenant_token = temp_tenant_token
        api_client.configure_api_client(temp_tenant_token)
        identity_api = IdentityApi(api_client.api_client)

        # Fetch all tenant connections
        try:
            logger.info("Calling get_connections")
            connections = identity_api.get_connections()
            logger.info(f"Connections retrieved: {len(connections)} tenants")
        except ApiException as e:
            logger.error(f"ApiException in get_connections: {str(e)}")
            return Response({"error": f"Failed to fetch connections: {str(e)}"},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            logger.error(f"Unexpected error in get_connections: {str(e)}")
            return Response({"error": f"Unexpected error in get_connections: {str(e)}"},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        if not connections:
            logger.warning("No tenant connections found")
            return Response({"error": "No tenant connections found"}, status=status.HTTP_400_BAD_REQUEST)

        # Process all tenants
        created_tenants = []
        for connection in connections:
            tenant_id = connection.tenant_id
            tenant_name = connection.tenant_name if connection.tenant_name else 'Unnamed Tenant'
            logger.info(f"Processing tenant ID: {tenant_id}, Name: {tenant_name}")

            # Create or update XeroTenant
            tenant, _ = XeroTenant.objects.get_or_create(
                tenant_id=tenant_id,
                defaults={'tenant_name': tenant_name}
            )

            # Save token to JSONField (new approach)
            expires_at = timezone.now() + datetime.timedelta(seconds=token_data.get('expires_in'))
            credentials.set_tenant_token_data(
                tenant_id=tenant_id,
                token_data=token_data,
                refresh_token=token_data.get('refresh_token'),
                expires_at=expires_at,
                connected_at=timezone.now()
            )
            
            # Also create/update XeroTenantToken model for backward compatibility
            XeroTenantToken.objects.update_or_create(
                tenant=tenant,
                credentials=credentials,
                defaults={
                    'token': token_data,
                    'refresh_token': token_data.get('refresh_token'),
                    'expires_at': expires_at
                }
            )
            created_tenants.append(tenant_id)

        logger.info(f"Stored tokens for tenants: {created_tenants}")
        return Response({
            "message": "Xero connection established",
            "tenant_ids": created_tenants
        })

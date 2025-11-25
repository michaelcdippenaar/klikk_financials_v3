"""
Xero cube views - data processing and summary endpoints.
"""
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny

from apps.xero.xero_core.models import XeroTenant
from apps.xero.xero_metadata.models import XeroAccount
from apps.xero.xero_data.models import XeroJournals
from apps.xero.xero_cube.models import XeroTrailBalance, XeroBalanceSheet
from apps.xero.xero_cube.services import process_xero_data


class XeroProcessDataView(APIView):
    permission_classes = [AllowAny]  # TODO: Change to IsAuthenticated for production

    def post(self, request):
        """
        Process Xero data (journals, trail balance, etc.).
        
        Expected payload:
        {
            "tenant_id": "string",
            "rebuild_trail_balance": false,  // Optional: If true, force full rebuild of trail balance and ignore existing data
            "exclude_manual_journals": false  // Optional: If true, only build trail balance from regular journals (exclude manual journals)
        }
        """
        tenant_id = request.data.get('tenant_id')
        if not tenant_id:
            return Response({"error": "tenant_id is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        rebuild_trail_balance = request.data.get('rebuild_trail_balance', False)
        exclude_manual_journals = request.data.get('exclude_manual_journals', False)
        
        try:
            # Use the service function for consistency with scheduled tasks
            result = process_xero_data(tenant_id, rebuild_trail_balance=rebuild_trail_balance, exclude_manual_journals=exclude_manual_journals)
            
            return Response({
                "message": result['message'],
                "stats": result['stats']
            })
        except XeroTenant.DoesNotExist:
            return Response({"error": "Tenant not found"}, status=status.HTTP_404_NOT_FOUND)
        except ValueError as e:
            return Response({"error": f"Processing failed: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": f"Unexpected error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class XeroDataSummaryView(APIView):
    permission_classes = [AllowAny]  # TODO: Change to IsAuthenticated for production

    def get(self, request):
        """Get a summary of data for a tenant."""
        tenant_id = request.query_params.get('tenant_id')
        if not tenant_id:
            return Response({"error": "tenant_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            tenant = XeroTenant.objects.get(tenant_id=tenant_id)
            summary = {
                'tenant_id': tenant_id,
                'tenant_name': tenant.tenant_name,
                'accounts_count': XeroAccount.objects.filter(organisation=tenant).count(),
                'journals_count': XeroJournals.objects.filter(organisation=tenant).count(),
                'trail_balance_count': XeroTrailBalance.objects.filter(organisation=tenant).count(),
                'balance_sheet_count': XeroBalanceSheet.objects.filter(organisation=tenant).count(),
            }
            return Response(summary)
        except XeroTenant.DoesNotExist:
            return Response({"error": "Tenant not found"}, status=status.HTTP_404_NOT_FOUND)

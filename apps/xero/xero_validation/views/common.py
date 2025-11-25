"""
Common helper functions and utilities for validation views.
"""
import logging
from decimal import Decimal

from rest_framework import status
from rest_framework.response import Response

from apps.xero.xero_core.models import XeroTenant
from ..models import XeroProfitAndLossReport, XeroTrailBalanceReport

logger = logging.getLogger(__name__)

# Constants
DEFAULT_TARGET_ACCOUNT_CODE = '960'  # Default account code for income statement entries
DEFAULT_TOLERANCE = Decimal('0.01')


def get_param(request, key, default=None):
    """Helper to get parameter from request.data or query_params."""
    return request.data.get(key) or request.query_params.get(key) or default


def get_tenant_id(request):
    """Extract and validate tenant_id from request."""
    tenant_id = get_param(request, 'tenant_id')
    if not tenant_id:
        raise ValueError("tenant_id is required")
    return tenant_id


def parse_date_string(date_str):
    """Parse date string and validate format."""
    if not date_str:
        return None
    from django.utils.dateparse import parse_date as django_parse_date
    parsed = django_parse_date(date_str)
    if not parsed:
        raise ValueError("Invalid date format. Use YYYY-MM-DD")
    return parsed


def parse_tolerance(tolerance_str, default=DEFAULT_TOLERANCE):
    """Parse tolerance value from string."""
    if not tolerance_str:
        return default
    try:
        return Decimal(str(tolerance_str))
    except (ValueError, TypeError):
        raise ValueError("Invalid tolerance value. Must be a number")


def handle_validation_error(exc, error_message="Validation failed"):
    """Standard error handling for validation views."""
    if isinstance(exc, XeroTenant.DoesNotExist):
        return Response({"error": "Tenant not found"}, status=status.HTTP_404_NOT_FOUND)
    elif isinstance(exc, XeroTrailBalanceReport.DoesNotExist):
        return Response({"error": "Report not found"}, status=status.HTTP_404_NOT_FOUND)
    elif isinstance(exc, XeroProfitAndLossReport.DoesNotExist):
        return Response({"error": "P&L report not found"}, status=status.HTTP_404_NOT_FOUND)
    elif isinstance(exc, ValueError):
        return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    else:
        logger.error(f"{error_message}: {str(exc)}", exc_info=True)
        return Response(
            {"error": f"{error_message}: {str(exc)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


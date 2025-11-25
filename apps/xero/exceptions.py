"""
Custom exceptions for Xero apps.
"""


class XeroAPIError(Exception):
    """Base exception for Xero API errors."""
    pass


class XeroTenantNotFoundError(XeroAPIError):
    """Raised when a Xero tenant is not found."""
    pass


class XeroAuthenticationError(XeroAPIError):
    """Raised when Xero authentication fails."""
    pass


class XeroCredentialsNotFoundError(XeroAPIError):
    """Raised when Xero credentials are not found."""
    pass


class XeroAPIRequestError(XeroAPIError):
    """Raised when a Xero API request fails."""
    pass


class XeroDataSyncError(XeroAPIError):
    """Raised when data synchronization fails."""
    pass


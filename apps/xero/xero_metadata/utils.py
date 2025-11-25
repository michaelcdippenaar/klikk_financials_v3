"""
Utility functions for fiscal year and financial period calculations.
"""


def fiscal_year_to_financial_year(year, month, fiscal_year_start_month):
    """
    Convert calendar year/month to financial year.
    
    Args:
        year: Calendar year
        month: Calendar month (1-12)
        fiscal_year_start_month: Month when fiscal year starts (1-12)
    
    Returns:
        Financial year (integer)
    """
    if month >= fiscal_year_start_month:
        return year
    else:
        return year - 1


def fiscal_month_to_financial_period(month, fiscal_year_start_month):
    """
    Convert calendar month to financial period.
    
    Args:
        month: Calendar month (1-12)
        fiscal_year_start_month: Month when fiscal year starts (1-12)
    
    Returns:
        Financial period (1-12)
    """
    if month >= fiscal_year_start_month:
        return month - fiscal_year_start_month + 1
    else:
        return month + (12 - fiscal_year_start_month) + 1


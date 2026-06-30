"""
GET YOUR PLUS — Helper Utilities
Formatting, date calculations, and common utilities.
"""

from datetime import datetime, timedelta
from config import CURRENCY


def format_price(price: float) -> str:
    """Format price with currency symbol."""
    if price == int(price):
        return f"{CURRENCY}{int(price)}"
    return f"{CURRENCY}{price:.2f}"


def format_date(iso_string: str) -> str:
    """Format ISO date string to human-readable format."""
    try:
        dt = datetime.fromisoformat(iso_string)
        return dt.strftime("%d %b %Y, %I:%M %p")
    except (ValueError, TypeError):
        return iso_string or "N/A"


def format_date_short(iso_string: str) -> str:
    """Format ISO date string to short date."""
    try:
        dt = datetime.fromisoformat(iso_string)
        return dt.strftime("%d %b %Y")
    except (ValueError, TypeError):
        return iso_string or "N/A"


def calculate_warranty_expiry(warranty_days: int) -> str:
    """Calculate warranty expiry date from now."""
    if not warranty_days or warranty_days <= 0:
        return None
    expiry = datetime.now() + timedelta(days=warranty_days)
    return expiry.isoformat()


def is_warranty_active(expiry_iso: str) -> bool:
    """Check if warranty is still active."""
    if not expiry_iso:
        return False
    try:
        expiry = datetime.fromisoformat(expiry_iso)
        return datetime.now() < expiry
    except (ValueError, TypeError):
        return False


def warranty_status_text(expiry_iso: str) -> str:
    """Get human-readable warranty status."""
    if not expiry_iso:
        return "❌ No Warranty"
    
    if is_warranty_active(expiry_iso):
        expiry = datetime.fromisoformat(expiry_iso)
        remaining = expiry - datetime.now()
        days = remaining.days
        if days > 30:
            months = days // 30
            return f"✅ Active ({months} month{'s' if months > 1 else ''} remaining)"
        elif days > 0:
            return f"✅ Active ({days} day{'s' if days > 1 else ''} remaining)"
        else:
            return "✅ Active (expires today)"
    else:
        return "❌ Expired"


def truncate_text(text: str, max_length: int = 100) -> str:
    """Truncate text with ellipsis if too long."""
    if not text:
        return ""
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."

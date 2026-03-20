"""Currency management for multi-currency support."""

# Currency definitions with symbols and exchange rates (relative to USD)
CURRENCIES = {
    "USD": {"symbol": "$", "name": "US Dollar", "rate": 1.0},
    "EUR": {"symbol": "€", "name": "Euro", "rate": 0.92},
    "GBP": {"symbol": "£", "name": "British Pound", "rate": 0.79},
    "JPY": {"symbol": "¥", "name": "Japanese Yen", "rate": 149.50},
    "INR": {"symbol": "₹", "name": "Indian Rupee", "rate": 83.12},
    "CAD": {"symbol": "C$", "name": "Canadian Dollar", "rate": 1.36},
    "AUD": {"symbol": "A$", "name": "Australian Dollar", "rate": 1.53},
    "CHF": {"symbol": "Fr", "name": "Swiss Franc", "rate": 0.88},
    "CNY": {"symbol": "¥", "name": "Chinese Yuan", "rate": 7.24},
    "MXN": {"symbol": "$", "name": "Mexican Peso", "rate": 17.15},
}

DEFAULT_CURRENCY = "USD"


def get_currency_list():
    """Return list of currency codes."""
    return list(CURRENCIES.keys())


def get_currency_display_list():
    """Return list of currency display strings for dropdown."""
    return [f"{code} ({info['symbol']}) - {info['name']}" 
            for code, info in CURRENCIES.items()]


def get_currency_info(currency_code):
    """Get currency info by code."""
    return CURRENCIES.get(currency_code, CURRENCIES[DEFAULT_CURRENCY])


def get_symbol(currency_code):
    """Get currency symbol."""
    return get_currency_info(currency_code)["symbol"]


def convert_amount(amount, from_currency, to_currency):
    """Convert amount from one currency to another."""
    if from_currency == to_currency:
        return amount
    
    from_rate = CURRENCIES.get(from_currency, CURRENCIES[DEFAULT_CURRENCY])["rate"]
    to_rate = CURRENCIES.get(to_currency, CURRENCIES[DEFAULT_CURRENCY])["rate"]
    
    # Convert to USD first, then to target currency
    usd_amount = amount / from_rate
    return usd_amount * to_rate


def format_currency(amount, currency_code):
    """Format amount with currency symbol."""
    symbol = get_symbol(currency_code)
    return f"{symbol}{amount:,.2f}"
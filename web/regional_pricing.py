"""
Regional pricing configuration for POSSIBLE.

Prices differentiated by shipping region (LATAM vs USA/Canada).
Region determined by shipping country at checkout.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


# =============================================================================
# REGIONS
# =============================================================================

@dataclass(frozen=True)
class Region:
    """A shipping region with its pricing tier."""
    key: str
    name: str
    name_es: str
    countries: List[str]  # ISO 3166-1 alpha-2 codes
    currency_display: str  # For showing local currency reference
    usd_to_local_rate: float  # Approximate exchange rate for display


REGIONS: Dict[str, Region] = {
    "usa": Region(
        key="usa",
        name="USA & Canada",
        name_es="EE.UU. y Canadá",
        countries=["US", "CA"],
        currency_display="USD",
        usd_to_local_rate=1.0,
    ),
    "latam": Region(
        key="latam",
        name="Latin America",
        name_es="Latinoamérica",
        countries=[
            "MX",  # Mexico
            "AR",  # Argentina
            "BR",  # Brazil
            "CL",  # Chile
            "CO",  # Colombia
            "PE",  # Peru
            "EC",  # Ecuador
            "VE",  # Venezuela
            "BO",  # Bolivia
            "PY",  # Paraguay
            "UY",  # Uruguay
            "CR",  # Costa Rica
            "PA",  # Panama
            "GT",  # Guatemala
            "HN",  # Honduras
            "SV",  # El Salvador
            "NI",  # Nicaragua
            "DO",  # Dominican Republic
            "PR",  # Puerto Rico
            "CU",  # Cuba
        ],
        currency_display="USD",
        usd_to_local_rate=1.0,
    ),
}

# Default region for unknown countries
DEFAULT_REGION = "latam"


def get_region_for_country(country_code: str) -> Region:
    """Get the pricing region for a country code."""
    country_code = country_code.upper()

    for region in REGIONS.values():
        if country_code in region.countries:
            return region

    # Default to LATAM pricing for unknown countries
    return REGIONS[DEFAULT_REGION]


# =============================================================================
# SIZES
# =============================================================================

@dataclass(frozen=True)
class Size:
    """A print size option."""
    key: str
    name: str
    name_es: str
    height_mm: int
    description: str
    description_es: str


SIZES: Dict[str, Size] = {
    "mini": Size(
        key="mini",
        name="Mini",
        name_es="Mini",
        height_mm=50,
        description="Perfect for desk decorations",
        description_es="Perfecto para decoración de escritorio",
    ),
    "small": Size(
        key="small",
        name="Small",
        name_es="Pequeño",
        height_mm=75,
        description="Great display piece",
        description_es="Excelente pieza de exhibición",
    ),
    "medium": Size(
        key="medium",
        name="Medium",
        name_es="Mediano",
        height_mm=100,
        description="Statement piece for shelves",
        description_es="Pieza destacada para repisas",
    ),
    "large": Size(
        key="large",
        name="Large",
        name_es="Grande",
        height_mm=150,
        description="Impressive centerpiece",
        description_es="Impresionante pieza central",
    ),
}


# =============================================================================
# PRICING MATRIX
# =============================================================================

# Prices in USD cents
# Structure: PRICES[region_key][size_key] = price_cents
PRICES: Dict[str, Dict[str, int]] = {
    "usa": {
        "mini": 4500,    # $45
        "small": 6500,   # $65
        "medium": 8900,  # $89
        "large": 14500,  # $145
    },
    "latam": {
        "mini": 5500,    # $55
        "small": 7500,   # $75
        "medium": 10900, # $109
        "large": 17900,  # $179
    },
}


# =============================================================================
# LOCAL CURRENCY DISPLAY (for reference only, payment in USD)
# =============================================================================

# Approximate exchange rates for display purposes
EXCHANGE_RATES: Dict[str, Dict[str, float]] = {
    "MX": {"code": "MXN", "rate": 20.0, "symbol": "$"},
    "AR": {"code": "ARS", "rate": 1000.0, "symbol": "$"},
    "CO": {"code": "COP", "rate": 4200.0, "symbol": "$"},
    "CL": {"code": "CLP", "rate": 940.0, "symbol": "$"},
    "BR": {"code": "BRL", "rate": 5.0, "symbol": "R$"},
    "PE": {"code": "PEN", "rate": 3.8, "symbol": "S/"},
}


def get_local_currency_display(country_code: str, price_usd_cents: int) -> Optional[Dict]:
    """
    Get local currency display for a country.

    Returns dict with local price info, or None if no local currency configured.
    """
    country_code = country_code.upper()

    if country_code not in EXCHANGE_RATES:
        return None

    currency_info = EXCHANGE_RATES[country_code]
    price_usd = price_usd_cents / 100
    local_price = price_usd * currency_info["rate"]

    # Round to nearest 100 for cleaner display
    if local_price > 1000:
        local_price = round(local_price / 100) * 100
    else:
        local_price = round(local_price)

    return {
        "currency_code": currency_info["code"],
        "symbol": currency_info["symbol"],
        "amount": local_price,
        "display": f"{currency_info['symbol']}{local_price:,.0f}",
    }


# =============================================================================
# PRICING FUNCTIONS
# =============================================================================

@dataclass
class PriceResult:
    """Result of a price calculation."""
    size_key: str
    region_key: str
    country_code: str
    price_cents: int
    price_usd: float
    price_display: str
    local_currency: Optional[Dict]
    size: Size
    region: Region

    def to_dict(self) -> dict:
        return {
            "size_key": self.size_key,
            "region_key": self.region_key,
            "country_code": self.country_code,
            "price_cents": self.price_cents,
            "price_usd": self.price_usd,
            "price_display": self.price_display,
            "local_currency": self.local_currency,
            "size": {
                "key": self.size.key,
                "name": self.size.name,
                "name_es": self.size.name_es,
                "height_mm": self.size.height_mm,
            },
            "region": {
                "key": self.region.key,
                "name": self.region.name,
                "name_es": self.region.name_es,
            },
        }


def calculate_price(size_key: str, country_code: str) -> PriceResult:
    """
    Calculate price for a size and country.

    Args:
        size_key: Size key (mini, small, medium, large)
        country_code: ISO 3166-1 alpha-2 country code

    Returns:
        PriceResult with all pricing details

    Raises:
        ValueError: If size_key is invalid
    """
    if size_key not in SIZES:
        raise ValueError(f"Invalid size: {size_key}. Valid: {list(SIZES.keys())}")

    size = SIZES[size_key]
    region = get_region_for_country(country_code)

    price_cents = PRICES[region.key][size_key]
    price_usd = price_cents / 100

    local_currency = get_local_currency_display(country_code, price_cents)

    return PriceResult(
        size_key=size_key,
        region_key=region.key,
        country_code=country_code.upper(),
        price_cents=price_cents,
        price_usd=price_usd,
        price_display=f"${price_usd:.0f}",
        local_currency=local_currency,
        size=size,
        region=region,
    )


def get_all_prices_for_country(country_code: str) -> List[PriceResult]:
    """Get prices for all sizes for a specific country."""
    return [calculate_price(size_key, country_code) for size_key in SIZES.keys()]


def get_price_table(country_code: str) -> Dict:
    """
    Get a complete price table for a country.

    Useful for displaying pricing UI.
    """
    region = get_region_for_country(country_code)

    sizes = []
    for size_key, size in SIZES.items():
        price_result = calculate_price(size_key, country_code)
        sizes.append({
            "key": size_key,
            "name": size.name,
            "name_es": size.name_es,
            "height_mm": size.height_mm,
            "description": size.description,
            "description_es": size.description_es,
            "price_cents": price_result.price_cents,
            "price_usd": price_result.price_usd,
            "price_display": price_result.price_display,
            "local_currency": price_result.local_currency,
        })

    return {
        "country_code": country_code.upper(),
        "region": {
            "key": region.key,
            "name": region.name,
            "name_es": region.name_es,
        },
        "currency": "USD",
        "sizes": sizes,
    }


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    "Region",
    "Size",
    "PriceResult",
    "REGIONS",
    "SIZES",
    "PRICES",
    "get_region_for_country",
    "calculate_price",
    "get_all_prices_for_country",
    "get_price_table",
    "get_local_currency_display",
]

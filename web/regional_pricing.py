"""
Regional pricing configuration for POSSIBLE.

Competitive pricing differentiated by region (LATAM vs USA/Canada).
LATAM prices are lower to penetrate the Mexican/Latin American market.
Includes shipping configuration.

Updated: 2026-02 - Competitive pricing analysis
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional
from enum import Enum


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
    currency_display: str
    price_multiplier: float  # 1.0 = base (LATAM), 1.25 = USA premium


REGIONS: Dict[str, Region] = {
    "latam": Region(
        key="latam",
        name="Latin America",
        name_es="Latinoamérica",
        countries=[
            "MX",  # Mexico (primary market)
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
        price_multiplier=1.0,  # Base pricing
    ),
    "usa": Region(
        key="usa",
        name="USA & Canada",
        name_es="EE.UU. y Canadá",
        countries=["US", "CA"],
        currency_display="USD",
        price_multiplier=1.25,  # 25% premium
    ),
    "europe": Region(
        key="europe",
        name="Europe",
        name_es="Europa",
        countries=[
            "ES", "FR", "DE", "IT", "PT", "GB", "NL", "BE", "AT", "CH",
            "PL", "CZ", "SE", "NO", "DK", "FI", "IE", "GR",
        ],
        currency_display="USD",
        price_multiplier=1.35,  # 35% premium (higher shipping)
    ),
}

DEFAULT_REGION = "latam"


def get_region_for_country(country_code: str) -> Region:
    """Get the pricing region for a country code."""
    country_code = country_code.upper()

    for region in REGIONS.values():
        if country_code in region.countries:
            return region

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
        description="Keychain, desk toy",
        description_es="Llavero, juguete de escritorio",
    ),
    "small": Size(
        key="small",
        name="Small",
        name_es="Pequeño",
        height_mm=75,
        description="Desk figure, collectible",
        description_es="Figura de escritorio, coleccionable",
    ),
    "medium": Size(
        key="medium",
        name="Medium",
        name_es="Mediano",
        height_mm=100,
        description="Display piece, gift",
        description_es="Pieza de exhibición, regalo",
    ),
    "large": Size(
        key="large",
        name="Large",
        name_es="Grande",
        height_mm=150,
        description="Statement piece, premium gift",
        description_es="Pieza destacada, regalo premium",
    ),
    "xl": Size(
        key="xl",
        name="XL",
        name_es="Extra Grande",
        height_mm=200,
        description="Exhibition piece, centerpiece",
        description_es="Pieza de exhibición, centro de mesa",
    ),
}


# =============================================================================
# MATERIALS
# =============================================================================

class MaterialType(Enum):
    PLASTIC_WHITE = "plastic_white"
    PLASTIC_COLOR = "plastic_color"
    RESIN_PREMIUM = "resin_premium"
    FULL_COLOR = "full_color"
    METAL = "metal"


@dataclass(frozen=True)
class Material:
    """A print material option."""
    key: str
    name: str
    name_es: str
    description: str
    description_es: str
    quality_tier: str  # "standard", "premium", "luxury"


MATERIALS: Dict[str, Material] = {
    "plastic_white": Material(
        key="plastic_white",
        name="White Plastic",
        name_es="Plástico Blanco",
        description="Affordable, matte finish. Great for prototypes.",
        description_es="Económico, acabado mate. Ideal para prototipos.",
        quality_tier="standard",
    ),
    "plastic_color": Material(
        key="plastic_color",
        name="Colored Plastic",
        name_es="Plástico Color",
        description="Durable nylon in your favorite color.",
        description_es="Nylon duradero en tu color favorito.",
        quality_tier="standard",
    ),
    "resin_premium": Material(
        key="resin_premium",
        name="Premium Resin",
        name_es="Resina Premium",
        description="High detail, smooth surface. Museum quality.",
        description_es="Alto detalle, superficie lisa. Calidad museo.",
        quality_tier="premium",
    ),
    "full_color": Material(
        key="full_color",
        name="Full Color",
        name_es="Full Color",
        description="Prints the exact colors from your design.",
        description_es="Imprime los colores exactos de tu diseño.",
        quality_tier="premium",
    ),
    "metal": Material(
        key="metal",
        name="Stainless Steel",
        name_es="Acero Inoxidable",
        description="Real metal. Heavy, durable, impressive.",
        description_es="Metal real. Pesado, duradero, impresionante.",
        quality_tier="luxury",
    ),
}


# =============================================================================
# PRICING MATRIX (LATAM Base Prices in USD cents)
# =============================================================================

# Base prices for LATAM region (primary market)
# Anchor points: Mini $39.90, Medium $79.90, Large $149.90 (for standard plastic)
# USA/Canada = base * 1.25, Europe = base * 1.35
BASE_PRICES: Dict[str, Dict[str, int]] = {
    # Material -> Size -> Price in cents
    "plastic_white": {
        "mini": 3990,      # $39.90
        "small": 5990,     # $59.90
        "medium": 7990,    # $79.90
        "large": 14990,    # $149.90
        "xl": 19990,       # $199.90
    },
    "plastic_color": {
        "mini": 4990,      # $49.90
        "small": 6990,     # $69.90
        "medium": 9990,    # $99.90
        "large": 17990,    # $179.90
        "xl": 24990,       # $249.90
    },
    "resin_premium": {
        "mini": 6990,      # $69.90
        "small": 9990,     # $99.90
        "medium": 14990,   # $149.90
        "large": 24990,    # $249.90
        "xl": 34990,       # $349.90
    },
    "full_color": {
        "mini": 8990,      # $89.90
        "small": 12990,    # $129.90
        "medium": 17990,   # $179.90
        "large": 29990,    # $299.90
        "xl": 44990,       # $449.90
    },
    "metal": {
        "mini": 14990,     # $149.90
        "small": 24990,    # $249.90
        "medium": 34990,   # $349.90
        "large": 54990,    # $549.90
        "xl": 79990,       # $799.90
    },
}


# =============================================================================
# SHIPPING CONFIGURATION
# =============================================================================

@dataclass(frozen=True)
class ShippingOption:
    """A shipping option."""
    key: str
    name: str
    name_es: str
    price_cents: int
    estimated_days_min: int
    estimated_days_max: int
    carrier: str


@dataclass(frozen=True)
class ShippingZone:
    """Shipping zone with options and free shipping threshold."""
    key: str
    name: str
    free_shipping_threshold_cents: int  # 0 = no free shipping
    options: List[ShippingOption]


SHIPPING_ZONES: Dict[str, ShippingZone] = {
    "mx_metro": ShippingZone(
        key="mx_metro",
        name="Mexico Metro (CDMX, GDL, MTY)",
        free_shipping_threshold_cents=7990,  # Free above $79.90 (Medium+)
        options=[
            ShippingOption(
                key="standard",
                name="Standard",
                name_es="Estándar",
                price_cents=990,  # $9.90
                estimated_days_min=3,
                estimated_days_max=5,
                carrier="Estafeta Terrestre",
            ),
            ShippingOption(
                key="express",
                name="Express",
                name_es="Express",
                price_cents=1490,  # $14.90
                estimated_days_min=1,
                estimated_days_max=2,
                carrier="Estafeta Express",
            ),
        ],
    ),
    "mx_national": ShippingZone(
        key="mx_national",
        name="Mexico National",
        free_shipping_threshold_cents=14990,  # Free above $149.90 (Large+)
        options=[
            ShippingOption(
                key="standard",
                name="Standard",
                name_es="Estándar",
                price_cents=1290,  # $12.90
                estimated_days_min=4,
                estimated_days_max=7,
                carrier="Estafeta Terrestre",
            ),
            ShippingOption(
                key="express",
                name="Express",
                name_es="Express",
                price_cents=1990,  # $19.90
                estimated_days_min=2,
                estimated_days_max=3,
                carrier="Estafeta Express",
            ),
        ],
    ),
    "latam": ShippingZone(
        key="latam",
        name="Latin America",
        free_shipping_threshold_cents=17990,  # Free above $179.90
        options=[
            ShippingOption(
                key="standard",
                name="Standard",
                name_es="Estándar",
                price_cents=1990,  # $19.90
                estimated_days_min=7,
                estimated_days_max=14,
                carrier="DHL/FedEx Economy",
            ),
            ShippingOption(
                key="express",
                name="Express",
                name_es="Express",
                price_cents=3490,  # $34.90
                estimated_days_min=3,
                estimated_days_max=5,
                carrier="DHL Express",
            ),
        ],
    ),
    "usa_canada": ShippingZone(
        key="usa_canada",
        name="USA & Canada",
        free_shipping_threshold_cents=14990,  # Free above $149.90
        options=[
            ShippingOption(
                key="standard",
                name="Standard",
                name_es="Estándar",
                price_cents=1490,  # $14.90
                estimated_days_min=5,
                estimated_days_max=10,
                carrier="FedEx Connect+",
            ),
            ShippingOption(
                key="express",
                name="Express",
                name_es="Express",
                price_cents=2990,  # $29.90
                estimated_days_min=2,
                estimated_days_max=4,
                carrier="FedEx International Priority",
            ),
        ],
    ),
    "europe": ShippingZone(
        key="europe",
        name="Europe",
        free_shipping_threshold_cents=24990,  # Free above $249.90
        options=[
            ShippingOption(
                key="standard",
                name="Standard",
                name_es="Estándar",
                price_cents=2990,  # $29.90
                estimated_days_min=10,
                estimated_days_max=20,
                carrier="DHL Economy",
            ),
            ShippingOption(
                key="express",
                name="Express",
                name_es="Express",
                price_cents=4990,  # $49.90
                estimated_days_min=4,
                estimated_days_max=7,
                carrier="DHL Express",
            ),
        ],
    ),
    "rest_of_world": ShippingZone(
        key="rest_of_world",
        name="Rest of World",
        free_shipping_threshold_cents=29990,  # Free above $299.90
        options=[
            ShippingOption(
                key="standard",
                name="Standard",
                name_es="Estándar",
                price_cents=3990,  # $39.90
                estimated_days_min=14,
                estimated_days_max=30,
                carrier="DHL Economy",
            ),
            ShippingOption(
                key="express",
                name="Express",
                name_es="Express",
                price_cents=5990,  # $59.90
                estimated_days_min=5,
                estimated_days_max=10,
                carrier="DHL Express",
            ),
        ],
    ),
}

# Mexico metro area postal codes (first 2-3 digits)
MX_METRO_POSTAL_PREFIXES = [
    # CDMX
    "01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12", "13", "14", "15", "16",
    # Guadalajara
    "44", "45",
    # Monterrey
    "64", "65", "66", "67",
]


def get_shipping_zone(country_code: str, postal_code: Optional[str] = None) -> ShippingZone:
    """
    Determine shipping zone based on country and postal code.

    Args:
        country_code: ISO 3166-1 alpha-2 country code
        postal_code: Optional postal/ZIP code for Mexico metro detection

    Returns:
        ShippingZone for the destination
    """
    country_code = country_code.upper()

    # Mexico - check for metro area
    if country_code == "MX":
        if postal_code:
            prefix = postal_code[:2]
            if prefix in MX_METRO_POSTAL_PREFIXES:
                return SHIPPING_ZONES["mx_metro"]
        return SHIPPING_ZONES["mx_national"]

    # USA & Canada
    if country_code in ["US", "CA"]:
        return SHIPPING_ZONES["usa_canada"]

    # LATAM
    latam_countries = REGIONS["latam"].countries
    if country_code in latam_countries and country_code != "MX":
        return SHIPPING_ZONES["latam"]

    # Europe
    if country_code in REGIONS.get("europe", Region("", "", "", [], "", 1.0)).countries:
        return SHIPPING_ZONES["europe"]

    # Rest of world
    return SHIPPING_ZONES["rest_of_world"]


# =============================================================================
# LOCAL CURRENCY DISPLAY
# =============================================================================

EXCHANGE_RATES: Dict[str, Dict[str, any]] = {
    "MX": {"code": "MXN", "rate": 20.5, "symbol": "$"},
    "AR": {"code": "ARS", "rate": 1050.0, "symbol": "$"},
    "CO": {"code": "COP", "rate": 4300.0, "symbol": "$"},
    "CL": {"code": "CLP", "rate": 980.0, "symbol": "$"},
    "BR": {"code": "BRL", "rate": 5.2, "symbol": "R$"},
    "PE": {"code": "PEN", "rate": 3.85, "symbol": "S/"},
}


def get_local_currency_display(country_code: str, price_usd_cents: int) -> Optional[Dict]:
    """Get local currency display for a country."""
    country_code = country_code.upper()

    if country_code not in EXCHANGE_RATES:
        return None

    currency_info = EXCHANGE_RATES[country_code]
    price_usd = price_usd_cents / 100
    local_price = price_usd * currency_info["rate"]

    # Round for cleaner display
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
    material_key: str
    region_key: str
    country_code: str

    # Product price
    base_price_cents: int      # LATAM base
    regional_price_cents: int  # After regional multiplier

    # Shipping
    shipping_zone_key: str
    shipping_options: List[Dict]
    free_shipping_threshold_cents: int
    qualifies_for_free_shipping: bool

    # Display
    price_usd: float
    price_display: str
    local_currency: Optional[Dict]

    # References
    size: Size
    material: Material
    region: Region

    def to_dict(self) -> dict:
        return {
            "size_key": self.size_key,
            "material_key": self.material_key,
            "region_key": self.region_key,
            "country_code": self.country_code,
            "base_price_cents": self.base_price_cents,
            "regional_price_cents": self.regional_price_cents,
            "price_cents": self.regional_price_cents,  # Alias for compatibility
            "price_usd": self.price_usd,
            "price_display": self.price_display,
            "local_currency": self.local_currency,
            "shipping": {
                "zone": self.shipping_zone_key,
                "options": self.shipping_options,
                "free_threshold_cents": self.free_shipping_threshold_cents,
                "free_threshold_display": f"${self.free_shipping_threshold_cents / 100:.0f}",
                "qualifies_for_free": self.qualifies_for_free_shipping,
            },
            "size": {
                "key": self.size.key,
                "name": self.size.name,
                "name_es": self.size.name_es,
                "height_mm": self.size.height_mm,
                "description": self.size.description,
                "description_es": self.size.description_es,
            },
            "material": {
                "key": self.material.key,
                "name": self.material.name,
                "name_es": self.material.name_es,
                "description": self.material.description,
                "description_es": self.material.description_es,
                "quality_tier": self.material.quality_tier,
            },
            "region": {
                "key": self.region.key,
                "name": self.region.name,
                "name_es": self.region.name_es,
            },
        }


def calculate_price(
    material_key: str,
    size_key: str,
    country_code: str,
    postal_code: Optional[str] = None,
) -> PriceResult:
    """
    Calculate price for a material, size, and destination.

    Args:
        material_key: Material key
        size_key: Size key
        country_code: ISO 3166-1 alpha-2 country code
        postal_code: Optional postal code for Mexico metro detection

    Returns:
        PriceResult with all pricing and shipping details

    Raises:
        ValueError: If material or size not found
    """
    if material_key not in MATERIALS:
        raise ValueError(f"Invalid material: {material_key}. Valid: {list(MATERIALS.keys())}")

    if size_key not in SIZES:
        raise ValueError(f"Invalid size: {size_key}. Valid: {list(SIZES.keys())}")

    material = MATERIALS[material_key]
    size = SIZES[size_key]
    region = get_region_for_country(country_code)
    shipping_zone = get_shipping_zone(country_code, postal_code)

    # Calculate price
    base_price = BASE_PRICES[material_key][size_key]
    regional_price = int(base_price * region.price_multiplier)

    # Round to nearest dollar for cleaner display
    regional_price = round(regional_price / 100) * 100

    # Check free shipping
    qualifies_for_free = regional_price >= shipping_zone.free_shipping_threshold_cents

    # Build shipping options
    shipping_options = []
    for opt in shipping_zone.options:
        shipping_options.append({
            "key": opt.key,
            "name": opt.name,
            "name_es": opt.name_es,
            "price_cents": 0 if qualifies_for_free else opt.price_cents,
            "price_display": "Free" if qualifies_for_free else f"${opt.price_cents / 100:.0f}",
            "estimated_days": f"{opt.estimated_days_min}-{opt.estimated_days_max}",
            "carrier": opt.carrier,
        })

    price_usd = regional_price / 100
    local_currency = get_local_currency_display(country_code, regional_price)

    return PriceResult(
        size_key=size_key,
        material_key=material_key,
        region_key=region.key,
        country_code=country_code.upper(),
        base_price_cents=base_price,
        regional_price_cents=regional_price,
        shipping_zone_key=shipping_zone.key,
        shipping_options=shipping_options,
        free_shipping_threshold_cents=shipping_zone.free_shipping_threshold_cents,
        qualifies_for_free_shipping=qualifies_for_free,
        price_usd=price_usd,
        price_display=f"${price_usd:.0f}",
        local_currency=local_currency,
        size=size,
        material=material,
        region=region,
    )


def get_price_table(country_code: str, postal_code: Optional[str] = None) -> Dict:
    """
    Get complete price table for a destination.

    Returns all material × size combinations with shipping info.
    """
    region = get_region_for_country(country_code)
    shipping_zone = get_shipping_zone(country_code, postal_code)

    materials_data = []
    for material_key, material in MATERIALS.items():
        sizes_data = []
        for size_key, size in SIZES.items():
            price = calculate_price(material_key, size_key, country_code, postal_code)
            sizes_data.append({
                "size_key": size_key,
                "size_name": size.name,
                "size_name_es": size.name_es,
                "height_mm": size.height_mm,
                "price_cents": price.regional_price_cents,
                "price_display": price.price_display,
                "local_currency": price.local_currency,
                "free_shipping": price.qualifies_for_free_shipping,
            })

        materials_data.append({
            "material_key": material_key,
            "material_name": material.name,
            "material_name_es": material.name_es,
            "description": material.description,
            "description_es": material.description_es,
            "quality_tier": material.quality_tier,
            "sizes": sizes_data,
        })

    return {
        "country_code": country_code.upper(),
        "region": {
            "key": region.key,
            "name": region.name,
            "name_es": region.name_es,
            "price_multiplier": region.price_multiplier,
        },
        "shipping": {
            "zone": shipping_zone.key,
            "zone_name": shipping_zone.name,
            "free_threshold_cents": shipping_zone.free_shipping_threshold_cents,
            "free_threshold_display": f"${shipping_zone.free_shipping_threshold_cents / 100:.0f}",
            "options": [
                {
                    "key": opt.key,
                    "name": opt.name,
                    "price_cents": opt.price_cents,
                    "price_display": f"${opt.price_cents / 100:.0f}",
                    "estimated_days": f"{opt.estimated_days_min}-{opt.estimated_days_max}",
                    "carrier": opt.carrier,
                }
                for opt in shipping_zone.options
            ],
        },
        "currency": "USD",
        "materials": materials_data,
    }


def calculate_order_total(
    items: List[Dict],  # [{"material_key": str, "size_key": str, "quantity": int}]
    country_code: str,
    postal_code: Optional[str] = None,
    shipping_option: str = "standard",
) -> Dict:
    """
    Calculate total for an order with multiple items.

    Returns subtotal, shipping, and total with free shipping logic.
    """
    shipping_zone = get_shipping_zone(country_code, postal_code)

    subtotal_cents = 0
    items_detail = []

    for item in items:
        price = calculate_price(
            item["material_key"],
            item["size_key"],
            country_code,
            postal_code,
        )
        quantity = item.get("quantity", 1)
        item_total = price.regional_price_cents * quantity
        subtotal_cents += item_total

        items_detail.append({
            "material_key": item["material_key"],
            "size_key": item["size_key"],
            "quantity": quantity,
            "unit_price_cents": price.regional_price_cents,
            "unit_price_display": price.price_display,
            "total_cents": item_total,
            "total_display": f"${item_total / 100:.0f}",
        })

    # Determine shipping cost
    qualifies_for_free = subtotal_cents >= shipping_zone.free_shipping_threshold_cents

    shipping_cents = 0
    shipping_option_detail = None
    for opt in shipping_zone.options:
        if opt.key == shipping_option:
            shipping_option_detail = opt
            shipping_cents = 0 if qualifies_for_free else opt.price_cents
            break

    if not shipping_option_detail:
        # Default to first option
        shipping_option_detail = shipping_zone.options[0]
        shipping_cents = 0 if qualifies_for_free else shipping_option_detail.price_cents

    total_cents = subtotal_cents + shipping_cents

    # Amount needed for free shipping
    amount_to_free_shipping = max(0, shipping_zone.free_shipping_threshold_cents - subtotal_cents)

    return {
        "items": items_detail,
        "subtotal_cents": subtotal_cents,
        "subtotal_display": f"${subtotal_cents / 100:.0f}",
        "shipping": {
            "option": shipping_option_detail.key,
            "name": shipping_option_detail.name,
            "carrier": shipping_option_detail.carrier,
            "estimated_days": f"{shipping_option_detail.estimated_days_min}-{shipping_option_detail.estimated_days_max}",
            "price_cents": shipping_cents,
            "price_display": "Free" if qualifies_for_free else f"${shipping_cents / 100:.0f}",
            "is_free": qualifies_for_free,
        },
        "free_shipping": {
            "threshold_cents": shipping_zone.free_shipping_threshold_cents,
            "threshold_display": f"${shipping_zone.free_shipping_threshold_cents / 100:.0f}",
            "qualifies": qualifies_for_free,
            "amount_needed_cents": amount_to_free_shipping,
            "amount_needed_display": f"${amount_to_free_shipping / 100:.0f}" if amount_to_free_shipping > 0 else None,
        },
        "total_cents": total_cents,
        "total_display": f"${total_cents / 100:.0f}",
        "local_currency": get_local_currency_display(country_code, total_cents),
    }


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    # Classes
    "Region",
    "Size",
    "Material",
    "MaterialType",
    "ShippingOption",
    "ShippingZone",
    "PriceResult",
    # Data
    "REGIONS",
    "SIZES",
    "MATERIALS",
    "BASE_PRICES",
    "SHIPPING_ZONES",
    "EXCHANGE_RATES",
    # Functions
    "get_region_for_country",
    "get_shipping_zone",
    "get_local_currency_display",
    "calculate_price",
    "get_price_table",
    "calculate_order_total",
]

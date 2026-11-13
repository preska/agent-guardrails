"""Sales tax by region. Rates are strings so they become exact Decimals."""

from decimal import Decimal

RATES = {
    "IL": Decimal("0.0625"),
    "NY": Decimal("0.04"),
    "OR": Decimal("0"),
}


def tax_for(region: str, amount: Decimal) -> Decimal:
    return amount * RATES.get(region, Decimal("0"))

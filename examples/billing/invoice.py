"""Invoices for the example billing service.

Amounts are Decimal end to end. A float anywhere in here would round
0.1 + 0.2 into 0.30000000000000004 and someone's invoice would be off by a cent.
"""

from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal

from examples.billing.tax import tax_for

CENT = Decimal("0.01")


@dataclass
class Line:
    description: str
    quantity: int
    unit_price: Decimal

    @property
    def amount(self) -> Decimal:
        return self.unit_price * self.quantity


@dataclass
class Invoice:
    number: str
    region: str
    lines: list[Line] = field(default_factory=list)

    def add(self, description: str, quantity: int, unit_price: str) -> None:
        self.lines.append(Line(description, quantity, Decimal(unit_price)))

    @property
    def subtotal(self) -> Decimal:
        return sum((line.amount for line in self.lines), Decimal("0"))

    @property
    def total(self) -> Decimal:
        total = self.subtotal + tax_for(self.region, self.subtotal)
        return total.quantize(CENT, rounding=ROUND_HALF_UP)

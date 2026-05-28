"""Modelo de datos para el resultado del motor de pricing."""

from datetime import date
from decimal import Decimal

from pydantic import ConfigDict
from pydantic.dataclasses import dataclass


@dataclass(config=ConfigDict(frozen=True))
class PricingScenario:
    """Resultado del cálculo de pricing para una habitación en una fecha.

    Es el *output* del motor — no se valida en creación sino que se
    genera internamente.
    """

    date: date
    room_category_id: str
    suggested_price: Decimal
    breakeven_price: Decimal
    marginal_cost: Decimal
    fixed_cost_allocated: Decimal
    expected_occupancy: Decimal
    expected_revenue: Decimal
    expected_profit: Decimal
    seasonal_coefficient_applied: str | None = None
    ota_commission_pct: Decimal

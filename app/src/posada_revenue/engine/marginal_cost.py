"""Cálculo del coste marginal por estancia.

Todas las funciones son **puras**: sin estado, sin E/S.
"""

from decimal import Decimal

from posada_revenue.money import eur
from posada_revenue.models.costs import VariableCost
from posada_revenue.models.room import RoomCategory


def marginal_cost(
    room: RoomCategory,
    occupancy_rate: Decimal,
    variable_costs: list[VariableCost],
) -> Decimal:
    """Calcula el coste marginal por estancia para una categoría de
    habitación.

    La fórmula incorpora un factor de fricción que crece con la
    ocupación:

    .. math::

        base = \sum VC_{\text{per\_stay}} + amenities\_cost \\
        friction = 1 + 0.15 \times occupancy\_rate^2 \\
        mc = base \times friction

    NO incluye comisión OTA (se aplica en ``breakeven_price``).

    Parameters
    ----------
    room : RoomCategory
        Categoría de habitación.
    occupancy_rate : Decimal
        Tasa de ocupación esperada (0‑1).
    variable_costs : list[VariableCost]
        Lista de costes variables.

    Returns
    -------
    Decimal
        Coste marginal por estancia redondeado a 2 decimales.
    """
    base = room.amenities_cost
    for vc in variable_costs:
        if vc.unit == "per_stay":
            if not vc.applies_to or room.id in vc.applies_to:
                base += vc.amount

    friction = Decimal("1") + Decimal("0.15") * (occupancy_rate ** 2)
    return eur(base * friction)

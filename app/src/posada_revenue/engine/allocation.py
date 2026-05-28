"""Imputación de costes fijos a categorías de habitación.

Todas las funciones son **puras**: sin estado, sin E/S.
"""

from decimal import Decimal

from posada_revenue.models.costs import FixedCost
from posada_revenue.models.room import RoomCategory
from posada_revenue.models.business_line import BusinessLine
from posada_revenue.money import eur


def allocate_fixed_costs_to_room(
    room: RoomCategory,
    all_rooms: list[RoomCategory],
    fixed_costs: list[FixedCost],
    business_lines: list[BusinessLine],
) -> Decimal:
    """Calcula el coste fijo **diario** imputado a una habitación de esta
    categoría.

    Para cada coste fijo se aplica el método de reparto indicado:

    * ``per_room``: ``monthly_amount / total_rooms``
    * ``per_sqm``: ``monthly_amount * (room.sqm / total_sqm)``
    * ``per_business_line``: se busca la línea de negocio cuyo ``id``
      coincide con ``FixedCost.business_line`` y se calcula
      ``monthly_amount * BL.revenue_weight / total_rooms``

    El total mensual se divide entre 30 para obtener el valor diario.

    Parameters
    ----------
    room : RoomCategory
        Categoría destino del cálculo.
    all_rooms : list[RoomCategory]
        Todas las categorías del hotel (para totales).
    fixed_costs : list[FixedCost]
        Lista de costes fijos a imputar.
    business_lines : list[BusinessLine]
        Líneas de negocio (para el método ``per_business_line``).

    Returns
    -------
    Decimal
        Coste fijo diario imputado a una habitación de esta categoría
        (redondeado a 2 decimales).
    """
    total_rooms = sum(r.units_available for r in all_rooms)
    total_sqm = sum(r.sqm * r.units_available for r in all_rooms)
    bl_map = {bl.id: bl for bl in business_lines}

    monthly_total = Decimal("0")

    for fc in fixed_costs:
        if fc.allocation_method == "per_room":
            share = fc.monthly_amount / Decimal(str(total_rooms))
            monthly_total += share

        elif fc.allocation_method == "per_sqm":
            share = fc.monthly_amount * (room.sqm / total_sqm)
            monthly_total += share

        elif fc.allocation_method == "per_business_line":
            bl = bl_map.get(fc.business_line)
            if bl is not None:
                share = fc.monthly_amount * bl.revenue_weight / Decimal(str(total_rooms))
                monthly_total += share
            # Si no se encuentra la BL, se omite este coste

    return eur(monthly_total / Decimal("30"))

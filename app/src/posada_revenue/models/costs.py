"""Modelos de datos para costes fijos y variables."""

from decimal import Decimal
from typing import Literal

from pydantic import ConfigDict, Field
from pydantic.dataclasses import dataclass


@dataclass(config=ConfigDict(frozen=True))
class FixedCost:
    """Coste fijo mensual imputable a una línea de negocio.

    Parameters
    ----------
    id : str
        Identificador único del coste.
    concept : str
        Concepto o descripción (ej. ``"Alquiler"``).
    monthly_amount : Decimal
        Importe mensual en EUR.
    allocation_method : Literal["per_room", "per_sqm", "per_business_line"]
        Criterio de reparto:
        - ``per_room``: se divide a partes iguales entre todas las habitaciones.
        - ``per_sqm``: se prorratea por superficie.
        - ``per_business_line``: se prorratea según *revenue_weight* de la línea.
    business_line : str
        Línea de negocio a la que pertenece (``"alojamiento"``,
        ``"restauracion"``, ``"eventos"``).
    """

    id: str
    concept: str
    monthly_amount: Decimal = Field(ge=0)
    allocation_method: Literal["per_room", "per_sqm", "per_business_line"]
    business_line: str


@dataclass(config=ConfigDict(frozen=True))
class VariableCost:
    """Coste variable por estancia o por noche.

    Parameters
    ----------
    id : str
        Identificador único.
    concept : str
        Concepto (ej. ``"Limpieza"``).
    unit : Literal["per_stay", "per_night", "percent_of_revenue"]
        Unidad de aplicación.
    amount : Decimal
        Importe (EUR para ``per_stay``/``per_night``, ratio 0‑1 para
        ``percent_of_revenue``).
    applies_to : list[str]
        Lista de ``id`` de ``RoomCategory`` a los que aplica. Vacío =
        aplica a todas las categorías.
    """

    id: str
    concept: str
    unit: Literal["per_stay", "per_night", "percent_of_revenue"]
    amount: Decimal = Field(ge=0)
    applies_to: list[str] = Field(default_factory=list)

"""Modelo de datos para líneas de negocio."""

from decimal import Decimal

from pydantic import ConfigDict, Field
from pydantic.dataclasses import dataclass


@dataclass(config=ConfigDict(frozen=True))
class BusinessLine:
    """Línea de negocio del hotel.

    Parameters
    ----------
    id : str
        Identificador (``"alojamiento"``, ``"restauracion"``, ``"eventos"``).
    revenue_weight : Decimal
        Peso relativo en los ingresos totales (0‑1). La suma de todos
        los pesos debe ser 1 ± 0.0001.
    target_margin : Decimal
        Margen objetivo de la línea (0‑1).
    """

    id: str
    revenue_weight: Decimal = Field(ge=0, le=1)
    target_margin: Decimal = Field(ge=0, le=1)

"""Modelo de datos para coeficientes estacionales."""

from datetime import date
from decimal import Decimal

from pydantic import ConfigDict, Field, model_validator
from pydantic.dataclasses import dataclass


@dataclass(config=ConfigDict(frozen=True))
class SeasonalCoefficient:
    """Coeficiente estacional que modifica precios y ocupación esperada
    en un ventana de fechas.

    Parameters
    ----------
    id : str
        Identificador único.
    name : str
        Nombre descriptivo (ej. ``"Semana Santa 2026"``).
    start_date : date
        Inicio del período (incluido).
    end_date : date
        Fin del período (incluido).
    demand_multiplier : Decimal
        Factor multiplicador de demanda/precio base.
    price_floor_multiplier : Decimal
        Factor que eleva el suelo de precio.
    price_ceiling_multiplier : Decimal
        Factor que eleva el techo de precio.
    expected_occupancy : Decimal
        Ocupación esperada en el período (0‑1).
    priority : int
        Prioridad para resolución de solapamientos. A mayor valor,
        mayor prioridad.

    Validaciones
    ------------
    - ``start_date <= end_date``
    - ``0 <= expected_occupancy <= 1``
    """

    id: str
    name: str
    start_date: date
    end_date: date
    demand_multiplier: Decimal = Field(ge=0)
    price_floor_multiplier: Decimal = Field(ge=0)
    price_ceiling_multiplier: Decimal = Field(ge=0)
    expected_occupancy: Decimal = Field(ge=0, le=1)
    priority: int

    @model_validator(mode="after")
    def _check_date_order(self) -> "SeasonalCoefficient":
        if self.start_date > self.end_date:
            raise ValueError(
                f"start_date ({self.start_date}) debe ser <= "
                f"end_date ({self.end_date})"
            )
        return self

"""Modelo de datos para categorías de habitación."""

from decimal import Decimal

from pydantic import ConfigDict, Field, model_validator
from pydantic.dataclasses import dataclass


@dataclass(config=ConfigDict(frozen=True))
class RoomCategory:
    """Categoría de habitación con su inventario y horquilla de precios.

    Parameters
    ----------
    id : str
        Identificador único (ej. ``"doble_std"``).
    name : str
        Nombre comercial (ej. ``"Doble Estándar"``).
    units_available : int
        Número de unidades de esta categoría en el hotel (≥ 1).
    base_rate : Decimal
        Tarifa rack — precio de referencia (EUR).
    floor_rate : Decimal
        Precio mínimo absoluto por noche (EUR).
    ceiling_rate : Decimal
        Tope superior de precio por noche (EUR).
    sqm : Decimal
        Superficie media de la habitación (m²).
    amenities_cost : Decimal
        Coste de amenities por estancia (EUR).

    Validaciones
    ------------
    - ``floor_rate <= base_rate <= ceiling_rate``
    """

    id: str
    name: str
    units_available: int = Field(ge=1)
    base_rate: Decimal = Field(ge=0)
    floor_rate: Decimal = Field(ge=0)
    ceiling_rate: Decimal = Field(ge=0)
    sqm: Decimal = Field(ge=0)
    amenities_cost: Decimal = Field(ge=0)

    @model_validator(mode="after")
    def _check_rate_order(self) -> "RoomCategory":
        if not (self.floor_rate <= self.base_rate <= self.ceiling_rate):
            raise ValueError(
                f"floor_rate ({self.floor_rate}) <= base_rate ({self.base_rate}) "
                f"<= ceiling_rate ({self.ceiling_rate}) no se cumple"
            )
        return self

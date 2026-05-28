"""Helpers monetarios para el sistema de Revenue Management.

Configura el contexto global de ``Decimal`` con precisión 28 y redondeo
``ROUND_HALF_UP``. Toda cantidad monetaria en el sistema usa ``Decimal``,
nunca ``float``.
"""

from decimal import ROUND_HALF_UP, Decimal, getcontext, setcontext

# ── Contexto global Decimal ──────────────────────────────────────────

_DEFAULT_CONTEXT = getcontext().copy()
_DEFAULT_CONTEXT.prec = 28
_DEFAULT_CONTEXT.rounding = ROUND_HALF_UP
setcontext(_DEFAULT_CONTEXT)


# ── Helpers ──────────────────────────────────────────────────────────


def eur(value: str | int | Decimal, rounding: str | None = None) -> Decimal:
    """Convierte un valor a :class:`Decimal` con 2 decimales exactos.

    Parameters
    ----------
    value : str | int | Decimal
        Importe a normalizar.
    rounding : str, optional
        Modo de redondeo opcional (por defecto usa el del contexto global).

    Returns
    -------
    Decimal
        Valor redondeado a 2 decimales.

    Examples
    --------
    >>> eur("23.3945")
    Decimal('23.39')
    >>> eur(100)
    Decimal('100.00')
    """
    if not isinstance(value, Decimal):
        value = Decimal(str(value))
    return value.quantize(Decimal("0.01"), rounding=rounding) if rounding else value.quantize(Decimal("0.01"))


def pct(value: str | int | Decimal) -> Decimal:
    """Convierte un valor a :class:`Decimal` con 4 decimales (para ratios).

    Parameters
    ----------
    value : str | int | Decimal
        Ratio o porcentaje.

    Returns
    -------
    Decimal
        Valor redondeado a 4 decimales.
    """
    if not isinstance(value, Decimal):
        value = Decimal(str(value))
    return value.quantize(Decimal("0.0001"))

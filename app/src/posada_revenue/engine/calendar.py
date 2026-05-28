"""Cómputo de fechas móviles litúrgicas y resolución de ventanas
estacionales.

Todas las funciones son **puras**: sin estado, sin E/S, sin efectos
secundarios.
"""

from datetime import date, timedelta

from posada_revenue.models.seasonality import SeasonalCoefficient


def compute_easter(year: int) -> date:
    """Calcula el Domingo de Resurrección (Pascua) para un año dado
    mediante el algoritmo de Butcher-Meeus (calendario gregoriano).

    Parameters
    ----------
    year : int
        Año gregoriano (≥ 1583).

    Returns
    -------
    date
        Fecha del Domingo de Resurrección.

    Examples
    --------
    >>> compute_easter(2026)
    datetime.date(2026, 4, 5)
    """
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l_ = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l_) // 451
    month = (h + l_ - 7 * m + 114) // 31
    day = ((h + l_ - 7 * m + 114) % 31) + 1
    return date(year, month, day)


def compute_corpus_christi(year: int) -> date:
    """Calcula el jueves de Corpus Christi.

    Corpus Christi = Domingo de Resurrección + 60 días.

    Parameters
    ----------
    year : int
        Año gregoriano (≥ 1583).

    Returns
    -------
    date
        Fecha de Corpus Christi (jueves).

    Examples
    --------
    >>> compute_corpus_christi(2026)
    datetime.date(2026, 6, 4)
    """
    return compute_easter(year) + timedelta(days=60)


def resolve_seasonal_window(
    target_date: date,
    coefficients: list[SeasonalCoefficient],
) -> SeasonalCoefficient | None:
    """Devuelve el coeficiente estacional aplicable a una fecha.

    Si varios coeficientes solapan en la fecha, gana el de mayor
    ``priority``. Si ninguno cubre la fecha retorna ``None``.

    Parameters
    ----------
    target_date : date
        Fecha a evaluar.
    coefficients : list[SeasonalCoefficient]
        Lista de coeficientes estacionales.

    Returns
    -------
    SeasonalCoefficient | None
        Coeficiente aplicable, o ``None`` si no hay ninguno.

    Examples
    --------
    >>> from datetime import date
    >>> from posada_revenue.models.seasonality import SeasonalCoefficient
    >>> from decimal import Decimal
    >>> a = SeasonalCoefficient(
    ...     id="a", name="A",
    ...     start_date=date(2026,6,1), end_date=date(2026,6,10),
    ...     demand_multiplier=Decimal("1"), price_floor_multiplier=Decimal("1"),
    ...     price_ceiling_multiplier=Decimal("1"), expected_occupancy=Decimal("0.5"),
    ...     priority=5)
    >>> b = SeasonalCoefficient(
    ...     id="b", name="B",
    ...     start_date=date(2026,6,3), end_date=date(2026,6,7),
    ...     demand_multiplier=Decimal("1"), price_floor_multiplier=Decimal("1"),
    ...     price_ceiling_multiplier=Decimal("1"), expected_occupancy=Decimal("0.5"),
    ...     priority=10)
    >>> resolve_seasonal_window(date(2026,6,5), [a, b]).id
    'b'
    """
    applicable = [
        c for c in coefficients if c.start_date <= target_date <= c.end_date
    ]
    if not applicable:
        return None
    return max(applicable, key=lambda c: c.priority)

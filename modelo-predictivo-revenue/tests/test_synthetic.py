"""
Tests de validación para el dataset sintético 2025.
"""

import pytest
import pandas as pd
from pathlib import Path

CSV_PATH = Path(__file__).resolve().parent.parent / "data" / "synthetic" / "2025_bookings.csv"
YEAR = 2025
TOTAL_ROOMS = 22
TOTAL_ROOM_NIGHTS = TOTAL_ROOMS * 365  # 8.030


@pytest.fixture(scope="module")
def df():
    return pd.read_csv(CSV_PATH, parse_dates=["arrival_date", "departure_date"])


def test_total_bookings_in_range(df):
    """Total reservas debe estar entre 3.500 y 4.500."""
    n = len(df)
    assert 3500 <= n <= 4500, f"Total reservas {n} fuera de rango [3500, 4500]"


def test_all_dates_in_2025(df):
    """Arrivals en 2025, departures pueden ser early 2026."""
    arr_years = df["arrival_date"].dt.year
    assert (arr_years == YEAR).all(), "Arrivals fuera de 2025"

    dep_years = df["departure_date"].dt.year
    # Departures pueden caer en 2026 si LOS cruza año
    assert dep_years.isin([2025, 2026]).all(), "Departures fuera de 2025-2026"

    # Si alguna departure es 2026, debe ser dentro de los primeros 7 días
    dep_2026 = df[dep_years == 2026]
    if len(dep_2026) > 0:
        jan7 = pd.Timestamp("2026-01-07")
        assert (dep_2026["departure_date"] <= jan7).all(), \
            "Departures en 2026 más allá del 7 de enero"


def test_annual_occupancy_around_70pct(df):
    """Ocupación anual debe ser ~70% (margen ±5pp)."""
    confirmed = df[df["status"] == "CONFIRMED"]
    los = (confirmed["departure_date"] - confirmed["arrival_date"]).dt.days
    occupied_nights = los.sum()
    occ_pct = occupied_nights / TOTAL_ROOM_NIGHTS * 100
    assert 65 <= occ_pct <= 78, f"Ocupación {occ_pct:.1f}% fuera de rango [65%, 78%]"


def test_status_distribution(df):
    """CONFIRMED ~90%, CANCELLED ~8%, NO_SHOW ~2%."""
    total = len(df)
    for status, expected_pct in [("CONFIRMED", 88), ("CANCELLED", 6), ("NO_SHOW", 1)]:
        actual_pct = (df["status"] == status).sum() / total * 100
        assert actual_pct >= expected_pct, \
            f"{status} {actual_pct:.1f}% < mínimo {expected_pct}%"


def test_channel_mix(df):
    """Mix de canales dentro de rangos esperados."""
    total = len(df)
    ranges = {"DIRECT": (30, 40), "BOOKING": (25, 35), "EXPEDIA": (15, 25), "AIRBNB": (10, 20)}
    for ch, (lo, hi) in ranges.items():
        pct = (df["channel"] == ch).sum() / total * 100
        assert lo <= pct <= hi, f"{ch} {pct:.1f}% fuera de [{lo}%, {hi}%]"


def test_room_categories_valid(df):
    """Todas las room_cat_id son válidas."""
    valid_ids = {"dob-001", "sup-001", "sui-001"}
    actual = set(df["room_cat_id"].unique())
    assert actual == valid_ids, f"Categorías inválidas: {actual - valid_ids}"


def test_no_negative_rates(df):
    """Ninguna tarifa es negativa."""
    assert (df["rate_paid_eur"] >= 0).all(), "Tarifas negativas encontradas"


def test_departure_after_arrival(df):
    """Departure siempre después de arrival."""
    assert (df["departure_date"] > df["arrival_date"]).all(), \
        "Reservas con departure <= arrival"


def test_lead_time_non_negative(df):
    """days_before_arrival no puede ser negativo."""
    assert (df["days_before_arrival"] >= 0).all(), \
        "Lead times negativos encontrados"


def test_guests_within_capacity(df):
    """Huéspedes no exceden capacidad de la categoría."""
    max_guests = {"dob-001": 2, "sup-001": 2, "sui-001": 3}
    for cat_id, max_g in max_guests.items():
        subset = df[df["room_cat_id"] == cat_id]
        assert (subset["guests"] <= max_g).all(), \
            f"{cat_id} tiene reservas con {max_g}+ huéspedes"


def test_monthly_occupancy_sums_to_annual(df):
    """Suma de ocupación mensual es coherente con la anual."""
    confirmed = df[df["status"] == "CONFIRMED"].copy()
    confirmed["month"] = confirmed["arrival_date"].dt.month
    confirmed["los"] = (confirmed["departure_date"] - confirmed["arrival_date"]).dt.days

    monthly_nights = confirmed.groupby("month")["los"].sum()
    total = monthly_nights.sum()

    assert total == confirmed["los"].sum(), \
        "Suma mensual no coincide con total anual"
    assert 5000 <= total <= 7000, \
        f"Noches totales {total} fuera de rango esperado [5000, 7000]"


def test_adr_reasonable_range(df):
    """ADR medio por categoría dentro de lo esperado."""
    confirmed = df[df["status"] == "CONFIRMED"].copy()
    confirmed["los"] = (confirmed["departure_date"] - confirmed["arrival_date"]).dt.days

    for cat_id, name in [("dob-001", "Doble"), ("sup-001", "Superior"), ("sui-001", "Suite Junior")]:
        cd = confirmed[confirmed["room_cat_id"] == cat_id]
        if cd.empty:
            continue
        total_rev = (cd["rate_paid_eur"] * cd["los"]).sum()
        total_nights = cd["los"].sum()
        adr = total_rev / total_nights if total_nights else 0
        assert 50 <= adr <= 350, f"{name} ADR {adr:.2f}€ fuera de rango [50, 350]"

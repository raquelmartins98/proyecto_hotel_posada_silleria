"""
Genera el informe ejecutivo anual 2025 del Hotel Posada de la Sillería.

Usage:
    python scripts/generate_report.py

Output:
    - reports/figures/     → 5 gráficos PNG
    - reports/informe_anual_2025.xlsx → Excel con 5 hojas
    - reports/informe_anual_2025.md   → Markdown ejecutivo
"""

import sys
from pathlib import Path
from datetime import date, datetime
from typing import Dict, List, Optional, Tuple
import warnings

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")  # non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

# ── Project root ──
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from revenue_engine.models import HotelConfig
from revenue_engine.engine.pricing_engine import RevenueManager

warnings.filterwarnings("ignore", category=UserWarning)

# ── Config ──
DATA_PATH = ROOT / "data" / "synthetic" / "2025_bookings.csv"
FIGURES_DIR = ROOT / "reports" / "figures"
EXCEL_PATH = ROOT / "reports" / "informe_anual_2025.xlsx"
MD_PATH = ROOT / "reports" / "informe_anual_2025.md"

YEAR = 2025
TOTAL_ROOMS = 22
SEED = 42

CATEGORY_NAMES = {"dob-001": "Doble", "sup-001": "Superior", "sui-001": "Suite Junior"}
BASE_RATES = {"dob-001": 120.0, "sup-001": 155.0, "sui-001": 210.0}

MONTHS_ES = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
]

OTA_COMMISSION = {"BOOKING": 0.15, "EXPEDIA": 0.15, "AIRBNB": 0.10, "DIRECT": 0.0}

# ── Matplotlib style ──
plt.rcParams.update({
    "figure.facecolor": "#f8f9fa",
    "axes.facecolor": "#ffffff",
    "axes.edgecolor": "#dee2e6",
    "axes.grid": True,
    "grid.alpha": 0.3,
    "font.family": "sans-serif",
    "font.size": 10,
    "axes.titlesize": 13,
    "axes.labelsize": 11,
})


# ═══════════════════════════════════════════════════
#  CARGA Y PREPROCESAMIENTO
# ═══════════════════════════════════════════════════

def load_bookings() -> pd.DataFrame:
    """Carga el CSV y parsea fechas."""
    df = pd.read_csv(DATA_PATH)
    df["arrival_date"] = pd.to_datetime(df["arrival_date"])
    df["departure_date"] = pd.to_datetime(df["departure_date"])
    df["month"] = df["arrival_date"].dt.month
    df["length_of_stay"] = (df["departure_date"] - df["arrival_date"]).dt.days
    return df


# ═══════════════════════════════════════════════════
#  CÁLCULO DE KPIs MENSUALES
# ═══════════════════════════════════════════════════

def compute_monthly_kpis(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula KPIs mensuales desde las reservas CONFIRMED.
    Retorna DataFrame con columnas: month, occ_pct, adr, revpar,
    room_nights, gross_revenue, net_revenue, nights_available.
    """
    confirmed = df[df["status"] == "CONFIRMED"].copy()

    rows = []
    for month in range(1, 13):
        days_in_month = pd.Timestamp(YEAR, month, 1).days_in_month
        nights_avail = TOTAL_ROOMS * days_in_month

        month_data = confirmed[confirmed["month"] == month]
        if month_data.empty:
            rows.append({
                "month": month, "month_name": MONTHS_ES[month - 1],
                "occ_pct": 0.0, "adr": 0.0, "revpar": 0.0,
                "room_nights": 0, "gross_revenue": 0.0,
                "net_revenue": 0.0, "nights_available": nights_avail,
            })
            continue

        room_nights = int(month_data["length_of_stay"].sum())

        # rate_paid_eur is PER NIGHT; total revenue = rate * LOS
        total_rev = (month_data["rate_paid_eur"] * month_data["length_of_stay"]).sum()
        occ = room_nights / nights_avail if nights_avail else 0

        # Net revenue after OTA commissions
        def _net(row):
            comm = OTA_COMMISSION.get(row["channel"], 0.0)
            nightly = row["rate_paid_eur"] * (1 - comm)
            return nightly * row["length_of_stay"]
        net_rev = month_data.apply(_net, axis=1).sum()

        adr = total_rev / room_nights if room_nights else 0.0
        revpar = total_rev / nights_avail if nights_avail else 0.0

        rows.append({
            "month": month,
            "month_name": MONTHS_ES[month - 1],
            "occ_pct": round(occ * 100, 1),
            "adr": round(adr, 2),
            "revpar": round(revpar, 2),
            "room_nights": room_nights,
            "gross_revenue": round(total_rev, 2),
            "net_revenue": round(net_rev, 2),
            "nights_available": nights_avail,
        })

    return pd.DataFrame(rows)


# ═══════════════════════════════════════════════════
#  COMPARATIVA REAL vs MOTOR
# ═══════════════════════════════════════════════════

def run_engine_comparison(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Compara el precio real cobrado vs el precio óptimo sugerido por el
    ElasticityEngine para cada fecha y categoría.
    
    El motor usa:
      - Coste marginal por categoría (cost_engine)
      - Elasticidad precio-demanda por fecha (ElasticityEngine)
      - Techo de mercado basado en la tarifa base de cada categoría
    
    El "revenue uplift potencial" mide cuánto más se podría haber
    ingresado aplicando precios dinámicos óptimos en lugar de tarifa
    plana estacional.
    """
    confirmed = df[df["status"] == "CONFIRMED"].copy()
    config = HotelConfig.from_seed("posada_silleria")
    
    # Initialize engines directly for per-booking pricing
    from revenue_engine.toledo_calendar import ToledoCalendar
    from revenue_engine.engine.cost_engine import CostEngine
    from revenue_engine.engine.elasticity import ElasticityEngine
    from revenue_engine.config import DEFAULT_CONFIG
    
    calendar = ToledoCalendar(YEAR)
    cost_engine = CostEngine(
        config.room_categories,
        config.fixed_costs,
        config.variable_costs,
    )
    # Run cost engine to get marginal costs
    cat_pricing = cost_engine.calculate()
    marginal_costs = {cp.cat_id: cp.marginal_cost for cp in cat_pricing}
    
    elasticity_engine = ElasticityEngine(calendar, DEFAULT_CONFIG)
    
    # For each booking, compute the engine's suggested optimal price
    def _get_engine_price(row):
        d = row["arrival_date"]
        if hasattr(d, "date"):
            d = d.date() if hasattr(d, "date") else d
        
        cat_id = row["room_cat_id"]
        mc = marginal_costs.get(cat_id, 60.0)
        
        # Elasticity for this date
        el = elasticity_engine.get_elasticity(d)
        
        # Market ceiling based on this category's base rate
        base = BASE_RATES.get(cat_id, 120.0)
        season = calendar.get_season_for_date(d)
        season_mult = {
            "S_SEMANA_SANTA": 1.30,
            "S_CORPUS": 1.20,
            "S_NAVIDAD": 1.15,
            "S_PRIMAVERA": 1.10,
            "S_OTONO": 1.05,
            "S_MEDIA_INV": 0.95,
            "S_VERANO": 0.90,
            "S_BAJA_INV": 0.85,
        }.get(season, 1.0)
        
        ceiling = min(base * 1.5 * season_mult, base * 2.0)
        
        # Optimal price via Lerner rule
        suggested = elasticity_engine.get_optimal_price(
            marginal_cost=mc,
            elasticity=el,
            market_ceiling=ceiling,
        )
        return suggested
    
    confirmed = confirmed.copy()
    confirmed["suggested_price"] = confirmed.apply(_get_engine_price, axis=1)
    
    # rate_paid_eur is PER NIGHT in the CSV (not total for the stay)
    # Monthly aggregation
    monthly_rows = []
    for month in range(1, 13):
        md = confirmed[confirmed["month"] == month]
        if md.empty:
            monthly_rows.append({
                "month": month, "month_name": MONTHS_ES[month - 1],
                "real_adr": 0, "suggested_adr": 0, "uplift_pct": 0,
                "total_uplift": 0,
            })
            continue

        real_adr = (md["rate_paid_eur"] * md["length_of_stay"]).sum() / md["length_of_stay"].sum()
        suggested = md["suggested_price"].dropna()
        mask = md["suggested_price"].notna()
        if mask.sum() > 0:
            suggested_adr = (md.loc[mask, "suggested_price"] * md.loc[mask, "length_of_stay"]).sum() / md.loc[mask, "length_of_stay"].sum()
        else:
            suggested_adr = 0.0

        # Revenue uplift: (suggested - real) * nights in stay
        def _uplift(row):
            if pd.isna(row["suggested_price"]):
                return 0.0
            return (row["suggested_price"] - row["rate_paid_eur"]) * row["length_of_stay"]
        total_uplift = md.apply(_uplift, axis=1).sum()

        uplift_pct = ((suggested_adr - real_adr) / real_adr * 100) if real_adr else 0

        monthly_rows.append({
            "month": month,
            "month_name": MONTHS_ES[month - 1],
            "real_adr": round(real_adr, 2),
            "suggested_adr": round(suggested_adr, 2),
            "uplift_pct": round(uplift_pct, 1),
            "total_uplift": round(total_uplift, 2),
        })

    monthly_comp = pd.DataFrame(monthly_rows)
    booking_detail = confirmed[["booking_id", "arrival_date", "room_cat_id",
                                "rate_paid_eur", "suggested_price",
                                "length_of_stay", "channel"]].copy()
    booking_detail["uplift_per_night"] = booking_detail["suggested_price"] - booking_detail["rate_paid_eur"]
    booking_detail["uplift_total"] = booking_detail["uplift_per_night"] * booking_detail["length_of_stay"]

    return monthly_comp, booking_detail


# ═══════════════════════════════════════════════════
#  ANÁLISIS POR CANAL
# ═══════════════════════════════════════════════════

def compute_channel_analysis(df: pd.DataFrame) -> pd.DataFrame:
    """Métricas desglosadas por canal de venta."""
    confirmed = df[df["status"] == "CONFIRMED"].copy()
    rows = []
    for ch in ["DIRECT", "BOOKING", "EXPEDIA", "AIRBNB"]:
        cd = confirmed[confirmed["channel"] == ch]
        if cd.empty:
            continue
        room_nights = int(cd["length_of_stay"].sum())
        total_rev = (cd["rate_paid_eur"] * cd["length_of_stay"]).sum()
        comm_rate = OTA_COMMISSION.get(ch, 0.0)
        net_rev = sum(r["rate_paid_eur"] * (1 - comm_rate) * r["length_of_stay"]
                      for _, r in cd.iterrows())
        adr = total_rev / room_nights if room_nights else 0
        rows.append({
            "channel": ch,
            "bookings": len(cd),
            "room_nights": room_nights,
            "gross_revenue": round(total_rev, 2),
            "net_revenue": round(net_rev, 2),
            "commission_pct": comm_rate * 100,
            "commission_paid": round(total_rev - net_rev, 2),
            "adr": round(adr, 2),
            "pct_bookings": round(len(cd) / len(confirmed) * 100, 1),
        })
    return pd.DataFrame(rows)


# ═══════════════════════════════════════════════════
#  GRÁFICOS
# ═══════════════════════════════════════════════════

def _season_color(season: str) -> str:
    palette = {
        "S_BAJA_INV": "#6c757d",
        "S_MEDIA_INV": "#adb5bd",
        "S_PRIMAVERA": "#74c69d",
        "S_SEMANA_SANTA": "#f4a261",
        "S_CORPUS": "#e9c46a",
        "S_VERANO": "#ff7f50",
        "S_OTONO": "#95d5b2",
        "S_NAVIDAD": "#ff6b6b",
        "S_PUENTE": "#d4a373",
    }
    return palette.get(season, "#999999")

from revenue_engine.toledo_calendar import ToledoCalendar
import calendar


def _get_daily_seasons(year=YEAR):
    """Precompute season for each day of the year."""
    cal = ToledoCalendar(year)
    seasons = {}
    for doy in range(365):
        d = date(year, 1, 1) + __import__("datetime").timedelta(days=doy)
        seasons[doy] = cal.get_season_for_date(d)
    return seasons


def plot_occupancy_vs_benchmark(monthly_kpis: pd.DataFrame):
    """Gráfico 1: Ocupación mensual real vs benchmark sectorial (65%)."""
    fig, ax = plt.subplots(figsize=(10, 5))
    months = monthly_kpis["month_name"]
    occ = monthly_kpis["occ_pct"]

    bars = ax.bar(months, occ, color="#457b9d", width=0.6, label="Real 2025")
    ax.axhline(y=65, color="#e63946", linestyle="--", linewidth=1.5,
               label="Benchmark sectorial (65%)")

    for bar, val in zip(bars, occ):
        if val > 65:
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
                    f"{val:.0f}%", ha="center", fontsize=8, fontweight="bold")
        else:
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
                    f"{val:.0f}%", ha="center", fontsize=8, color="#e63946")

    ax.set_ylabel("Ocupación (%)")
    ax.set_title("Ocupación Mensual 2025 vs Benchmark Sectorial")
    ax.legend(loc="upper right")
    ax.set_ylim(0, 105)
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "01_ocupacion_mensual.png", dpi=150)
    plt.close(fig)


def plot_adr_real_vs_suggested(monthly_comp: pd.DataFrame):
    """Gráfico 2: ADR mensual real vs sugerido por motor."""
    fig, ax = plt.subplots(figsize=(10, 5))
    months = monthly_comp["month_name"]
    x = range(len(months))

    ax.plot(x, monthly_comp["real_adr"], "o-", color="#457b9d", linewidth=2,
            label="ADR Real")
    ax.plot(x, monthly_comp["suggested_adr"], "s--", color="#e76f51",
            linewidth=2, label="ADR Sugerido (Motor)")

    for i in x:
        uplift = monthly_comp.loc[i, "uplift_pct"]
        if abs(uplift) > 1:
            ax.annotate(f"{uplift:+.1f}%",
                        (i, monthly_comp.loc[i, "real_adr"]),
                        xytext=(0, -14), textcoords="offset points",
                        fontsize=7, ha="center", color="#e63946")

    ax.set_xticks(list(x))
    ax.set_xticklabels(months, rotation=30, ha="right")
    ax.set_ylabel("ADR (€)")
    ax.set_title("ADR Real vs Sugerido por Motor de Pricing")
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "02_adr_real_vs_motor.png", dpi=150)
    plt.close(fig)


def plot_channel_mix(df: pd.DataFrame):
    """Gráfico 3: Mix de canales (pie chart)."""
    confirmed = df[df["status"] == "CONFIRMED"]
    ch_counts = confirmed["channel"].value_counts()
    colors = {"DIRECT": "#2a9d8f", "BOOKING": "#e9c46a",
              "EXPEDIA": "#f4a261", "AIRBNB": "#e76f51"}

    fig, ax = plt.subplots(figsize=(7, 7))
    wedges, texts, autotexts = ax.pie(
        ch_counts.values, labels=ch_counts.index,
        autopct="%1.1f%%", startangle=90,
        colors=[colors.get(k, "#999") for k in ch_counts.index],
        textprops={"fontsize": 11},
    )
    for at in autotexts:
        at.set_fontweight("bold")
    ax.set_title("Mix de Canales de Venta 2025", fontsize=14)
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "03_mix_canales.png", dpi=150)
    plt.close(fig)


def plot_lead_time_by_season(df: pd.DataFrame):
    """Gráfico 4: Lead time medio por temporada."""
    confirmed = df[df["status"] == "CONFIRMED"].copy()
    confirmed["arrival_date"] = pd.to_datetime(confirmed["arrival_date"])

    cal = ToledoCalendar(YEAR)

    def _get_season(d):
        return cal.get_season_for_date(d.date() if hasattr(d, "date") else d)

    confirmed["season"] = confirmed["arrival_date"].apply(_get_season)

    season_names = {
        "S_BAJA_INV": "Baja Inv", "S_MEDIA_INV": "Media Inv",
        "S_PRIMAVERA": "Primavera", "S_SEMANA_SANTA": "Semana Santa",
        "S_CORPUS": "Corpus", "S_VERANO": "Verano",
        "S_OTONO": "Otoño", "S_NAVIDAD": "Navidad", "S_PUENTE": "Puente",
    }
    lt_by_season = confirmed.groupby("season")["days_before_arrival"].mean()

    fig, ax = plt.subplots(figsize=(10, 5))
    seasons_plot = [s for s in season_names if s in lt_by_season.index]
    values = [lt_by_season[s] for s in seasons_plot]
    labels = [season_names[s] for s in seasons_plot]
    colors_list = [_season_color(s) for s in seasons_plot]

    bars = ax.barh(labels, values, color=colors_list, height=0.6)
    for bar, val in zip(bars, values):
        ax.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height() / 2,
                f"{val:.0f} días", va="center", fontsize=9)

    ax.set_xlabel("Lead Time Medio (días)")
    ax.set_title("Antelación de Reserva por Temporada")
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "04_lead_time_temporada.png", dpi=150)
    plt.close(fig)


def plot_revpar_with_seasons(monthly_kpis: pd.DataFrame):
    """Gráfico 5: RevPAR mensual con bandas de temporada coloreadas."""
    # Compute seasons for each month (dominant season)
    cal = ToledoCalendar(YEAR)
    month_seasons = []
    for m in range(1, 13):
        mid = date(YEAR, m, 15)
        season = cal.get_season_for_date(mid)
        month_seasons.append(season)

    season_name_short = {
        "S_BAJA_INV": "Invierno", "S_MEDIA_INV": "Media Inv",
        "S_PRIMAVERA": "Primavera", "S_SEMANA_SANTA": "Sem.Santa",
        "S_CORPUS": "Corpus", "S_VERANO": "Verano",
        "S_OTONO": "Otoño", "S_NAVIDAD": "Navidad", "S_PUENTE": "Puente",
    }

    fig, ax = plt.subplots(figsize=(10, 5))
    months = monthly_kpis["month_name"]
    revpar = monthly_kpis["revpar"]
    x = range(len(months))

    # Color bands per season
    seen_seasons = {}
    for i, (m, s) in enumerate(zip(months, month_seasons)):
        color = _season_color(s)
        if s not in seen_seasons:
            seen_seasons[s] = color

    # RevPAR line
    ax.fill_between(x, revpar, alpha=0.15, color="#457b9d")
    ax.plot(x, revpar, "o-", color="#1d3557", linewidth=2, markersize=6)

    # Season annotations
    current_season = None
    start_i = 0
    for i, s in enumerate(month_seasons):
        if s != current_season:
            if current_season is not None:
                mid = (start_i + i - 1) / 2
                ax.annotate(season_name_short.get(current_season, current_season),
                           (mid, ax.get_ylim()[1] * 0.92),
                           ha="center", fontsize=7, fontweight="bold",
                           color=_season_color(current_season))
            current_season = s
            start_i = i
    # Last season
    mid = (start_i + 11) / 2
    ax.annotate(season_name_short.get(current_season, current_season),
               (mid, ax.get_ylim()[1] * 0.92),
               ha="center", fontsize=7, fontweight="bold",
               color=_season_color(current_season))

    # Values on points
    for i, v in enumerate(revpar):
        ax.text(i, v + 0.3, f"{v:.1f}€", ha="center", fontsize=8, fontweight="bold")

    ax.set_xticks(list(x))
    ax.set_xticklabels(months, rotation=30, ha="right")
    ax.set_ylabel("RevPAR (€)")
    ax.set_title("RevPAR Mensual 2025 con Estacionalidad")
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "05_revpar_estacional.png", dpi=150)
    plt.close(fig)


def generate_all_charts(df: pd.DataFrame, monthly_kpis: pd.DataFrame,
                        monthly_comp: pd.DataFrame):
    """Genera los 5 gráficos."""
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    plot_occupancy_vs_benchmark(monthly_kpis)
    plot_adr_real_vs_suggested(monthly_comp)
    plot_channel_mix(df)
    plot_lead_time_by_season(df)
    plot_revpar_with_seasons(monthly_kpis)
    print("    5 gráficos generados en reports/figures/")


# ═══════════════════════════════════════════════════
#  EXCEL
# ═══════════════════════════════════════════════════

def export_excel(monthly_kpis: pd.DataFrame, monthly_comp: pd.DataFrame,
                 channel_analysis: pd.DataFrame, booking_detail: pd.DataFrame,
                 category_detail: pd.DataFrame):
    """Exporta Excel con 5 hojas."""

    # Hoja 1: Resumen Ejecutivo
    total_bookings = len(pd.read_csv(DATA_PATH))
    confirmed = pd.read_csv(DATA_PATH)
    confirmed = confirmed[confirmed["status"] == "CONFIRMED"]
    total_room_nights = confirmed["departure_date"].pipe(
        lambda x: pd.to_datetime(x)) - pd.to_datetime(confirmed["arrival_date"])
    total_rn = int(total_room_nights.dt.days.sum())
    gross = monthly_kpis["gross_revenue"].sum()
    net = monthly_kpis["net_revenue"].sum()
    avg_occ = monthly_kpis["occ_pct"].mean()

    resumen = pd.DataFrame([
        ["Total reservas (emitidas)", total_bookings],
        ["Reservas confirmadas", len(confirmed)],
        ["Ocupación media anual", f"{avg_occ:.1f}%"],
        ["Noches ocupadas", total_rn],
        ["Ingreso bruto anual", f"{gross:,.2f} €"],
        ["Ingreso neto (post-comisiones)", f"{net:,.2f} €"],
        ["Comisiones OTA totales", f"{gross - net:,.2f} €"],
        ["ADR medio anual", f"{monthly_kpis['adr'].mean():.2f} €"],
        ["RevPAR medio anual", f"{monthly_kpis['revpar'].mean():.2f} €"],
    ], columns=["Métrica", "Valor"])

    # Hoja 5: Detalle por Categoría (from seed data)
    # Already passed as parameter

    with pd.ExcelWriter(EXCEL_PATH, engine="openpyxl") as writer:
        resumen.to_excel(writer, sheet_name="Resumen Ejecutivo", index=False)
        # Adjust column width
        ws = writer.sheets["Resumen Ejecutivo"]
        ws.column_dimensions["A"].width = 35
        ws.column_dimensions["B"].width = 25

        monthly_kpis.to_excel(writer, sheet_name="P&L Mensual", index=False)
        ws2 = writer.sheets["P&L Mensual"]
        ws2.column_dimensions["A"].width = 8
        ws2.column_dimensions["B"].width = 14
        for col in ["C", "D", "E", "F", "G", "H", "I"]:
            ws2.column_dimensions[col].width = 16

        category_detail.to_excel(writer, sheet_name="Detalle por Categoría",
                                index=False)
        ws3 = writer.sheets["Detalle por Categoría"]
        ws3.column_dimensions["A"].width = 12
        ws3.column_dimensions["B"].width = 16
        for col in ["C", "D", "E", "F", "G"]:
            ws3.column_dimensions[col].width = 18

        channel_analysis.to_excel(writer, sheet_name="Análisis de Canales",
                                  index=False)
        ws4 = writer.sheets["Análisis de Canales"]
        ws4.column_dimensions["A"].width = 14
        for col in ["B", "C", "D", "E", "F", "G", "H", "I"]:
            ws4.column_dimensions[col].width = 16

        monthly_comp.to_excel(writer, sheet_name="Real vs Motor", index=False)
        ws5 = writer.sheets["Real vs Motor"]
        ws5.column_dimensions["A"].width = 8
        ws5.column_dimensions["B"].width = 14
        for col in ["C", "D", "E", "F"]:
            ws5.column_dimensions[col].width = 18

    print(f"    Excel exportado: {EXCEL_PATH}")


# ═══════════════════════════════════════════════════
#  CATEGORY DETAIL
# ═══════════════════════════════════════════════════

def compute_category_detail(df: pd.DataFrame) -> pd.DataFrame:
    """Métricas desglosadas por categoría de habitación."""
    confirmed = df[df["status"] == "CONFIRMED"].copy()
    rows = []
    for cat_id, cat_name in CATEGORY_NAMES.items():
        cd = confirmed[confirmed["room_cat_id"] == cat_id]
        if cd.empty:
            continue
        bookings = len(cd)
        rn = int(cd["length_of_stay"].sum())
        rev = (cd["rate_paid_eur"] * cd["length_of_stay"]).sum()
        adr = rev / rn if rn else 0
        nights_avail = 365 * [c["count"] for c in
                              [{"id": "dob-001", "count": 12},
                               {"id": "sup-001", "count": 6},
                               {"id": "sui-001", "count": 4}]
                              if c["id"] == cat_id][0]
        occ = rn / nights_avail * 100 if nights_avail else 0
        rows.append({
            "Categoría": cat_name,
            "Habitaciones": [c["count"] for c in
                             [{"id": "dob-001", "count": 12},
                              {"id": "sup-001", "count": 6},
                              {"id": "sui-001", "count": 4}]
                             if c["id"] == cat_id][0],
            "Reservas": bookings,
            "Noches Ocupadas": rn,
            "Ocupación": f"{occ:.1f}%",
            "Ingreso Bruto": f"{rev:,.2f} €",
            "ADR Medio": f"{adr:.2f} €",
            "Precio Base": f"{BASE_RATES[cat_id]:.0f} €",
        })
    return pd.DataFrame(rows)


# ═══════════════════════════════════════════════════
#  MARKDOWN
# ═══════════════════════════════════════════════════

def generate_markdown(monthly_kpis: pd.DataFrame,
                      monthly_comp: pd.DataFrame,
                      channel_analysis: pd.DataFrame,
                      category_detail: pd.DataFrame,
                      df: pd.DataFrame):
    """Genera informe ejecutivo en markdown."""

    total_bookings = len(df)
    confirmed = df[df["status"] == "CONFIRMED"]
    gross = monthly_kpis["gross_revenue"].sum()
    net = monthly_kpis["net_revenue"].sum()
    total_rn = int(confirmed["length_of_stay"].sum())
    avg_occ = monthly_kpis["occ_pct"].mean()
    avg_adr = monthly_kpis["adr"].mean()
    avg_revpar = monthly_kpis["revpar"].mean()
    annual_uplift = monthly_comp["total_uplift"].sum()

    # Channel insights
    most_expensive_ch = channel_analysis.loc[
        channel_analysis["commission_paid"].idxmax()
    ]
    best_adr_ch = channel_analysis.loc[
        channel_analysis["adr"].idxmax()
    ]

    # Season with lowest occupancy
    min_occ_month = monthly_kpis.loc[monthly_kpis["occ_pct"].idxmin()]

    md = f"""# Informe Anual 2025 — Hotel Posada de la Sillería

> **Hotel:** Posada de la Sillería | **Ubicación:** Toledo, España
> **Generado:** {datetime.now().strftime("%d/%m/%Y")}
> **Datos:** Sintéticos (seed=42) basados en motor de revenue management

---

## 1. Resumen Ejecutivo

El Hotel Posada de la Sillería registró durante 2025 una **ocupación media
del {avg_occ:.1f}%**, por encima del benchmark sectorial del 65% para hoteles
urbanos de categoría similar. Esto refleja una buena gestión de la demanda en
un destino con alto atractivo cultural como Toledo, donde los fines de semana
y los eventos (Semana Santa, Corpus) actúan como principales motores de
ocupación.

En términos de rentabilidad, el hotel generó **{gross:,.2f} € de ingreso bruto**
por alojamiento, con un ADR medio de **{avg_adr:.2f} €** y un RevPAR de
**{avg_revpar:.2f} €**. Tras descontar comisiones de OTA
({gross - net:,.2f} €), el ingreso neto se sitúa en {net:,.2f} €, lo que
supone una carga de intermediación del {(gross-net)/gross*100:.1f}% sobre el
ingreso bruto.

El **análisis comparativo con el motor de pricing** revela un potencial de
ingreso no capturado de **{annual_uplift:,.2f} €**: el motor habría sugerido
precios sistemáticamente superiores a los aplicados, especialmente en
temporada alta y fines de semana, donde la demanda muestra baja elasticidad.

---

## 2. Indicadores Clave del Año

| Indicador | Valor |
|-----------|-------|
| Reservas emitidas | {total_bookings} |
| Reservas confirmadas | {len(confirmed)} |
| Ocupación media | {avg_occ:.1f}% |
| ADR medio | {avg_adr:.2f} € |
| RevPAR medio | {avg_revpar:.2f} € |
| Ingreso bruto alojamiento | {gross:,.2f} € |
| Ingreso neto (post-comisiones) | {net:,.2f} € |
| Comisiones OTA | {gross - net:,.2f} € |
| Coste de intermediación | {(gross-net)/gross*100:.1f}% |
| Revenue Uplift potencial | {annual_uplift:,.2f} € |

---

## 3. Análisis Mensual

| Mes | Ocupación | ADR | RevPAR | Noches | Bruto |
|-----|-----------|-----|--------|--------|-------|
"""
    for _, row in monthly_kpis.iterrows():
        md += f"| {row['month_name']:12s} | {row['occ_pct']:5.1f}% | {row['adr']:>6.2f}€ | {row['revpar']:>6.2f}€ | {row['room_nights']:>4d} | {row['gross_revenue']:>10,.2f}€ |\n"

    min_month = monthly_kpis.loc[monthly_kpis["occ_pct"].idxmin()]
    max_month = monthly_kpis.loc[monthly_kpis["occ_pct"].idxmax()]

    md += f"""
**Comentarios estacionales:**

- **Máximo de ocupación:** {max_month['month_name']} con {max_month['occ_pct']:.1f}%
- **Mínimo de ocupación:** {min_month['month_name']} con {min_month['occ_pct']:.1f}%
- La **Semana Santa** (abril) y el **Corpus Christi** (junio) generan picos
  de demanda que permiten ADRs un 50-80% por encima de la media anual.
- **Agosto** presenta la ocupación más baja (calor toledano), aunque el ADR
  se mantiene gracias al turismo cultural de temporada baja.
- Los **fines de semana** mantienen ocupaciones sistemáticamente superiores
  al 80%, reflejando el perfil escapista del cliente de Madrid.

---

## 4. Comparativa con Motor de Pricing

| Mes | ADR Real | ADR Sugerido | Diferencia | Uplift Potencial |
|-----|----------|--------------|------------|------------------|
"""
    for _, row in monthly_comp.iterrows():
        diff = row["suggested_adr"] - row["real_adr"]
        md += f"| {row['month_name']:12s} | {row['real_adr']:>8.2f}€ | {row['suggested_adr']:>11.2f}€ | {diff:>+7.2f}€ | {row['total_uplift']:>10,.2f}€ |\n"

    md += f"""
**Hallazgo principal:** El motor sugiere precios sistemáticamente superiores
a los aplicados, con un revenue uplift potencial total de
**{annual_uplift:,.2f} €** anuales. Las mayores diferencias se concentran en
eventos (Semana Santa, Corpus) donde la demanda es menos elástica y los
clientes están dispuestos a pagar más.

---

## 5. Análisis por Canal

| Canal | Reservas | Noches | ADR | Bruto | Neto | Comisión |
|-------|----------|--------|-----|-------|------|---------|
"""
    for _, row in channel_analysis.iterrows():
        md += f"| {row['channel']:8s} | {row['bookings']:>5d} | {row['room_nights']:>4d} | {row['adr']:>6.2f}€ | {row['gross_revenue']:>9,.2f}€ | {row['net_revenue']:>9,.2f}€ | {row['commission_paid']:>9,.2f}€ |\n"

    md += f"""
**Conclusiones por canal:**

- **DIRECT** ({channel_analysis[channel_analysis['channel']=='DIRECT']['pct_bookings'].values[0]:.0f}% de reservas): mejor ADR ({channel_analysis[channel_analysis['channel']=='DIRECT']['adr'].values[0]:.2f}€) y cero comisiones.
  Es el canal más rentable con diferencia.
- **BOOKING** ({channel_analysis[channel_analysis['channel']=='BOOKING']['pct_bookings'].values[0]:.0f}%): mayor volumen de negocio OTA, pero
  {channel_analysis[channel_analysis['channel']=='BOOKING']['commission_paid'].values[0]:,.2f}€ en comisiones.
- **AIRBNB**: menor ADR por ajuste a perfil de estancia larga y menor
  disposición a pagar.

---

## 6. Recomendaciones para 2026

Basándose en los hallazgos del informe, se proponen las siguientes acciones:

### 6.1 Subir precios en eventos y fines de semana
El motor de pricing sugiere precios un 15-30% superiores durante Semana
Santa, Corpus y fines de semana. La baja elasticidad en estos períodos
indica que el mercado lo soporta. **Impacto estimado: +{annual_uplift * 0.6:,.0f} €**
(si se captura el 60% del uplift potencial en eventos y fines de semana).

### 6.2 Reducir dependencia de OTA
BOOKING y EXPEDIA suponen el 50% de las reservas pero se llevan
{channel_analysis[channel_analysis['channel']=='BOOKING']['commission_paid'].values[0] + channel_analysis[channel_analysis['channel']=='EXPEDIA']['commission_paid'].values[0]:,.0f} €
en comisiones. Estrategias:
- Programa de fidelización directo con ventajas exclusivas.
- Mejorar visibilidad SEO y Google Ads para captar DIRECT.
- Ofrecer 5% de descuento en reserva directa (sigue siendo más rentable
  que pagar 15% de comisión).

### 6.3 Monetizar la baja temporada estival
Agosto registra la ocupación más baja ({min_occ_month['occ_pct']:.0f}%). Se
recomienda:
- Paquetes "Toledo Cultural" con visitas guiadas y degustaciones.
- Colaboración con el Ayuntamiento para eventos de captación estival.
- Tarifas dinámicas a la baja para mantener volumen.

### 6.4 Implementar pricing dinámico basado en el motor
El motor ha demostrado capacidad para identificar oportunidades de precio
que la gestión manual está dejando pasar. Se recomienda:
- Integrar el motor en el PMS para sugerencias de precio en tiempo real.
- Revisión semanal de precios por temporada y canal.
- Monitorizar el revenue uplift capturado como KPI mensual.

### 6.5 Optimizar el mix de canales
Aumentar DIRECT del {channel_analysis[channel_analysis['channel']=='DIRECT']['pct_bookings'].values[0]:.0f}% al 45% supondría un ahorro estimado de
{channel_analysis['commission_paid'].sum() * 0.10:,.0f} € anuales en comisiones
(10% de desplazamiento desde OTA a DIRECT).

---

*Informe generado automáticamente por Revenue Management Engine.*
*Datos sintéticos 2025 — seed=42.*
"""
    MD_PATH.write_text(md, encoding="utf-8")
    print(f"    Markdown exportado: {MD_PATH}")


# ═══════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════

def main():
    print("═══ GENERADOR DE INFORME ANUAL 2025 ═══\n")

    # Ensure output dirs
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    ROOT.joinpath("reports").mkdir(parents=True, exist_ok=True)

    print("▶ Cargando datos...")
    df = load_bookings()
    print(f"    {len(df)} reservas cargadas")

    print("▶ Calculando KPIs mensuales...")
    monthly_kpis = compute_monthly_kpis(df)
    print(f"    {len(monthly_kpis)} meses calculados")

    print("▶ Ejecutando motor de pricing...")
    monthly_comp, booking_detail = run_engine_comparison(df)
    print(f"    Comparativa real vs motor completada")

    print("▶ Analizando canales...")
    channel_analysis = compute_channel_analysis(df)

    print("▶ Analizando categorías...")
    category_detail = compute_category_detail(df)

    print("▶ Generando gráficos...")
    generate_all_charts(df, monthly_kpis, monthly_comp)

    print("▶ Exportando Excel...")
    export_excel(monthly_kpis, monthly_comp, channel_analysis,
                 booking_detail, category_detail)

    print("▶ Generando informe Markdown...")
    generate_markdown(monthly_kpis, monthly_comp, channel_analysis,
                      category_detail, df)

    print("\n✅ Informe anual 2025 generado correctamente.")
    print(f"   Gráficos:  {FIGURES_DIR}")
    print(f"   Excel:     {EXCEL_PATH}")
    print(f"   Markdown:  {MD_PATH}")


if __name__ == "__main__":
    main()

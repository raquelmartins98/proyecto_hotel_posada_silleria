"""
Genera dataset sintético de reservas 2025 para el Hotel Posada de la Sillería.

Patrones realistas de Toledo:
  - Semana Santa, Corpus, puentes → alta ocupación y ADR
  - Agosto → baja ocupación (calor)
  - Fines de semana → ocupación alta (escapismo Madrid)
  - Mix de canales: DIRECT +8% ADR, OTA comisión 15%
  - 8% cancelaciones, 2% no-show
"""

import csv
import random
from datetime import date, timedelta, datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from revenue_engine.toledo_calendar import ToledoCalendar

# ── Semilla reproducible ──
SEED = 42
random.seed(SEED)

# ── Configuración del hotel ──
ROOM_CATEGORIES = {
    "dob-001": {"code": "DOB", "name": "Doble",       "count": 12, "base_rate": 120.0, "max_guests": 2},
    "sup-001": {"code": "SUP", "name": "Superior",     "count": 6,  "base_rate": 155.0, "max_guests": 2},
    "sui-001": {"code": "SUI", "name": "Suite Junior", "count": 4,  "base_rate": 210.0, "max_guests": 3},
}
TOTAL_ROOMS = sum(c["count"] for c in ROOM_CATEGORIES.values())
TOTAL_ROOM_NIGHTS = TOTAL_ROOMS * 365  # 8.030

# ── Target occupancy parameters by season/event ──
# These are used to compute daily target bookings
OCCUPANCY_TARGETS = {
    "S_SEMANA_SANTA":  0.97,  # Casi lleno
    "S_CORPUS":        0.90,
    "S_PUENTE":        0.85,
    "S_NAVIDAD":       0.85,  # Diciembre 23 - Enero 7
    "weekend_base":    0.80,  # Viernes + Sábado (escapismo Madrid)
    "weekday_base":    0.50,
    "S_BAJA_INV":      0.40,  # Enero-Febrero frío
    "S_VERANO":        0.50,  # Agosto calor
}

# Events for 2025 (computed from ToledoCalendar)
YEAR = 2025

# ── Channel mix ──
CHANNELS = {
    "DIRECT":  {"pct": 0.35, "adr_multiplier": 1.08},
    "BOOKING": {"pct": 0.30, "adr_multiplier": 1.00},
    "EXPEDIA": {"pct": 0.20, "adr_multiplier": 1.00},
    "AIRBNB":  {"pct": 0.15, "adr_multiplier": 0.95},
}

# ── Status probabilities ──
STATUS_PROBS = {"CONFIRMED": 0.90, "CANCELLED": 0.08, "NO_SHOW": 0.02}

# ── Length of stay distribution (probability by nights) ──
LOS_DIST = {1: 0.45, 2: 0.35, 3: 0.12, 4: 0.05, 5: 0.02, 6: 0.01}

# ── Lead time by season (mean days before arrival) ──
LEAD_TIME = {
    "S_SEMANA_SANTA":  ("lognormal", 60, 20),
    "S_CORPUS":        ("lognormal", 45, 15),
    "S_PUENTE":        ("lognormal", 30, 15),
    "S_NAVIDAD":       ("lognormal", 45, 20),
    "weekend":         ("lognormal", 14, 10),
    "weekday":         ("lognormal", 7,  7),
}
MAX_LEAD = 365

# ── Guests distribution per room ──
GUESTS_DIST = {
    "dob-001": {1: 0.40, 2: 0.60},
    "sup-001": {1: 0.30, 2: 0.70},
    "sui-001": {1: 0.15, 2: 0.50, 3: 0.35},
}


def _init_calendar() -> ToledoCalendar:
    return ToledoCalendar(YEAR)


def _get_season_and_events(cal: ToledoCalendar) -> Dict[int, Dict]:
    """Precomputa season, is_weekend, is_event, is_puente for each day of year."""
    day_info = {}
    puente_dates = set()
    for s, e, _ in cal.get_puentes():
        d = s
        while d <= e:
            puente_dates.add(d)
            d += timedelta(days=1)

    for day_offset in range(365):
        d = date(YEAR, 1, 1) + timedelta(days=day_offset)
        season = cal.get_season_for_date(d)
        is_we = cal.is_weekend(d)
        is_puente = d in puente_dates

        # Determine target occupancy for this day
        if season == "S_SEMANA_SANTA":
            target = OCCUPANCY_TARGETS["S_SEMANA_SANTA"]
        elif season == "S_CORPUS":
            target = OCCUPANCY_TARGETS["S_CORPUS"]
        elif season == "S_PUENTE":
            target = OCCUPANCY_TARGETS["S_PUENTE"]
        elif season == "S_NAVIDAD":
            target = OCCUPANCY_TARGETS["S_NAVIDAD"]
        elif season == "S_VERANO":
            target = OCCUPANCY_TARGETS["S_VERANO"]
        elif season == "S_BAJA_INV":
            target = OCCUPANCY_TARGETS["S_BAJA_INV"] if not is_we else 0.60
        elif is_we:
            target = OCCUPANCY_TARGETS["weekend_base"]
        else:
            target = OCCUPANCY_TARGETS["weekday_base"]

        # Season coefficient for ADR
        coeff = cal.get_coefficient(d)

        day_info[day_offset] = {
            "date": d,
            "season": season,
            "is_weekend": is_we,
            "is_puente": is_puente,
            "target_occ": target,
            "season_coeff": coeff,
            "dow": d.weekday(),
        }

    return day_info


def _pick_room_category() -> Tuple[str, Dict]:
    """Pick room category weighted by room_count."""
    cats = list(ROOM_CATEGORIES.keys())
    weights = [ROOM_CATEGORIES[c]["count"] for c in cats]
    cid = random.choices(cats, weights=weights, k=1)[0]
    return cid, ROOM_CATEGORIES[cid]


def _pick_los() -> int:
    """Pick length of stay in nights."""
    nights = list(LOS_DIST.keys())
    probs = list(LOS_DIST.values())
    return random.choices(nights, weights=probs, k=1)[0]


def _pick_channel() -> Tuple[str, float]:
    """Pick channel and get the ADR multiplier."""
    channels = list(CHANNELS.keys())
    weights = [CHANNELS[c]["pct"] for c in channels]
    ch = random.choices(channels, weights=weights, k=1)[0]
    return ch, CHANNELS[ch]["adr_multiplier"]


def _pick_guests(cat_id: str) -> int:
    """Pick number of guests for this booking."""
    dist = GUESTS_DIST[cat_id]
    vals = list(dist.keys())
    probs = list(dist.values())
    return random.choices(vals, weights=probs, k=1)[0]


def _pick_status() -> str:
    statuses = list(STATUS_PROBS.keys())
    probs = list(STATUS_PROBS.values())
    return random.choices(statuses, weights=probs, k=1)[0]


def _pick_lead_time(season: str, is_weekend: bool) -> int:
    """Pick days_before_arrival for this booking."""
    if season == "S_SEMANA_SANTA":
        dist_type, mean, std = LEAD_TIME["S_SEMANA_SANTA"]
    elif season == "S_CORPUS":
        dist_type, mean, std = LEAD_TIME["S_CORPUS"]
    elif season == "S_PUENTE":
        dist_type, mean, std = LEAD_TIME["S_PUENTE"]
    elif season == "S_NAVIDAD":
        dist_type, mean, std = LEAD_TIME["S_NAVIDAD"]
    elif is_weekend:
        dist_type, mean, std = LEAD_TIME["weekend"]
    else:
        dist_type, mean, std = LEAD_TIME["weekday"]

    if dist_type == "lognormal":
        # Sample from lognormal-ish distribution
        lead = int(random.gauss(mean, std))
    else:
        lead = int(random.gauss(mean, std))

    # Clamp
    lead = max(0, min(lead, MAX_LEAD))
    return lead


def _compute_rate(
    base_rate: float,
    season_coeff: float,
    channel_mult: float,
    is_weekend: bool,
    cat_id: str,
) -> float:
    """
    Compute the ADR (rate paid by guest) for a booking.
    
    Formula: base_rate * season_coeff * channel_mult * weekend_surcharge
    """
    rate = base_rate * season_coeff * channel_mult
    if is_weekend:
        rate *= 1.12  # 12% weekend surcharge
    # Add small random noise (±5%)
    rate *= random.uniform(0.95, 1.05)
    return round(rate, 2)


def generate_bookings(target_total: int = 4000) -> List[Dict]:
    """
    Generate synthetic bookings targeting ~70% annual occupancy.
    
    Strategy: for each day, compute target arrivals based on target occupancy
    and average LOS, then generate that many bookings per arrival day.
    No constraint checking needed — natural distribution hits the target.
    """
    cal = _init_calendar()
    day_info = _get_season_and_events(cal)
    
    # Avg length of stay weighted by LOS_DIST
    avg_los = sum(n * p for n, p in LOS_DIST.items())
    
    bookings = []
    booking_id = 1
    
    # Total arrivals needed for ~70% actual occupancy (after 10% cancellation)
    total_arrivals_target = round(TOTAL_ROOMS * 365 * 0.74 / avg_los / 0.90)
    total_target_sum = sum(info["target_occ"] for info in day_info.values())
    
    # Hamilton method: exact proportional distribution, no rounding drift
    frac_parts = []
    for offset, info in day_info.items():
        raw = total_arrivals_target * info["target_occ"] / total_target_sum
        frac_parts.append((offset, raw, int(raw), raw - int(raw)))
    base = sum(f[2] for f in frac_parts)
    rem = total_arrivals_target - base
    frac_parts.sort(key=lambda x: -x[3])  # highest remainder first
    extras = {f[0] for i, f in enumerate(frac_parts) if i < rem}
    day_arrivals = {f[0]: f[2] + (1 if f[0] in extras else 0) for f in frac_parts}
    
    for offset, info in day_info.items():
        arrivals = day_arrivals[offset]
        for _ in range(arrivals):
            cat_id, cat_info = _pick_room_category()
            los = _pick_los()
            
            # Cap: don't let a single night exceed TOTAL_ROOMS
            would_exceed = False
            for n in range(los):
                night_offset = offset + n
                if night_offset >= 365:
                    would_exceed = True
                    break
            
            if would_exceed:
                continue
            
            ch_name, ch_mult = _pick_channel()
            n_guests = _pick_guests(cat_id)
            status = _pick_status()
            lead_time = _pick_lead_time(info["season"], info["is_weekend"])
            
            rate = _compute_rate(
                base_rate=cat_info["base_rate"],
                season_coeff=info["season_coeff"],
                channel_mult=ch_mult,
                is_weekend=info["is_weekend"],
                cat_id=cat_id,
            )
            
            departure_date = info["date"] + timedelta(days=los)
            
            bookings.append({
                "booking_id": f"BK-{booking_id:05d}",
                "arrival_date": info["date"].isoformat(),
                "departure_date": departure_date.isoformat(),
                "room_cat_id": cat_id,
                "guests": n_guests,
                "channel": ch_name,
                "rate_paid_eur": rate,
                "days_before_arrival": lead_time,
                "status": status,
                "length_of_stay": los,
            })
            booking_id += 1
    
    print(f"    Generadas {len(bookings)} reservas")
    return bookings


def save_csv(bookings: List[Dict], path: Path):
    """Save bookings to CSV (without length_of_stay internal field)."""
    fields = ["booking_id", "arrival_date", "departure_date", "room_cat_id",
              "guests", "channel", "rate_paid_eur", "days_before_arrival", "status"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for b in bookings:
            row = {k: b[k] for k in fields}
            writer.writerow(row)
    print(f"    CSV guardado en {path}")


def print_stats(bookings: List[Dict], day_info: Dict[int, Dict]):
    """Print validation stats."""
    total = len(bookings)
    confirmed = sum(1 for b in bookings if b["status"] == "CONFIRMED")
    cancelled = sum(1 for b in bookings if b["status"] == "CANCELLED")
    no_show = sum(1 for b in bookings if b["status"] == "NO_SHOW")
    
    room_nights_gross = sum(b["length_of_stay"] for b in bookings if b["status"] == "CONFIRMED")
    room_nights_net = sum(b["length_of_stay"] for b in bookings)
    
    total_revenue = sum(b["rate_paid_eur"] for b in bookings if b["status"] == "CONFIRMED")
    avg_rate = total_revenue / room_nights_gross if room_nights_gross else 0
    
    # Compute actual occupancy from CONFIRMED bookings
    occupied_nights = [0] * 365
    for b in bookings:
        if b["status"] != "CONFIRMED":
            continue
        arrival = date.fromisoformat(b["arrival_date"])
        for i in range(b["length_of_stay"]):
            d = arrival + timedelta(days=i)
            offset = (d - date(YEAR, 1, 1)).days
            if 0 <= offset < 365:
                occupied_nights[offset] += 1
    actual_occ = sum(occupied_nights) / (TOTAL_ROOMS * 365) * 100
    
    # Channel mix
    channel_counts = {}
    for b in bookings:
        ch = b["channel"]
        channel_counts[ch] = channel_counts.get(ch, 0) + 1
    
    print(f"\n── ESTADÍSTICAS DEL DATASET ──")
    print(f"  Total reservas generadas:  {total}")
    print(f"  CONFIRMED: {confirmed} ({confirmed/total*100:.1f}%)")
    print(f"  CANCELLED: {cancelled} ({cancelled/total*100:.1f}%)")
    print(f"  NO_SHOW:   {no_show} ({no_show/total*100:.1f}%)")
    print(f"  Noches ocupadas (real):    {sum(occupied_nights):,}")
    print(f"  Capacidad total (noches):  {TOTAL_ROOMS * 365:,}")
    print(f"  Ocupación anual real:      {actual_occ:.1f}%")
    print(f"  Ingreso bruto (confirm.):  {total_revenue:,.2f}€")
    print(f"  ADR medio:                 {avg_rate:.2f}€")
    print(f"  Mix de canales:")
    for ch, count in sorted(channel_counts.items(), key=lambda x: -x[1]):
        pct = count / total * 100
        print(f"    {ch:8s}: {count:5d} ({pct:.1f}%)")


def main():
    print("═══ GENERADOR DE DATOS SINTÉTICOS — 2025 ═══\n")
    
    out_dir = Path(__file__).resolve().parent.parent / "data" / "synthetic"
    out_dir.mkdir(parents=True, exist_ok=True)
    
    print("▶ Generando reservas...")
    bookings = generate_bookings(target_total=4000)
    
    print("\n▶ Calculando estadísticas...")
    cal = _init_calendar()
    day_info = _get_season_and_events(cal)
    print_stats(bookings, day_info)
    
    print("\n▶ Guardando CSV...")
    csv_path = out_dir / "2025_bookings.csv"
    save_csv(bookings, csv_path)
    
    print("\n✅ Dataset sintético generado correctamente.")


if __name__ == "__main__":
    main()

"""
preparar_serie.py — Bloque 2: Carga, preparacion y visualizacion
de la serie temporal de ocupacion desde Insforge.

Lee ocupacion_real via REST, construye un pd.Series diario,
analiza continuidad y genera grafica PNG.
"""
import sys
import os
from pathlib import Path
from datetime import datetime

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from dotenv import load_dotenv
import requests

# ── Config ────────────────────────────────────────────────

SALIDA = Path(__file__).parent / "graficas" / "ocupacion_anual.png"
ENV_PATH = Path(__file__).resolve().parents[1] / "frontend" / ".env"

# ── 1. Leer credenciales ─────────────────────────────────

load_dotenv(ENV_PATH)
API_URL = os.getenv("VITE_INSFORGE_URL")
ANON_KEY = os.getenv("VITE_INSFORGE_ANON_KEY")

if not API_URL or not ANON_KEY:
    print("[FAIL] Faltan credenciales en frontend/.env")
    sys.exit(1)

# ── 2. Pedir datos a Insforge ───────────────────────────

url = f"{API_URL.rstrip('/')}/api/database/records/ocupacion_real"
headers = {
    "Authorization": f"Bearer {ANON_KEY}",
    "Accept": "application/json",
}

print("Leyendo ocupacion_real desde Insforge...", end=" ")
resp = requests.get(url, headers=headers, timeout=15)
resp.raise_for_status()
raw = resp.json()

# Normalizar respuesta
records = raw["records"] if isinstance(raw, dict) and "records" in raw else raw
print(f"{len(records)} filas recibidas.")

if not records:
    print("[FAIL] No hay datos")
    sys.exit(1)

# ── 3. Construir Serie Temporal ─────────────────────────

df = pd.DataFrame(records)
df["fecha"] = pd.to_datetime(df["fecha"])
df = df.sort_values("fecha").reset_index(drop=True)

serie = df.set_index("fecha")["porcentaje_ocupacion"].copy()
serie.index = pd.DatetimeIndex(serie.index).tz_localize(None)

# ── 4. Frecuencia diaria y deteccion de huecos ─────────

# Inferir frecuencia
freq_inferida = pd.infer_freq(serie.index)
print(f"\nFrecuencia inferida: {freq_inferida}")

# Reindexar a calendario completo para detectar huecos
idx_completo = pd.date_range(start=serie.index.min(), end=serie.index.max(), freq="D")
serie_completa = serie.reindex(idx_completo)

huecos = serie_completa.isna().sum()
if huecos > 0:
    print(f"\n[!] HUECOS DETECTADOS: {huecos} dia(s) sin datos.")
    faltantes = serie_completa[serie_completa.isna()].index
    print(f"    Fechas faltantes: {faltantes[0].strftime('%Y-%m-%d')} ... {faltantes[-1].strftime('%Y-%m-%d')}")
else:
    print("\n[OK] Sin huecos -- serie completa y contigua.")

# ── 5. Resumen estadistico ──────────────────────────────

print(f"""
--- RESUMEN SERIE OCUPACION ---
Inicio:      {serie.index.min().strftime('%d/%m/%Y')}
Fin:         {serie.index.max().strftime('%d/%m/%Y')}
Dias:        {len(serie)}
Media:       {serie.mean():.2f}%
Minimo:      {serie.min():.2f}%
Maximo:      {serie.max():.2f}%
Mediana:     {serie.median():.2f}%
Desv. std:   {serie.std():.2f}%
-------------------------------
""")

# ── 6. Grafica ──────────────────────────────────────────

SALIDA.parent.mkdir(parents=True, exist_ok=True)

fig, ax = plt.subplots(figsize=(14, 5))
fig.patch.set_facecolor("#fafafa")
ax.set_facecolor("#fafafa")

ax.fill_between(serie_completa.index, serie_completa.values,
                alpha=0.15, color="#1a73e8")
ax.plot(serie_completa.index, serie_completa.values,
        color="#1a73e8", linewidth=0.9, label="Ocupación diaria (%)")

# Linea de media
media_val = serie_completa.mean()
ax.axhline(y=media_val, color="#e8710a", linestyle="--", linewidth=0.8,
           alpha=0.8, label=f"Media {media_val:.1f}%")

# Formato ejes
ax.xaxis.set_major_locator(mdates.MonthLocator())
ax.xaxis.set_major_formatter(mdates.DateFormatter("%b"))
ax.xaxis.set_minor_locator(mdates.WeekdayLocator())
ax.set_xlim(serie_completa.index.min(), serie_completa.index.max())
ax.set_ylim(0, 105)
ax.set_ylabel("Ocupación (%)")
ax.set_title("Ocupación Hotelera — Posada de la Sillería (Toledo)",
             fontsize=13, fontweight="bold")
ax.legend(loc="upper right", framealpha=0.9)
ax.grid(axis="y", alpha=0.3)

fig.tight_layout()
fig.savefig(SALIDA, dpi=150)
print(f"Grafica guardada: {SALIDA.resolve()}")
print(f"   Tamaño: {SALIDA.stat().st_size / 1024:.1f} KB")

plt.close(fig)
print("\n[OK] Serie temporal preparada y visualizada. Listo para modelado.")

"""
escenarios.py — Bloque 5: Tres escenarios de prediccion (optimista,
realista, pesimista) a partir del modelo SARIMA(2,1,1)(1,0,2,7).

A diferencia del Bloque 4 (que dividia train/test para medir error),
aqui ENTRENAMOS CON LA SERIE COMPLETA (365 dias) y PREDECIMOS 30 DIAS
HACIA DELANTE.

Los 3 escenarios salen del intervalo de confianza al 95%:
  - OPTIMISTA: limite superior del IC  (mejor caso)
  - REALISTA:  prediccion central        (caso mas probable)
  - PESIMISTA: limite inferior del IC   (peor caso)

Todos los valores se recortan al rango logico 0-100% (la ocupacion
no puede ser negativa ni superar el 100%).
"""
import sys
import os
import warnings
from pathlib import Path
from datetime import timedelta

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from dotenv import load_dotenv
import requests

warnings.filterwarnings("ignore")

# ── Config ────────────────────────────────────────────────

SALIDA = Path(__file__).parent / "graficas" / "tres_escenarios.png"
ENV_PATH = Path(__file__).resolve().parents[1] / "frontend" / ".env"

# Parametros SARIMA optimos descubiertos en el Bloque 4
# (auto_arima con seasonal=True, m=7 sobre 335 dias de entrenamiento)
ORDER = (2, 1, 1)            # (p, d, q) — parte NO estacional
SEASONAL_ORDER = (1, 0, 2, 7)  # (P, D, Q, m) — parte estacional (m=7)

DIAS_PREDICCION = 30

# ═══════════════════════════════════════════════════════════
#  1. CARGAR DATOS DESDE INSFORGE
# ═══════════════════════════════════════════════════════════

load_dotenv(ENV_PATH)
API_URL = os.getenv("VITE_INSFORGE_URL")
ANON_KEY = os.getenv("VITE_INSFORGE_ANON_KEY")

url = f"{API_URL.rstrip('/')}/api/database/records/ocupacion_real"
headers = {"Authorization": f"Bearer {ANON_KEY}", "Accept": "application/json"}

print("=" * 60)
print("BLOQUE 5: TRES ESCENARIOS DE PREDICCION (SARIMA)")
print("=" * 60)

print("\n[1/6] Leyendo ocupacion_real desde Insforge...", end=" ")
resp = requests.get(url, headers=headers, timeout=15)
resp.raise_for_status()
raw = resp.json()
records = raw["records"] if isinstance(raw, dict) and "records" in raw else raw
print(f"{len(records)} filas.")

# ═══════════════════════════════════════════════════════════
#  2. CONSTRUIR SERIE TEMPORAL COMPLETA
# ═══════════════════════════════════════════════════════════
#  DIFERENCIA CLAVE con el Bloque 4: NO dividimos train/test.
#  Usamos los 365 dias para entrenar, porque queremos predecir
#  el futuro, no medir error contra datos que ya tenemos.

print("\n[2/6] Construyendo serie temporal completa (365 dias)...")

df = pd.DataFrame(records)
df["fecha"] = pd.to_datetime(df["fecha"])
df = df.sort_values("fecha").reset_index(drop=True)

serie = df.set_index("fecha")["porcentaje_ocupacion"].astype(float)

print(f"  Rango: {serie.index.min().date()} -> {serie.index.max().date()}")
print(f"  Total: {len(serie)} dias")
print(f"  Media historica: {serie.mean():.1f}%")

# ═══════════════════════════════════════════════════════════
#  3. ENTRENAR SARIMA SOBRE LA SERIE COMPLETA
# ═══════════════════════════════════════════════════════════
#  Usamos SARIMAX de statsmodels con los parametros optimos
#  descubiertos por auto_arima en el Bloque 4:
#    SARIMA(2,1,1)(1,0,2,7)
#
#  p=2: la ocupacion de hoy depende de la de ayer y anteayer
#  d=1: restamos la serie a si misma una vez (elimina tendencia)
#  q=1: un error pasado influye en la prediccion
#  P=1: la ocupacion de este sabado depende del sabado pasado
#  D=0: la estacionalidad semanal ya es estacionaria
#  Q=2: dos errores estacionales pasados influyen
#  m=7: ciclo semanal (lunes-domingo, finde vs entre semana)

print("\n[3/6] Entrenando SARIMA(2,1,1)(1,0,2,7) sobre los 365 dias...")
print("  (Esto toma 10-20 segundos)")
sys.stdout.flush()

from statsmodels.tsa.statespace.sarimax import SARIMAX

modelo = SARIMAX(
    serie,
    order=ORDER,
    seasonal_order=SEASONAL_ORDER,
    enforce_stationarity=False,
    enforce_invertibility=False,
)
modelo_fit = modelo.fit(disp=False, maxiter=200)

print(f"  Modelo SARIMA{ORDER}{SEASONAL_ORDER}")
print(f"  AIC: {modelo_fit.aic:.1f}")
print(f"  Log-verosimilitud: {modelo_fit.llf:.1f}")

# ═══════════════════════════════════════════════════════════
#  4. PREDECIR 30 DIAS CON INTERVALOS DE CONFIANZA
# ═══════════════════════════════════════════════════════════
#  get_forecast() predice hacia adelante (fuera de la muestra).
#  summary_frame() devuelve mean, mean_se, y los IC 95%.

print(f"\n[4/6] Prediciendo {DIAS_PREDICCION} dias hacia adelante...")

pred = modelo_fit.get_forecast(steps=DIAS_PREDICCION)
pred_df = pred.summary_frame(alpha=0.05)  # alpha=0.05 → IC del 95%

# Fechas futuras a partir del ultimo dia de la serie
ultima_fecha = serie.index.max()
fechas_futuras = [ultima_fecha + timedelta(days=i + 1) for i in range(DIAS_PREDICCION)]

# Extraer los 3 escenarios del intervalo de confianza
pred_central = pred_df["mean"].values      # REALISTA
pred_inferior = pred_df["mean_ci_lower"].values  # PESIMISTA (IC inferior)
pred_superior = pred_df["mean_ci_upper"].values  # OPTIMISTA (IC superior)

# ── RECORTAR al rango logico 0-100% ──────────────────────
#  La ocupacion no puede ser negativa (minimo 0%) ni
#  superar el 100% (maximo 100%). El modelo SARIMA no sabe
#  esto y podria dar valores fuera de rango.
pred_central = np.clip(pred_central, 0, 100)
pred_inferior = np.clip(pred_inferior, 0, 100)
pred_superior = np.clip(pred_superior, 0, 100)

# ═══════════════════════════════════════════════════════════
#  5. TABLA RESUMEN (DataFrame)
# ═══════════════════════════════════════════════════════════

print(f"\n[5/6] Construyendo tabla de escenarios...")

tabla = pd.DataFrame({
    "fecha": fechas_futuras,
    "pesimista": np.round(pred_inferior, 1),
    "realista": np.round(pred_central, 1),
    "optimista": np.round(pred_superior, 1),
})
tabla["fecha"] = tabla["fecha"].dt.strftime("%Y-%m-%d")

# Medias de cada escenario
media_pesimista = pred_inferior.mean()
media_realista = pred_central.mean()
media_optimista = pred_superior.mean()

print(f"\n  Primeros 10 dias de prediccion:")
print(f"  {'Fecha':<14} {'Pesimista':<12} {'Realista':<12} {'Optimista':<12}")
print(f"  {'-'*14} {'-'*12} {'-'*12} {'-'*12}")
for _, row in tabla.head(10).iterrows():
    print(f"  {row['fecha']:<14} {row['pesimista']:<12.1f} {row['realista']:<12.1f} {row['optimista']:<12.1f}")

print(f"\n  OCUPACION MEDIA PREVISTA ({DIAS_PREDICCION} dias):")
print(f"    Pesimista:  {media_pesimista:.1f}%")
print(f"    Realista:   {media_realista:.1f}%")
print(f"    Optimista:  {media_optimista:.1f}%")

# ═══════════════════════════════════════════════════════════
#  6. GRAFICA: 3 LINEAS + BANDA SOMBREADA
# ═══════════════════════════════════════════════════════════
#  La banda sombreada entre pesimista y optimista representa
#  visualmente la incertidumbre de la prediccion.

print(f"\n[6/6] Generando grafica tres_escenarios.png...")

SALIDA.parent.mkdir(parents=True, exist_ok=True)

fig, ax = plt.subplots(figsize=(14, 5.5))
fig.patch.set_facecolor("#fafafa")
ax.set_facecolor("#fafafa")

# ── Banda sombreada (incertidumbre) ─────────────────────
#  Va primero para que las lineas queden encima
ax.fill_between(
    fechas_futuras,
    pred_inferior,
    pred_superior,
    color="#e8710a",
    alpha=0.12,
    label="Incertidumbre (IC 95%)",
)

# ── Linea pesimista (rojo-anaranjado, punteada) ─────────
ax.plot(
    fechas_futuras, pred_inferior,
    color="#c62828", linewidth=1.3, linestyle="--",
    marker="v", markersize=3,
    label=f"Pesimista — {media_pesimista:.1f}%",
)

# ── Linea realista (azul, gruesa, continua) ─────────────
ax.plot(
    fechas_futuras, pred_central,
    color="#1a73e8", linewidth=2.2,
    marker="o", markersize=3.5,
    label=f"Realista — {media_realista:.1f}%",
)

# ── Linea optimista (verde, punteada) ───────────────────
ax.plot(
    fechas_futuras, pred_superior,
    color="#2e7d32", linewidth=1.3, linestyle="--",
    marker="^", markersize=3,
    label=f"Optimista — {media_optimista:.1f}%",
)

# ── Ajustes del grafico ─────────────────────────────────
ax.set_ylabel("Ocupacion (%)")
ax.set_title(
    "Prediccion ocupacion — Tres escenarios (SARIMA)",
    fontsize=13, fontweight="bold",
)
ax.legend(loc="upper right", framealpha=0.9, fontsize=9)
ax.grid(axis="y", alpha=0.3)
ax.set_ylim(0, 105)
ax.xaxis.set_major_formatter(mdates.DateFormatter("%d-%b"))
ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=1))

fig.tight_layout()
fig.savefig(SALIDA, dpi=150)
plt.close(fig)

print(f"  Grafica guardada: {SALIDA.resolve()}")
if SALIDA.exists():
    print(f"  Tamano: {SALIDA.stat().st_size / 1024:.1f} KB")

# ═══════════════════════════════════════════════════════════
#  7. RESUMEN FINAL
# ═══════════════════════════════════════════════════════════

print(f"""
{'='*60}
RESUMEN — Bloque 5: Tres escenarios de prediccion
{'='*60}

Modelo: SARIMA{ORDER}{SEASONAL_ORDER}
Serie:  {len(serie)} dias historicos (ocupacion_real)
Rango:  {serie.index.min().date()} -> {serie.index.max().date()}

Prediccion: {DIAS_PREDICCION} dias hacia adelante

Escenarios (ocupacion media):
  Pesimista  ->  {media_pesimista:.1f}%  (limite inferior IC 95%)
  Realista   ->  {media_realista:.1f}%  (prediccion central)
  Optimista  ->  {media_optimista:.1f}%  (limite superior IC 95%)

Rango de incertidumbre: {media_optimista - media_pesimista:.1f} puntos
  (a mayor rango, menor certeza sobre el futuro)

Grafica: {SALIDA.resolve()}
""")

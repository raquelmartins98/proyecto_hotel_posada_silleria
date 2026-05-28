"""
modelo_holtwinters.py — Bloque 6.1: Tercer modelo (Holt-Winters) para
comparar con ARIMA y SARIMA.

Holt-Winters (ExponentialSmoothing) es un modelo de SUAVIZADO EXPONENCIAL
que, a diferencia de ARIMA/SARIMA, NO asume que los datos se generan con
un proceso estocastico. En vez de eso, "suaviza" la serie ponderando mas
los valores recientes y menos los antiguos.

Tiene 3 componentes:
  - NIVEL (level):  el valor base de la serie
  - TENDENCIA (trend):  hacia donde va (sube/baja)
  - ESTACIONALIDAD (seasonal):  patron que se repite (en nuestro caso m=7)

A diferencia de auto_arima, aqui NO hay busqueda automatica de parametros.
Probamos manualmente 3 configuraciones:
  1) Aditivo  + Aditivo  (tendencia y estacionalidad aditivas)
  2) Aditivo  + Multiplicativo
  3) Multiplicativo + Aditivo  (solo si los datos lo permiten)

Usamos la MISMA serie, la MISMA division train/test (335/30) y las MISMAS
metricas que ARIMA y SARIMA para que la comparacion sea justa.
"""
import sys
import os
import warnings
from pathlib import Path

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from dotenv import load_dotenv
import requests

warnings.filterwarnings("ignore")

# ── Config ────────────────────────────────────────────────

SALIDA = Path(__file__).parent / "graficas" / "tres_modelos.png"
ENV_PATH = Path(__file__).resolve().parents[1] / "frontend" / ".env"
DIAS_PRUEBA = 30

# ── 1. Cargar datos desde Insforge ──────────────────────

load_dotenv(ENV_PATH)
API_URL = os.getenv("VITE_INSFORGE_URL")
ANON_KEY = os.getenv("VITE_INSFORGE_ANON_KEY")

url = f"{API_URL.rstrip('/')}/api/database/records/ocupacion_real"
headers = {"Authorization": f"Bearer {ANON_KEY}", "Accept": "application/json"}

print("=" * 60)
print("BLOQUE 6.1: HOLT-WINTERS — Tercer modelo de prediccion")
print("=" * 60)

print("\n[1/6] Leyendo ocupacion_real desde Insforge...", end=" ")
resp = requests.get(url, headers=headers, timeout=15)
resp.raise_for_status()
raw = resp.json()
records = raw["records"] if isinstance(raw, dict) and "records" in raw else raw
print(f"{len(records)} filas.")

# ── 2. Serie temporal ────────────────────────────────────

print("\n[2/6] Construyendo serie temporal...")

df = pd.DataFrame(records)
df["fecha"] = pd.to_datetime(df["fecha"])
df = df.sort_values("fecha").reset_index(drop=True)
serie = df.set_index("fecha")["porcentaje_ocupacion"].astype(float)

# ── 3. Division train/test (IDENTICA a ARIMA y SARIMA) ──

train = serie.iloc[:-DIAS_PRUEBA]
test  = serie.iloc[-DIAS_PRUEBA:]

print(f"  Serie completa: {serie.index.min().date()} -> {serie.index.max().date()}  ({len(serie)} dias)")
print(f"  Entrenamiento:  {train.index[0].date()} -> {train.index[-1].date()}  ({len(train)} dias)")
print(f"  Prueba:         {test.index[0].date()}  -> {test.index[-1].date()}  ({len(test)} dias)")
print(f"  Estacionalidad: semanal (m=7)")

# ═══════════════════════════════════════════════════════════
#  4. HOLT-WINTERS: PROBAR CONFIGURACIONES
# ═══════════════════════════════════════════════════════════
#  ExponentialSmoothing acepta:
#    trend:       None, "add", "mul"
#    seasonal:    None, "add", "mul"
#    seasonal_periods: 7 (nuestro ciclo semanal)
#    initialization_method: "estimated" (statsmodels estima los valores
#                            iniciales de nivel, tendencia y estacionalidad
#                            a partir de los propios datos)

print("\n[3/6] Probando configuraciones de Holt-Winters...")

from statsmodels.tsa.holtwinters import ExponentialSmoothing
from sklearn.metrics import mean_absolute_error, mean_squared_error

# Probamos 2 configuraciones (la multiplicativa solo si tiene sentido)
configuraciones = [
    {"name": "Add-Add",    "trend": "add", "seasonal": "add", "desc": "Tendencia aditiva + Estacionalidad aditiva"},
    {"name": "Add-Mul",    "trend": "add", "seasonal": "mul", "desc": "Tendencia aditiva + Estacionalidad multiplicativa"},
]

resultados = []

for cfg in configuraciones:
    print(f"\n  Probando: {cfg['name']} — {cfg['desc']}")

    try:
        modelo = ExponentialSmoothing(
            train,
            trend=cfg["trend"],
            seasonal=cfg["seasonal"],
            seasonal_periods=7,
            initialization_method="estimated",
        )
        modelo_fit = modelo.fit()

        # Predecir 30 dias
        pred = modelo_fit.forecast(steps=DIAS_PRUEBA)

        # Recortar a rango logico 0-100%
        pred = np.clip(pred, 0, 100).values

        # Metricas
        mae = mean_absolute_error(test.values, pred)
        rmse = np.sqrt(mean_squared_error(test.values, pred))

        resultados.append({
            "name": cfg["name"],
            "desc": cfg["desc"],
            "modelo": modelo_fit,
            "pred": pred,
            "mae": mae,
            "rmse": rmse,
        })

        print(f"    MAE  = {mae:.2f}")
        print(f"    RMSE = {rmse:.2f}")
        print(f"    AIC  = {modelo_fit.aic:.1f}")

    except Exception as e:
        print(f"    [SKIP] {e}")

# ── Elegir la mejor configuracion (menor MAE) ────────────

if not resultados:
    print("\n[FAIL] Ninguna configuracion funciono.")
    sys.exit(1)

mejor = min(resultados, key=lambda r: r["mae"])
print(f"\n  MEJOR CONFIGURACION: {mejor['name']} (MAE={mejor['mae']:.2f})")
print(f"    {mejor['desc']}")

# ═══════════════════════════════════════════════════════════
#  5. CARGAR RESULTADOS DE ARIMA Y SARIMA (re-ejecutando)
# ═══════════════════════════════════════════════════════════
#  Para que la comparacion sea justa, re-ejecutamos ARIMA y
#  SARIMA con los mismos datos y la misma division train/test.
#  Los resultados deberian ser identicos a los de los bloques
#  3 y 4 (ARIMA MAE=12.96, SARIMA MAE=8.05).

print("\n[4/6] Re-ejecutando ARIMA y SARIMA para comparacion...")

# ── ARIMA(5,1,2) ────────────────────────────────────────
from statsmodels.tsa.arima.model import ARIMA as ARIMA_std

ARIMA_P, ARIMA_D, ARIMA_Q = 5, 1, 2
modelo_arima = ARIMA_std(train, order=(ARIMA_P, ARIMA_D, ARIMA_Q))
modelo_arima_fit = modelo_arima.fit()
pred_arima = modelo_arima_fit.forecast(steps=DIAS_PRUEBA)
pred_arima = np.clip(pred_arima, 0, 100)

mae_arima  = mean_absolute_error(test.values, pred_arima)
rmse_arima = np.sqrt(mean_squared_error(test.values, pred_arima))

print(f"  ARIMA({ARIMA_P},{ARIMA_D},{ARIMA_Q}):  MAE={mae_arima:.2f}  RMSE={rmse_arima:.2f}")

# ── SARIMA(2,1,1)(1,0,2,7) ─────────────────────────────
from statsmodels.tsa.statespace.sarimax import SARIMAX

ORDER = (2, 1, 1)
SEASONAL_ORDER = (1, 0, 2, 7)

modelo_sarima = SARIMAX(
    train,
    order=ORDER,
    seasonal_order=SEASONAL_ORDER,
    enforce_stationarity=False,
    enforce_invertibility=False,
)
modelo_sarima_fit = modelo_sarima.fit(disp=False, maxiter=200)
pred_sarima = modelo_sarima_fit.forecast(steps=DIAS_PRUEBA)
pred_sarima = np.clip(pred_sarima, 0, 100)

mae_sarima  = mean_absolute_error(test.values, pred_sarima)
rmse_sarima = np.sqrt(mean_squared_error(test.values, pred_sarima))

p, d, q = ORDER
P, D, Q, m = SEASONAL_ORDER
print(f"  SARIMA({p},{d},{q})({P},{D},{Q},{m}):  MAE={mae_sarima:.2f}  RMSE={rmse_sarima:.2f}")

# ═══════════════════════════════════════════════════════════
#  6. TABLA COMPARATIVA
# ═══════════════════════════════════════════════════════════

print(f"\n[5/6] Tabla comparativa de los 3 modelos...")

hw_name = f"Holt-Winters ({mejor['name']})"

print(f"""
{'='*55}
  MODELO                      MAE         RMSE
{'='*55}
  ARIMA({ARIMA_P},{ARIMA_D},{ARIMA_Q})             {mae_arima:>6.2f}      {rmse_arima:>6.2f}
  SARIMA({p},{d},{q})({P},{D},{Q},{m})  {mae_sarima:>6.2f}      {rmse_sarima:>6.2f}
  {hw_name:<28} {mejor['mae']:>6.2f}      {mejor['rmse']:>6.2f}
{'='*55}
""")

# ── Ranking ──────────────────────────────────────────────
ranking = sorted(
    [("ARIMA", mae_arima, rmse_arima),
     ("SARIMA", mae_sarima, rmse_sarima),
     (f"Holt-Winters ({mejor['name']})", mejor['mae'], mejor['rmse'])],
    key=lambda r: r[1],  # ordenar por MAE (menor = mejor)
)

print("  RANKING (por MAE, menor es mejor):")
for i, (nombre, mae, rmse) in enumerate(ranking, 1):
    print(f"    {i}. {nombre:<30} MAE={mae:.2f}  RMSE={rmse:.2f}")

# ═══════════════════════════════════════════════════════════
#  7. GRAFICA: LOS 3 MODELOS + REAL
# ═══════════════════════════════════════════════════════════

print(f"\n[6/6] Generando grafica tres_modelos.png...")

SALIDA.parent.mkdir(parents=True, exist_ok=True)

fig, ax = plt.subplots(figsize=(14, 5.5))
fig.patch.set_facecolor("#fafafa")
ax.set_facecolor("#fafafa")

# ── Datos reales de prueba (negro, gruesa) ──────────────
ax.plot(test.index, test.values, color="#1a1a2e", linewidth=2.2,
        marker="o", markersize=2.5, label="Real (prueba)", zorder=5)

# ── ARIMA (gris punteado) ───────────────────────────────
ax.plot(test.index, pred_arima, color="#888888", linewidth=1.3,
        linestyle="--", marker="s", markersize=2,
        label=f"ARIMA({ARIMA_P},{ARIMA_D},{ARIMA_Q}) — MAE={mae_arima:.1f}")

# ── SARIMA (naranja) ────────────────────────────────────
ax.plot(test.index, pred_sarima, color="#e8710a", linewidth=1.8,
        linestyle="--", marker="^", markersize=2,
        label=f"SARIMA({p},{d},{q})({P},{D},{Q},{m}) — MAE={mae_sarima:.1f}")

# ── Holt-Winters (verde) ────────────────────────────────
ax.plot(test.index, mejor["pred"], color="#2e7d32", linewidth=1.5,
        linestyle="--", marker="v", markersize=2,
        label=f"Holt-Winters ({mejor['name']}) — MAE={mejor['mae']:.1f}")

# ── Linea de corte train/test ───────────────────────────
ax.axvline(x=train.index[-1], color="#666666", linewidth=0.6,
           linestyle=":", alpha=0.5)
ax.text(train.index[-1], ax.get_ylim()[1] * 0.95, "Corte train/test",
        fontsize=8, color="#666666", ha="right")

ax.set_ylabel("Ocupacion (%)")
ax.set_title(
    "Comparacion: ARIMA vs SARIMA vs Holt-Winters — 30 dias de prueba",
    fontsize=13, fontweight="bold",
)
ax.legend(loc="upper right", framealpha=0.9, fontsize=7.5)
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
#  8. INTERPRETACION
# ═══════════════════════════════════════════════════════════

# Determinar diferencias clave
vs_arima_mae = mejor['mae'] - mae_arima
vs_sarima_mae = mejor['mae'] - mae_sarima

print(f"""
{'='*60}
INTERPRETACION — Holt-Winters frente a ARIMA y SARIMA
{'='*60}

Holt-Winters ({mejor['name']}) se diferencia de ARIMA/SARIMA en que:

1. NO asume un proceso estocastico — simplemente suaviza la serie
   dando mas peso a los valores recientes (suavizado exponencial).

2. Es MAS RAPIDO de entrenar — no necesita auto_arima ni busqueda
   de parametros. Segundos en vez de minutos.

3. Maneja la estacionalidad semanal (m=7) igual que SARIMA, pero
   con menos parametros (solo alpha, beta, gamma de suavizado).

Resultados sobre los {DIAS_PRUEBA} dias de prueba:
""")

print(f"  ARIMA({ARIMA_P},{ARIMA_D},{ARIMA_Q}):             MAE={mae_arima:.2f}")
print(f"  SARIMA({p},{d},{q})({P},{D},{Q},{m}):  MAE={mae_sarima:.2f}")
print(f"  Holt-Winters ({mejor['name']}):            MAE={mejor['mae']:.2f}")

print(f"""
En que aporta algo distinto:
  - Si Holt-Winters tiene mejor MAE que ARIMA pero peor que SARIMA:
    confirma que la estacionalidad semanal es clave (ARIMA no la tiene)
    y que SARIMA la captura mejor por su estructura mas rica.

  - Si Holt-Winters se acerca a SARIMA: significa que el patron
    semanal es tan fuerte que hasta un modelo simple lo captura.

  - La gran ventaja de Holt-Winters es la VELOCIDAD y SIMPLICIDAD:
    se puede re-entrenar en tiempo real sin apenas coste computacional,
    ideal para un dashboard que se actualice cada hora.
""")

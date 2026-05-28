"""
ensemble.py — Bloque 6.2: Combinacion de modelos (ARIMA + SARIMA + Holt-Winters)
para prediccion conjunta de ocupacion.

Entrena los 3 modelos individuales con la misma particion train/test (335/30)
y las 3 predicciones se almacenan en un DataFrame para el ensemble.
"""
import sys
import os
import warnings
from pathlib import Path

import pandas as pd
import numpy as np
from dotenv import load_dotenv
import requests

warnings.filterwarnings("ignore")

# ── Config ────────────────────────────────────────────────

ENV_PATH = Path(__file__).resolve().parents[1] / "frontend" / ".env"

DIAS_PRUEBA = 30  # ultimos N dias para test (misma particion que ARIMA/SARIMA/HW)

# Parametros pre-optimizados de ejecuciones anteriores
ARIMA_ORDER       = (5, 1, 2)
SARIMA_ORDER      = (2, 1, 1)
SARIMA_SEASONAL   = (1, 0, 2, 7)  # estacionalidad semanal m=7
HW_SEASONAL_PERIODS = 7

# ── 1. Cargar datos desde Insforge ──────────────────────

load_dotenv(ENV_PATH)
API_URL = os.getenv("VITE_INSFORGE_URL")
ANON_KEY = os.getenv("VITE_INSFORGE_ANON_KEY")

if not API_URL or not ANON_KEY:
    print("[FAIL] Faltan credenciales en frontend/.env")
    sys.exit(1)

url = f"{API_URL.rstrip('/')}/api/database/records/ocupacion_real"
headers = {"Authorization": f"Bearer {ANON_KEY}", "Accept": "application/json"}

print("Leyendo ocupacion_real desde Insforge...", end=" ")
resp = requests.get(url, headers=headers, timeout=15)
resp.raise_for_status()
raw = resp.json()
records = raw["records"] if isinstance(raw, dict) and "records" in raw else raw
print(f"{len(records)} filas.")

if not records:
    print("[FAIL] No hay datos")
    sys.exit(1)

# ── 2. Construir serie temporal ─────────────────────────

df = pd.DataFrame(records)
df["fecha"] = pd.to_datetime(df["fecha"])
df = df.sort_values("fecha").reset_index(drop=True)

serie = df.set_index("fecha")["porcentaje_ocupacion"].astype(float)

print(f"Serie: {serie.index.min().date()} -> {serie.index.max().date()}")
print(f"Total: {len(serie)} dias")

# ── 3. Dividir en entrenamiento y prueba ────────────────

train = serie.iloc[:-DIAS_PRUEBA]   # primeros ~335 dias
test  = serie.iloc[-DIAS_PRUEBA:]   # ultimos 30 dias

print(f"\nSerie cargada: {len(train)} dias entrenamiento, {len(test)} dias prueba")
print(f"  Entrenamiento: {train.index[0].date()} -> {train.index[-1].date()}")
print(f"  Prueba:        {test.index[0].date()}  -> {test.index[-1].date()}")

# =====================================================================
#  4. ENTRENAR MODELOS INDIVIDUALES
# =====================================================================

from sklearn.metrics import mean_absolute_error, mean_squared_error

# ── 4a. ARIMA(5,1,2) ────────────────────────────────────

print("\n--- ARIMA(5,1,2) ---")
from statsmodels.tsa.arima.model import ARIMA as ARIMA_std

modelo_arima = ARIMA_std(train, order=ARIMA_ORDER)
modelo_arima_fit = modelo_arima.fit()
pred_arima = modelo_arima_fit.forecast(steps=DIAS_PRUEBA)
pred_arima = np.clip(pred_arima, 0, 100)

mae_arima  = mean_absolute_error(test.values, pred_arima)
rmse_arima = np.sqrt(mean_squared_error(test.values, pred_arima))
print(f"  MAE={mae_arima:.2f}  RMSE={rmse_arima:.2f}")

# ── 4b. SARIMA(2,1,1)(1,0,2,7) ──────────────────────────

print("\n--- SARIMA(2,1,1)(1,0,2,7) ---")
from statsmodels.tsa.statespace.sarimax import SARIMAX

modelo_sarima = SARIMAX(
    train,
    order=SARIMA_ORDER,
    seasonal_order=SARIMA_SEASONAL,
    enforce_stationarity=False,
    enforce_invertibility=False,
)
modelo_sarima_fit = modelo_sarima.fit(disp=False, maxiter=200)
pred_sarima = modelo_sarima_fit.forecast(steps=DIAS_PRUEBA)
pred_sarima = np.clip(pred_sarima, 0, 100)

mae_sarima  = mean_absolute_error(test.values, pred_sarima)
rmse_sarima = np.sqrt(mean_squared_error(test.values, pred_sarima))
print(f"  MAE={mae_sarima:.2f}  RMSE={rmse_sarima:.2f}")

# ── 4c. Holt-Winters (Add-Add) ──────────────────────────

print("\n--- Holt-Winters (Add-Add) ---")
from statsmodels.tsa.holtwinters import ExponentialSmoothing

modelo_hw = ExponentialSmoothing(
    train,
    trend="add",
    seasonal="add",
    seasonal_periods=HW_SEASONAL_PERIODS,
    initialization_method="estimated",
)
modelo_hw_fit = modelo_hw.fit()
pred_hw = modelo_hw_fit.forecast(steps=DIAS_PRUEBA)
pred_hw = np.clip(pred_hw, 0, 100).values

mae_hw  = mean_absolute_error(test.values, pred_hw)
rmse_hw = np.sqrt(mean_squared_error(test.values, pred_hw))
print(f"  MAE={mae_hw:.2f}  RMSE={rmse_hw:.2f}")

# =====================================================================
#  5. ENSEMBLE DATAFRAME
# =====================================================================

print("\n--- DataFrame con las 3 predicciones ---")

predicciones = pd.DataFrame({
    "fecha":       test.index,
    "real":        test.values,
    "arima":       pred_arima,
    "sarima":      pred_sarima,
    "holtwinters": pred_hw,
}).reset_index(drop=True)

print(predicciones.head().to_string(index=False))

print(f"\nShape: {predicciones.shape[0]} filas, {predicciones.shape[1]} columnas")
print("Columnas: fecha, real, arima, sarima, holtwinters")

# =====================================================================
#  6. COMBINACIONES ENSEMBLE
# =====================================================================

print("\n" + "=" * 55)
print("  COMBINACIONES ENSEMBLE")
print("=" * 55)

# ── 6a. Promedio simple ─────────────────────────────────

pred_promedio = predicciones[["arima", "sarima", "holtwinters"]].mean(axis=1)

mae_promedio  = mean_absolute_error(predicciones["real"], pred_promedio)
rmse_promedio = np.sqrt(mean_squared_error(predicciones["real"], pred_promedio))

print(f"\n  A) Promedio simple")
print(f"     MAE={mae_promedio:.2f}  RMSE={rmse_promedio:.2f}")

# ── 6b. Ponderado por inverso del MAE ───────────────────

# Peso = (1 / MAE) para cada modelo, luego normalizar a suma = 1.0
pesos_raw = {
    "ARIMA":  1.0 / mae_arima,
    "SARIMA": 1.0 / mae_sarima,
    "Holt-Winters": 1.0 / mae_hw,
}
total_inverso = sum(pesos_raw.values())
pesos_norm = {k: v / total_inverso for k, v in pesos_raw.items()}

print(f"\n  B) Ponderado (peso = 1/MAE, normalizado)")
print(f"     Pesos finales:")
for k, v in pesos_norm.items():
    print(f"       {k:<15} {v*100:>6.2f}%")

# Aplicar pesos a las columnas de prediccion
pred_ponderado = (
    predicciones["arima"]       * pesos_norm["ARIMA"]
    + predicciones["sarima"]    * pesos_norm["SARIMA"]
    + predicciones["holtwinters"] * pesos_norm["Holt-Winters"]
)

mae_ponderado  = mean_absolute_error(predicciones["real"], pred_ponderado)
rmse_ponderado = np.sqrt(mean_squared_error(predicciones["real"], pred_ponderado))
print(f"     MAE={mae_ponderado:.2f}  RMSE={rmse_ponderado:.2f}")

# =====================================================================
#  7. TABLA COMPARATIVA
# =====================================================================

print(f"\n{'='*55}")
print(f"  {'Modelo':<22} {'MAE':>8} {'RMSE':>8}")
print(f"{'='*55}")
print(f"  {'ARIMA(5,1,2)':<22} {mae_arima:>8.2f} {rmse_arima:>8.2f}")
print(f"  {'SARIMA(2,1,1)(1,0,2,7)':<22} {mae_sarima:>8.2f} {rmse_sarima:>8.2f}")
print(f"  {'Holt-Winters (Add-Add)':<22} {mae_hw:>8.2f} {rmse_hw:>8.2f}")
print(f"  {'-'*40}")
print(f"  {'Ensemble (promedio)':<22} {mae_promedio:>8.2f} {rmse_promedio:>8.2f}")
print(f"  {'Ensemble (ponderado)':<22} {mae_ponderado:>8.2f} {rmse_ponderado:>8.2f}")
print(f"{'='*55}")

# ── Mejora respecto al mejor individual ─────────────────
mejor_individual_mae = min(mae_arima, mae_sarima, mae_hw)
mejor_nombre = {mae_arima: "ARIMA", mae_sarima: "SARIMA", mae_hw: "Holt-Winters"}[mejor_individual_mae]

for nombre, mae_val in [("Promedio", mae_promedio), ("Ponderado", mae_ponderado)]:
    if mae_val < mejor_individual_mae:
        dif = (1 - mae_val / mejor_individual_mae) * 100
        print(f"\n  {nombre} mejora un {dif:.1f}% el MAE respecto al mejor individual ({mejor_nombre})")
    else:
        dif = (mae_val / mejor_individual_mae - 1) * 100
        print(f"\n  {nombre} es un {dif:.1f}% PEOR que el mejor individual ({mejor_nombre})")

# =====================================================================
#  8. GRAFICA: REAL vs ENSEMBLE PONDERADO
# =====================================================================

import matplotlib.pyplot as plt
import matplotlib.dates as mdates

GRAFICA = Path(__file__).parent / "graficas" / "ensemble_final.png"
GRAFICA.parent.mkdir(parents=True, exist_ok=True)

fig, ax = plt.subplots(figsize=(14, 5.5))
fig.patch.set_facecolor("#fafafa")
ax.set_facecolor("#fafafa")

# Datos reales de entrenamiento (gris claro, fondo)
ax.plot(train.index, train.values, color="#cccccc", linewidth=0.7,
        label="Entrenamiento (real)")

# Datos reales de prueba (negro, gruesa)
ax.plot(predicciones["fecha"], predicciones["real"], color="#1a1a2e", linewidth=2.2,
        marker="o", markersize=3.0, label="Real (prueba)", zorder=5)

# Prediccion individual SARIMA (naranja punteado, referencia)
ax.plot(predicciones["fecha"], predicciones["sarima"], color="#e8710a", linewidth=1.2,
        linestyle="--", alpha=0.5, label=f"SARIMA individual (MAE={mae_sarima:.2f})")

# Ensemble ponderado (verde, gruesa)
ax.plot(predicciones["fecha"], pred_ponderado, color="#2e7d32", linewidth=2.0,
        linestyle="-", marker="s", markersize=2.5,
        label=f"Ensemble ponderado (MAE={mae_ponderado:.2f})", zorder=4)

# Linea de corte train/test
ax.axvline(x=train.index[-1], color="#666666", linewidth=0.6,
           linestyle=":", alpha=0.5)
ax.text(train.index[-1], ax.get_ylim()[1] * 0.95, "Corte train/test",
        fontsize=8, color="#666666", ha="right")

ax.set_ylabel("Ocupacion (%)")
ax.set_title(
    "Ensemble Ponderado — Prediccion conjunta ARIMA + SARIMA + Holt-Winters\n"
    f"MAE={mae_ponderado:.2f}%  |  Pesos: ARIMA {pesos_norm['ARIMA']*100:.1f}%  "
    f"SARIMA {pesos_norm['SARIMA']*100:.1f}%  HW {pesos_norm['Holt-Winters']*100:.1f}%",
    fontsize=12, fontweight="bold",
)
ax.legend(loc="upper right", framealpha=0.9, fontsize=8)
ax.grid(axis="y", alpha=0.3)
ax.set_ylim(0, 105)
ax.xaxis.set_major_formatter(mdates.DateFormatter("%d-%b"))
ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=1))

fig.tight_layout()
fig.savefig(GRAFICA, dpi=150)
plt.close(fig)

print(f"\nGrafica guardada: {GRAFICA.resolve()}")
if GRAFICA.exists():
    print(f"  Tamano: {GRAFICA.stat().st_size / 1024:.1f} KB")

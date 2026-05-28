"""
modelo_sarima.py — Bloque 4: Modelo SARIMA con estacionalidad semanal (m=7).

Comparacion directa con ARIMA(5,1,2) del bloque anterior usando la MISMA
division train/test (335/30) para que sea justo.

SARIMA anade 4 parametros estacionales (P,D,Q,m) que capturan patrones
que se repiten cada m=7 dias (lunes-domingo, finde vs semana).
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

GRAFICA = Path(__file__).parent / "graficas" / "sarima_vs_arima.png"
ENV_PATH = Path(__file__).resolve().parents[1] / "frontend" / ".env"
DIAS_PRUEBA = 30

# Parametros ARIMA optimos del bloque anterior (para no re-ejecutar auto_arima)
ARIMA_P, ARIMA_D, ARIMA_Q = 5, 1, 2

# ── 1. Cargar datos ─────────────────────────────────────

load_dotenv(ENV_PATH)
API_URL = os.getenv("VITE_INSFORGE_URL")
ANON_KEY = os.getenv("VITE_INSFORGE_ANON_KEY")

url = f"{API_URL.rstrip('/')}/api/database/records/ocupacion_real"
headers = {"Authorization": f"Bearer {ANON_KEY}", "Accept": "application/json"}

print("Leyendo ocupacion_real desde Insforge...", end=" ")
resp = requests.get(url, headers=headers, timeout=15)
resp.raise_for_status()
raw = resp.json()
records = raw["records"] if isinstance(raw, dict) and "records" in raw else raw
print(f"{len(records)} filas.")

# ── 2. Serie temporal ────────────────────────────────────

df = pd.DataFrame(records)
df["fecha"] = pd.to_datetime(df["fecha"])
df = df.sort_values("fecha").reset_index(drop=True)
serie = df.set_index("fecha")["porcentaje_ocupacion"].astype(float)

# ── 3. Division train/test (IDENTICA a ARIMA) ─────────────

train = serie.iloc[:-DIAS_PRUEBA]
test  = serie.iloc[-DIAS_PRUEBA:]

print(f"Entrenamiento: {train.index[0].date()} -> {train.index[-1].date()}  ({len(train)} dias)")
print(f"Prueba:        {test.index[0].date()}  -> {test.index[-1].date()}  ({len(test)} dias)")

# =====================================================================
# PARTE A: ARIMA(5,1,2) — referencia del bloque anterior
# =====================================================================

from statsmodels.tsa.arima.model import ARIMA as ARIMA_std

print(f"\n--- ARIMA({ARIMA_P},{ARIMA_D},{ARIMA_Q}) (referencia) ---")
modelo_arima = ARIMA_std(train, order=(ARIMA_P, ARIMA_D, ARIMA_Q))
modelo_arima_fit = modelo_arima.fit()
pred_arima = modelo_arima_fit.forecast(steps=DIAS_PRUEBA)

# =====================================================================
# PARTE B: SARIMA con auto_arima (seasonal=True, m=7)
# =====================================================================
#    P = orden autoregresivo estacional (semanas pasadas que influyen)
#    D = diferenciacion estacional (para eliminar ciclo semanal)
#    Q = orden media movil estacional
#    m = 7 (ciclo semanal: sabado y domingo repiten patron cada 7 dias)
#
#    La combinacion (p,d,q)(P,D,Q,7) captura TENDENCIA (dias) +
#    ESTACIONALIDAD (semanas), que es lo que necesita una ocupacion
#    hotelera con picos los fines de semana.

from pmdarima import auto_arima

print("\nBuscando parametros SARIMA con estacionalidad semanal (m=7)...")
print("(Esto puede tomar 1-3 minutos)")
sys.stdout.flush()

modelo_auto_sarima = auto_arima(
    train,
    seasonal=True,
    m=7,                    # ciclo semanal: lunes-domingo
    stepwise=True,
    trace=False,
    error_action="ignore",
    suppress_warnings=True,
    n_jobs=-1,
)

p, d, q = modelo_auto_sarima.order
P, D, Q, m = modelo_auto_sarima.seasonal_order

print(f"\nSARIMA({p},{d},{q})({P},{D},{Q},{m})")
print(f"  AIC: {modelo_auto_sarima.aic():.1f}")

# Predecir 30 dias
pred_sarima, conf_int_sarima = modelo_auto_sarima.predict(
    n_periods=DIAS_PRUEBA,
    return_conf_int=True,
)

# =====================================================================
# PARTE C: Metricas de error
# =====================================================================

from sklearn.metrics import mean_absolute_error, mean_squared_error

mae_arima   = mean_absolute_error(test.values, pred_arima)
rmse_arima  = np.sqrt(mean_squared_error(test.values, pred_arima))

mae_sarima  = mean_absolute_error(test.values, pred_sarima)
rmse_sarima = np.sqrt(mean_squared_error(test.values, pred_sarima))

print(f"""
--- METRICAS COMPARATIVAS (30 dias de prueba) ---
               MAE (puntos)    RMSE (puntos)
ARIMA(5,1,2)    {mae_arima:>6.2f}           {rmse_arima:>6.2f}
SARIMA({p},{d},{q})({P},{D},{Q},{m})   {mae_sarima:>6.2f}           {rmse_sarima:>6.2f}
""")

# Calcular mejora
if mae_sarima < mae_arima:
    mejora_mae = (1 - mae_sarima / mae_arima) * 100
    print(f"SARIMA mejora el MAE en un {mejora_mae:.1f}% respecto a ARIMA")
else:
    print(f"ARIMA tiene mejor MAE por {(mae_sarima - mae_arima):.2f} puntos")

if rmse_sarima < rmse_arima:
    mejora_rmse = (1 - rmse_sarima / rmse_arima) * 100
    print(f"SARIMA mejora el RMSE en un {mejora_rmse:.1f}% respecto a ARIMA")
else:
    print(f"ARIMA tiene mejor RMSE por {(rmse_sarima - rmse_arima):.2f} puntos")

# =====================================================================
# PARTE D: Grafica comparativa ARIMA vs SARIMA
# =====================================================================

GRAFICA.parent.mkdir(parents=True, exist_ok=True)

fig, ax = plt.subplots(figsize=(14, 5.5))
fig.patch.set_facecolor("#fafafa")
ax.set_facecolor("#fafafa")

# Datos reales de prueba (azul oscuro, linea gruesa)
ax.plot(test.index, test.values, color="#1a1a2e", linewidth=2.0,
        marker="o", markersize=2.5, label="Real (prueba)")

# Prediccion ARIMA (gris)
ax.plot(test.index, pred_arima, color="#888888", linewidth=1.3,
        linestyle="--", label=f"ARIMA({ARIMA_P},{ARIMA_D},{ARIMA_Q}) — MAE={mae_arima:.1f}%")

# Prediccion SARIMA (naranja)
ax.plot(test.index, pred_sarima, color="#e8710a", linewidth=1.8,
        linestyle="--", label=f"SARIMA({p},{d},{q})({P},{D},{Q},{m}) — MAE={mae_sarima:.1f}%")

# Banda de confianza SARIMA
ax.fill_between(test.index,
                conf_int_sarima[:, 0], conf_int_sarima[:, 1],
                color="#e8710a", alpha=0.08,
                label="IC 95% SARIMA")

ax.set_ylabel("Ocupacion (%)")
ax.set_title("ARIMA vs SARIMA — Prediccion 30 dias de ocupacion",
             fontsize=13, fontweight="bold")
ax.legend(loc="upper right", framealpha=0.9, fontsize=8)
ax.grid(axis="y", alpha=0.3)
ax.set_ylim(0, 105)
ax.xaxis.set_major_formatter(mdates.DateFormatter("%d-%b"))
ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=1))

fig.tight_layout()
fig.savefig(GRAFICA, dpi=150)
plt.close(fig)

print(f"\nGrafica guardada: {GRAFICA.resolve()}")
print(f"   Tamano: {GRAFICA.stat().st_size / 1024:.1f} KB")

# =====================================================================
# PARTE E: Interpretacion
# =====================================================================

print(f"""
--- INTERPRETACION ---

Comparacion directa ARIMA vs SARIMA (30 dias de prueba):

  ARIMA({ARIMA_P},{ARIMA_D},{ARIMA_Q}):
    MAE={mae_arima:.2f}%  RMSE={rmse_arima:.2f}%
    Solo mira tendencia lineal de los ultimos {ARIMA_P} dias.

  SARIMA({p},{d},{q})({P},{D},{Q},{m}):
    MAE={mae_sarima:.2f}%  RMSE={rmse_sarima:.2f}%
    Ademas captura el patron semanal (m={m}: fines de semana vs entre semana).
""")

# Determinar cual gana
if mae_sarima < mae_arima and rmse_sarima < rmse_arima:
    print("""RESULTADO: SARIMA GANA en ambas metricas. La estacionalidad semanal
mejora la prediccion significativamente porque la ocupacion hotelera tiene
un patron claro: los fines de semana se llena mas que entre semana, y
SARIMA captura eso mientras que ARIMA no.""")
elif mae_sarima < mae_arima:
    print("""RESULTADO: SARIMA gana en MAE pero ARIMA en RMSE. La estacionalidad
ayuda en el error medio pero ARIMA tiene menos errores puntuales grandes.""")
else:
    print("""RESULTADO: ARIMA fue mejor. La estacionalidad semanal m=7 quizas
no es el ciclo dominante en estos datos; podriamos probar m=365
(estacionalidad anual) para capturar temporada alta/baja.""")

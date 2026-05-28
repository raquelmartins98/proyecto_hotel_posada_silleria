"""
modelo_arima.py — Bloque 3: Primer modelo ARIMA sobre ocupacion_real.

1) Lee la serie de 365 dias desde Insforge (reutiliza logica de conexion)
2) Divide en entrenamiento (~335 dias) y prueba (30 dias)
3) auto_arima encuentra (p,d,q) optimos sin estacionalidad
4) Predice 30 dias futuros y compara con valores reales
5) Calcula MAE y RMSE
6) Genera grafica comparativa
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

# Silenciar warnings verbosos de statsmodels durante auto_arima
warnings.filterwarnings("ignore")

# ── Config ────────────────────────────────────────────────

GRAFICA = Path(__file__).parent / "graficas" / "arima_prediccion.png"
ENV_PATH = Path(__file__).resolve().parents[1] / "frontend" / ".env"

DIAS_PRUEBA = 30  # ultimos N dias para test

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

# ── 2. Construir serie temporal ─────────────────────────

df = pd.DataFrame(records)
df["fecha"] = pd.to_datetime(df["fecha"])
df = df.sort_values("fecha").reset_index(drop=True)

serie = df.set_index("fecha")["porcentaje_ocupacion"].astype(float)

print(f"Serie: {serie.index.min().date()} -> {serie.index.max().date()}")
print(f"Total: {len(serie)} dias")

# ── 3. Dividir en entrenamiento y prueba ────────────────
#    MOTIVO: Nunca evaluamos un modelo con datos que ya vio.
#    Entrenamos con ~335 dias, guardamos los ultimos 30 para medir.

train = serie.iloc[:-DIAS_PRUEBA]   # primeros ~335 dias
test  = serie.iloc[-DIAS_PRUEBA:]   # ultimos 30 dias

print(f"\nEntrenamiento: {train.index[0].date()} -> {train.index[-1].date()}  ({len(train)} dias)")
print(f"Prueba:        {test.index[0].date()}  -> {test.index[-1].date()}  ({len(test)} dias)")

# ── 4. auto_arima — busca (p,d,q) optimos ──────────────
#    p = orden autoregresivo (cuantos dias pasados influyen)
#    d = diferenciacion (cuantas veces restamos la serie a si misma
#        para hacerla estacionaria — sin tendencia)
#    q = orden de media movil (cuantos errores pasados influyen)
#
#    seasonal=False: la estacionalidad la reservamos para SARIMA.

print("\nBuscando parametros (p,d,q) optimos con auto_arima...")
print("(Esto puede tomar 30-60 segundos)")
sys.stdout.flush()

from pmdarima import auto_arima

modelo_auto = auto_arima(
    train,
    seasonal=False,        # sin estacionalidad (SARIMA en bloque 4)
    stepwise=True,         # busqueda gradual (mas rapida)
    trace=False,           # no imprimir cada intento
    error_action="ignore",
    suppress_warnings=True,
    n_jobs=-1,             # usar todos los CPUs
)

p, d, q = modelo_auto.order
print(f"\nParametros seleccionados: (p={p}, d={d}, q={q})")
print(f"  AIC (criterio de calidad): {modelo_auto.aic():.1f}")

# ── 5. Entrenar modelo final ────────────────────────────

print("\nEntrenando modelo ARIMA final...")
modelo = modelo_auto  # auto_arima ya lo entreno internamente

# ── 6. Predecir los 30 dias de prueba ──────────────────
#    predict_in_sample con conf_int=True nos da intervalos de confianza
#    para el periodo que ya tiene datos (el test).

pred_result = modelo.predict_in_sample(
    start=len(train),
    end=len(train) + len(test) - 1,
    return_conf_int=True,
)

# predict_in_sample devuelve (predicciones, intervalos_de_confianza)
predichos = pred_result[0]
conf_int  = pred_result[1]

# ── 7. Metricas de error ───────────────────────────────
#    MAE = error absoluto medio (misma unidad que los datos: % ocupacion)
#    RMSE = raiz del error cuadratico medio (penaliza mas errores grandes)

from sklearn.metrics import mean_absolute_error, mean_squared_error

mae  = mean_absolute_error(test.values, predichos)
rmse = np.sqrt(mean_squared_error(test.values, predichos))

print(f"\nMetricas sobre los {DIAS_PRUEBA} dias de prueba:")
print(f"  MAE  = {mae:.2f} puntos de ocupacion")
print(f"  RMSE = {rmse:.2f} puntos de ocupacion")

# ── 8. Grafica comparativa ──────────────────────────────

GRAFICA.parent.mkdir(parents=True, exist_ok=True)

fig, ax = plt.subplots(figsize=(14, 5.5))
fig.patch.set_facecolor("#fafafa")
ax.set_facecolor("#fafafa")

# Datos reales de entrenamiento (gris claro)
ax.plot(train.index, train.values, color="#999999", linewidth=0.8,
        label="Entrenamiento (real)")

# Datos reales de prueba (azul)
ax.plot(test.index, test.values, color="#1a73e8", linewidth=1.5,
        label="Prueba (real)")

# Prediccion del modelo (naranja)
ax.plot(test.index, predichos, color="#e8710a", linewidth=1.5,
        linestyle="--", label=f"Prediccion ARIMA({p},{d},{q})")

# Banda de confianza del 95%
ax.fill_between(test.index,
                conf_int[:, 0], conf_int[:, 1],
                color="#e8710a", alpha=0.12,
                label="IC 95%")

ax.axvline(x=train.index[-1], color="#666666", linewidth=0.6,
           linestyle=":", alpha=0.5)
ax.text(train.index[-1], ax.get_ylim()[1] * 0.95, "Corte train/test",
        fontsize=8, color="#666666", ha="right")

ax.set_ylabel("Ocupacion (%)")
ax.set_title(f"ARIMA({p},{d},{q}) — Prediccion ocupacion 30 dias\n"
             f"MAE={mae:.2f}%  RMSE={rmse:.2f}%",
             fontsize=12, fontweight="bold")
ax.legend(loc="upper right", framealpha=0.9)
ax.grid(axis="y", alpha=0.3)
ax.set_ylim(0, 105)
ax.xaxis.set_major_formatter(mdates.DateFormatter("%d-%b"))
ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=1))

fig.tight_layout()
fig.savefig(GRAFICA, dpi=150)
plt.close(fig)

print(f"\nGrafica guardada: {GRAFICA.resolve()}")
print(f"   Tamano: {GRAFICA.stat().st_size / 1024:.1f} KB")

# ── 9. Interpretacion sencilla ──────────────────────────

print(f"""
--- INTERPRETACION ---

ARIMA({p},{d},{q}) sobre los ultimos {DIAS_PRUEBA} dias:

  MAE  = {mae:.2f} puntos  -> de media, el modelo se equivoca en {mae:.1f} puntos de ocupacion
  RMSE = {rmse:.2f} puntos  -> penaliza errores grandes; si RMSE > MAE x 1.5 hay
                                algunos dias donde falla bastante

La ocupacion media del periodo de prueba es {test.mean():.1f}%.
Relacion MAE/media: {mae/test.mean()*100:.1f}% de error relativo.
""")

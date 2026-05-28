"""
volcar_predicciones.py — Camino B, paso 2/4: Genera las predicciones
SARIMA y las inserta (upsert) en la tabla predicciones de Insforge
via REST API.

Flujo:
  1) Lee ocupacion_real desde Insforge
  2) Entrena SARIMA(2,1,1)(1,0,2,7) sobre la serie completa
  3) Genera 30 dias de prediccion con 3 escenarios
  4) Upsert en tabla predicciones (fecha es UNIQUE)
  5) Verifica los datos insertados
"""
import sys
import os
import warnings
from pathlib import Path
from datetime import datetime, timedelta

import pandas as pd
import numpy as np
from dotenv import load_dotenv
import requests

warnings.filterwarnings("ignore")

# ── Config ────────────────────────────────────────────────

ENV_PATH = Path(__file__).resolve().parents[1] / "frontend" / ".env"
DIAS_PREDICCION = 30

# Parametros SARIMA pre-optimizados (Bloque 4)
SARIMA_ORDER = (2, 1, 1)
SARIMA_SEASONAL = (1, 0, 2, 7)

# ── Conectar a Insforge ──────────────────────────────

load_dotenv(ENV_PATH)
API_URL = os.getenv("VITE_INSFORGE_URL")
ANON_KEY = os.getenv("VITE_INSFORGE_ANON_KEY")

# API Key de admin (del MCP) para writes
ADMIN_KEY = "ik_371927c198260f2bf08eb13ba70a8d42"

if not API_URL or not ANON_KEY:
    print("[FAIL] Faltan credenciales en frontend/.env")
    sys.exit(1)

BASE = API_URL.rstrip("/")
HEADERS_READ  = {"Authorization": f"Bearer {ANON_KEY}", "Accept": "application/json"}
HEADERS_WRITE = {"Authorization": f"Bearer {ADMIN_KEY}", "Content-Type": "application/json"}

print("=" * 60)
print("VOLCAR PREDICCIONES A INSFORGE")
print("=" * 60)

# =====================================================================
#  1. CARGAR OCUPACION REAL
# =====================================================================

print("\n[1/5] Leyendo ocupacion_real...", end=" ")
resp = requests.get(
    f"{BASE}/api/database/records/ocupacion_real",
    headers=HEADERS_READ, timeout=15
)
resp.raise_for_status()
raw = resp.json()
records = raw["records"] if isinstance(raw, dict) and "records" in raw else raw
print(f"{len(records)} filas.")

df = pd.DataFrame(records)
df["fecha"] = pd.to_datetime(df["fecha"])
df = df.sort_values("fecha").reset_index(drop=True)
serie = df.set_index("fecha")["porcentaje_ocupacion"].astype(float)

print(f"  Rango: {serie.index.min().date()} -> {serie.index.max().date()}")
print(f"  Total: {len(serie)} dias")
print(f"  Media: {serie.mean():.1f}%")

# =====================================================================
#  2. ENTRENAR SARIMA
# =====================================================================

print("\n[2/5] Entrenando SARIMA(2,1,1)(1,0,2,7)...", end=" ", flush=True)

from statsmodels.tsa.statespace.sarimax import SARIMAX

modelo = SARIMAX(
    serie,
    order=SARIMA_ORDER,
    seasonal_order=SARIMA_SEASONAL,
    enforce_stationarity=False,
    enforce_invertibility=False,
)
modelo_fit = modelo.fit(disp=False, maxiter=200)
print("[OK]")

# =====================================================================
#  3. PREDECIR 30 DIAS CON 3 ESCENARIOS
# =====================================================================

print(f"\n[3/5] Prediciendo {DIAS_PREDICCION} dias...", end=" ", flush=True)

pred = modelo_fit.get_forecast(steps=DIAS_PREDICCION)
pred_df = pred.summary_frame(alpha=0.05)

ultima_fecha = serie.index.max()
fechas_pred = [ultima_fecha + timedelta(days=i + 1) for i in range(DIAS_PREDICCION)]

pred_central   = np.clip(pred_df["mean"].values, 0, 100)
pred_inferior  = np.clip(pred_df["mean_ci_lower"].values, 0, 100)
pred_superior  = np.clip(pred_df["mean_ci_upper"].values, 0, 100)

print(f"{DIAS_PREDICCION} dias generados")
print(f"  Rango: {fechas_pred[0].date()} -> {fechas_pred[-1].date()}")
print(f"  Media realista: {pred_central.mean():.1f}%")

# =====================================================================
#  4. UPSERT EN TABLA PREDICCIONES VIA REST
# =====================================================================

print("\n[4/5] Insertando predicciones en Insforge (upsert)...")

# Construir array de registros (REST API requiere array aunque sea 1)
registros = []
for i in range(DIAS_PREDICCION):
    registros.append({
        "fecha": str(fechas_pred[i].date()),
        "ocupacion_pesimista": round(float(pred_inferior[i]), 1),
        "ocupacion_realista": round(float(pred_central[i]), 1),
        "ocupacion_optimista": round(float(pred_superior[i]), 1),
        "modelo": "SARIMA",
    })

# Upsert via POST con resolution=merge-duplicates
# La columna "fecha" tiene UNIQUE, asi que Insforge detecta el conflicto
# y hace UPDATE en lugar de INSERT para fechas que ya existen
upsert_url = f"{BASE}/api/database/records/predicciones"
upsert_headers = {
    **HEADERS_WRITE,
    "Prefer": "resolution=merge-duplicates,return=representation",
}

resp = requests.post(upsert_url, headers=upsert_headers, json=registros, timeout=30)

if resp.status_code in (200, 201):
    resultado = resp.json()
    insertados = len(resultado) if isinstance(resultado, list) else 1
    print(f"  {insertados} registros insertados/actualizados correctamente")
    print(f"  Rango: {registros[0]['fecha']} -> {registros[-1]['fecha']}")
else:
    print(f"  [FAIL] Status {resp.status_code}: {resp.text[:200]}")
    sys.exit(1)

# =====================================================================
#  5. VERIFICAR DATOS INSERTADOS
# =====================================================================

print("\n[5/5] Verificando datos en Insforge...")

resp_check = requests.get(
    f"{BASE}/api/database/records/predicciones?order=fecha.asc",
    headers=HEADERS_READ, timeout=15
)
resp_check.raise_for_status()
raw_check = resp_check.json()
check_records = raw_check["records"] if isinstance(raw_check, dict) and "records" in raw_check else raw_check

total = len(check_records)
print(f"\n  Total filas en tabla predicciones: {total}")

print(f"\n  Primeras 3 filas (ordenadas por fecha):")
print(f"  {'Fecha':<14} {'Pesimista':<12} {'Realista':<12} {'Optimista':<12} {'Modelo':<10}")
print(f"  {'-'*14} {'-'*12} {'-'*12} {'-'*12} {'-'*10}")
for row in check_records[:3]:
    print(f"  {row['fecha']:<14} {row['ocupacion_pesimista']:<12} "
          f"{row['ocupacion_realista']:<12} {row['ocupacion_optimista']:<12} "
          f"{row['modelo']:<10}")

print(f"\n  Ultima fila:")
ultima = check_records[-1]
print(f"  {ultima['fecha']:<14} {ultima['ocupacion_pesimista']:<12} "
      f"{ultima['ocupacion_realista']:<12} {ultima['ocupacion_optimista']:<12} "
      f"{ultima['modelo']:<10}")

print(f"\n  generada_en (ultima): {ultima.get('generada_en', 'N/A')}")

print(f"\n{'=' * 60}")
print("[OK] Predicciones volcadas a Insforge correctamente.")
print(f"     Tabla: predicciones ({total} filas)")
print(f"     Rango: {check_records[0]['fecha']} -> {check_records[-1]['fecha']}")
print(f"{'=' * 60}")

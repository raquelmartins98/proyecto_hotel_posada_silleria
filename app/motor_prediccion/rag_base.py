"""
rag_base.py — Bloque 7.1: Base de conocimiento RAG para el asistente IA
del hotel. Construye en memoria toda la informacion disponible:
  - Serie historica de ocupacion (365 dias)
  - Prediccion SARIMA 30 dias (3 escenarios)
  - Eventos locales
  - Precios de la competencia
  - Costes mensuales

Exporta build_knowledge_base() para que rag_buscador.py la reutilice.
"""
import sys
import os
import warnings
from pathlib import Path
from datetime import timedelta

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


def fetch_table(base_url: str, headers: dict, nombre: str) -> list[dict]:
    """Lee una tabla completa de Insforge via REST."""
    url = f"{base_url}/api/database/records/{nombre}"
    resp = requests.get(url, headers=headers, timeout=15)
    resp.raise_for_status()
    raw = resp.json()
    return raw["records"] if isinstance(raw, dict) and "records" in raw else raw


def build_knowledge_base(verbose: bool = True) -> dict:
    """
    Construye y devuelve la base de conocimiento completa.
    - verbose=True: imprime el progreso (para ejecucion directa)
    - verbose=False: silencioso (para importacion desde rag_buscador.py)
    """
    # ── Conectar a Insforge ────────────────────────────
    load_dotenv(ENV_PATH)
    api_url = os.getenv("VITE_INSFORGE_URL")
    anon_key = os.getenv("VITE_INSFORGE_ANON_KEY")

    if not api_url or not anon_key:
        print("[FAIL] Faltan credenciales en frontend/.env")
        sys.exit(1)

    base = api_url.rstrip("/")
    headers = {"Authorization": f"Bearer {anon_key}", "Accept": "application/json"}

    if verbose:
        print("=" * 60)
        print("BLOQUE 7.1: BASE DE CONOCIMIENTO RAG")
        print("=" * 60)

    # ── 2a. ocupacion_real ─────────────────────────────
    if verbose:
        print("\n[1/5] Cargando ocupacion historica...", end=" ")
    records_ocup = fetch_table(base, headers, "ocupacion_real")
    if verbose:
        print(f"{len(records_ocup)} filas.")

    df_ocup = pd.DataFrame(records_ocup)
    df_ocup["fecha"] = pd.to_datetime(df_ocup["fecha"])
    df_ocup = df_ocup.sort_values("fecha").reset_index(drop=True)
    serie_ocup = df_ocup.set_index("fecha")["porcentaje_ocupacion"].astype(float)

    if verbose:
        print(f"  Rango: {serie_ocup.index.min().date()} -> {serie_ocup.index.max().date()}")
        print(f"  Media historica: {serie_ocup.mean():.1f}%")

    # ── 2b. eventos_locales ────────────────────────────
    if verbose:
        print("\n[2/5] Cargando eventos locales...", end=" ")
    records_eventos = fetch_table(base, headers, "eventos_locales")
    if verbose:
        print(f"{len(records_eventos)} eventos.")

    df_eventos = pd.DataFrame(records_eventos)
    if not df_eventos.empty:
        df_eventos["fecha_inicio"] = pd.to_datetime(df_eventos["fecha_inicio"])
        df_eventos["fecha_fin"] = pd.to_datetime(df_eventos["fecha_fin"])

    # ── 2c. precios_competencia ────────────────────────
    if verbose:
        print("\n[3/5] Cargando precios de competencia...", end=" ")
    records_comp = fetch_table(base, headers, "precios_competencia")
    if verbose:
        print(f"{len(records_comp)} registros.")

    df_comp = pd.DataFrame(records_comp)
    if not df_comp.empty:
        df_comp["fecha"] = pd.to_datetime(df_comp["fecha"])

    # ── 2d. costes_mensuales ───────────────────────────
    if verbose:
        print("\n[4/5] Cargando costes mensuales...", end=" ")
    records_costes = fetch_table(base, headers, "costes_mensuales")
    if verbose:
        print(f"{len(records_costes)} meses.")

    df_costes = pd.DataFrame(records_costes)

    # ── 3. Generar prediccion SARIMA ───────────────────
    if verbose:
        print(f"\n[5/5] Generando prediccion SARIMA {DIAS_PREDICCION} dias...")

    from statsmodels.tsa.statespace.sarimax import SARIMAX

    modelo = SARIMAX(
        serie_ocup,
        order=SARIMA_ORDER,
        seasonal_order=SARIMA_SEASONAL,
        enforce_stationarity=False,
        enforce_invertibility=False,
    )
    modelo_fit = modelo.fit(disp=False, maxiter=200)

    pred = modelo_fit.get_forecast(steps=DIAS_PREDICCION)
    pred_df = pred.summary_frame(alpha=0.05)

    ultima_fecha = serie_ocup.index.max()
    fechas_pred = [ultima_fecha + timedelta(days=i + 1) for i in range(DIAS_PREDICCION)]

    pred_central   = np.clip(pred_df["mean"].values, 0, 100)
    pred_inferior  = np.clip(pred_df["mean_ci_lower"].values, 0, 100)
    pred_superior  = np.clip(pred_df["mean_ci_upper"].values, 0, 100)

    if verbose:
        print(f"  Prediccion generada: {DIAS_PREDICCION} dias")
        print(f"  Media realista: {pred_central.mean():.1f}%")
        print(f"  Rango: {fechas_pred[0].date()} -> {fechas_pred[-1].date()}")

    # ── 4. Construir diccionario ───────────────────────
    conocimiento = {
        "hotel": {
            "nombre": "Hotel Boutique Posada de la Silleria",
            "ubicacion": "Toledo, junto a la catedral",
            "habitaciones": 19,
            "tipos_habitacion": [
                "Doble", "Doble Superior", "Suite Junior",
                "Suite", "Suite Presidencial",
            ],
        },
        "ocupacion_historica": {
            "dias": len(serie_ocup),
            "rango_inicio": str(serie_ocup.index.min().date()),
            "rango_fin": str(serie_ocup.index.max().date()),
            "media": round(float(serie_ocup.mean()), 1),
            "minimo": round(float(serie_ocup.min()), 1),
            "maximo": round(float(serie_ocup.max()), 1),
            "desviacion": round(float(serie_ocup.std()), 1),
            "serie_diaria": {
                str(k.date()): round(float(v), 1)
                for k, v in serie_ocup.items()
            },
        },
        "prediccion": {
            "modelo": f"SARIMA{SARIMA_ORDER}{SARIMA_SEASONAL}",
            "dias": DIAS_PREDICCION,
            "rango_inicio": str(fechas_pred[0].date()),
            "rango_fin": str(fechas_pred[-1].date()),
            "media_pesimista": round(float(pred_inferior.mean()), 1),
            "media_realista": round(float(pred_central.mean()), 1),
            "media_optimista": round(float(pred_superior.mean()), 1),
            "diario": [
                {
                    "fecha": str(row.date()),
                    "pesimista": round(float(pred_inferior[i]), 1),
                    "realista": round(float(pred_central[i]), 1),
                    "optimista": round(float(pred_superior[i]), 1),
                }
                for i, row in enumerate(fechas_pred)
            ],
        },
        "eventos": {
            "total": len(df_eventos),
            "lista": [
                {
                    "nombre": row["nombre"],
                    "fecha_inicio": str(row["fecha_inicio"].date()),
                    "fecha_fin": str(row["fecha_fin"].date()),
                    "tipo": row["tipo"],
                    "impacto": row["impacto_estimado"],
                    "repite_anual": row["es_fijo_anual"],
                }
                for _, row in df_eventos.iterrows()
            ],
        },
        "competencia": {
            "total": len(df_comp),
            "hoteles": sorted(df_comp["hotel"].unique().tolist()) if not df_comp.empty else [],
            "precios": [
                {
                    "hotel": row["hotel"],
                    "tipo_habitacion": row["tipo_habitacion"],
                    "fecha": str(row["fecha"].date()),
                    "precio": row["precio"],
                    "fuente": row["fuente"],
                }
                for _, row in df_comp.iterrows()
            ],
        },
        "costes": {
            "total_meses": len(df_costes),
            "media_mensual": round(float(df_costes["total"].mean()), 2) if not df_costes.empty else 0,
            "total_anual": round(float(df_costes["total"].sum()), 2) if not df_costes.empty else 0,
            "por_mes": [
                {
                    "mes": int(row["mes"]),
                    "anio": int(row["anio"]),
                    "operativos": row["costes_operativos"],
                    "mantenimiento": row["mantenimiento"],
                    "personal": row["personal"],
                    "suministros": row["suministros"],
                    "otros": row["otros"],
                    "total": row["total"],
                }
                for _, row in df_costes.iterrows()
            ],
        },
    }

    if verbose:
        print(f"\n[OK] Base de conocimiento construida: {len(conocimiento)} secciones, "
              f"{DIAS_PREDICCION} dias prediccion, "
              f"{len(records_eventos)} eventos, "
              f"{len(records_comp)} precios, "
              f"{len(records_costes)} meses de costes.")

    return conocimiento


# ── Ejecucion directa ────────────────────────────────────
if __name__ == "__main__":
    kb = build_knowledge_base(verbose=True)

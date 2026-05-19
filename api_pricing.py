"""
api_pricing.py — API REST para el Motor de Pricing Dinamico
=============================================================
Endpoints:
  GET  /health          -> Estado del servidor y conexion a InsForge
  GET  /habitaciones    -> Lista de tipos de habitacion con tarifas base
  GET  /temporadas      -> Lista de temporadas con multiplicadores
  POST /calcular-precio -> Calcula precio sugerido para una reserva

Uso: uvicorn api_pricing:app --reload --port 8000
"""

import os
import requests
from datetime import date
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Importar el motor de pricing
from pricing_engine import (
    calcular_precio_sugerido,
    PrecioResultado,
    FactorBreakdown,
    _query,
    _cache,
)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
API_KEY = "ik_371927c198260f2bf08eb13ba70a8d42"
BASE_URL = "https://v63axieg.us-east.insforge.app"

app = FastAPI(
    title="Motor de Pricing Dinamico - Posada de la Silleria",
    description="API REST para calcular precios de habitaciones con factores de ajuste",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class FactorBreakdownOut(BaseModel):
    factor: str
    valor_aplicado: float
    descripcion: str
    fuente: str


class PrecioResponse(BaseModel):
    precio_sugerido: float
    precio_minimo: float
    precio_maximo: float
    precio_base: float
    nivel_confianza: str
    desglose: List[FactorBreakdownOut]


class CalcularPrecioRequest(BaseModel):
    fecha: str = Field(..., description="Fecha de entrada (YYYY-MM-DD)", examples=["2026-06-06"])
    tipo_habitacion: str = Field(..., description="Nombre exacto del tipo de habitacion",
                                  examples=["Suite Castellana (vista Patio)"])
    num_noches: int = Field(1, ge=1, le=30, description="Numero de noches")
    num_huespedes: int = Field(1, ge=1, le=6, description="Numero de huespedes")
    canal: str = Field("Booking", description="Canal de reserva",
                        examples=["Booking", "Directo", "Expedia"])


class HabitacionOut(BaseModel):
    tipo: str
    tarifa_base: float
    capacidad: int
    descripcion: str


class TemporadaOut(BaseModel):
    nombre: str
    fecha_inicio: str
    fecha_fin: str
    multiplicador_precio: float


class EventoOut(BaseModel):
    nombre: str
    tipo: str
    impacto_estimado: str
    fecha_inicio: str
    fecha_fin: str


class HealthResponse(BaseModel):
    status: str
    api_insforge: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health", response_model=HealthResponse, tags=["Sistema"])
async def health_check():
    """Verifica que el servidor y la conexion a InsForge funcionan."""
    try:
        resp = requests.get(f"{BASE_URL}/api/health", timeout=5)
        resp.raise_for_status()
        insforge_status = "ok"
    except Exception as e:
        insforge_status = f"error: {e}"

    return HealthResponse(
        status="ok",
        api_insforge=insforge_status,
    )


@app.get("/habitaciones", response_model=List[HabitacionOut], tags=["Referencia"])
async def listar_habitaciones():
    """Lista todos los tipos de habitacion con sus tarifas base."""
    rows = _query("SELECT tipo, tarifa_base, capacidad, descripcion FROM public.habitaciones ORDER BY tarifa_base;")
    return [
        HabitacionOut(
            tipo=r["tipo"],
            tarifa_base=float(r["tarifa_base"]),
            capacidad=int(r["capacidad"]),
            descripcion=r.get("descripcion", ""),
        )
        for r in rows
    ]


@app.get("/temporadas", response_model=List[TemporadaOut], tags=["Referencia"])
async def listar_temporadas():
    """Lista todas las temporadas con sus multiplicadores."""
    rows = _query(
        """SELECT nombre, fecha_inicio, fecha_fin, multiplicador_precio
           FROM public.temporadas ORDER BY fecha_inicio;"""
    )
    return [
        TemporadaOut(
            nombre=r["nombre"],
            fecha_inicio=str(r["fecha_inicio"]),
            fecha_fin=str(r["fecha_fin"]),
            multiplicador_precio=float(r["multiplicador_precio"]),
        )
        for r in rows
    ]


@app.get("/eventos", response_model=List[EventoOut], tags=["Referencia"])
async def listar_eventos(fecha: Optional[str] = Query(None, description="Filtrar por fecha (YYYY-MM-DD)")):
    """Lista eventos locales. Opcionalmente filtrar por fecha."""
    if fecha:
        rows = _query(
            """SELECT nombre, tipo, impacto_estimado, fecha_inicio, fecha_fin
               FROM public.eventos_locales
               WHERE $1::date BETWEEN fecha_inicio AND fecha_fin
               ORDER BY fecha_inicio;""",
            [fecha],
        )
    else:
        rows = _query(
            """SELECT nombre, tipo, impacto_estimado, fecha_inicio, fecha_fin
               FROM public.eventos_locales ORDER BY fecha_inicio;"""
        )
    return [
        EventoOut(
            nombre=r["nombre"],
            tipo=r["tipo"],
            impacto_estimado=r["impacto_estimado"],
            fecha_inicio=str(r["fecha_inicio"]),
            fecha_fin=str(r["fecha_fin"]),
        )
        for r in rows
    ]


@app.post("/calcular-precio", response_model=PrecioResponse, tags=["Pricing"])
async def calcular_precio(req: CalcularPrecioRequest):
    """Calcula el precio sugerido para una reserva aplicando todos los factores."""
    try:
        resultado = calcular_precio_sugerido(
            fecha=req.fecha,
            tipo_habitacion=req.tipo_habitacion,
            num_noches=req.num_noches,
            num_huespedes=req.num_huespedes,
            canal=req.canal,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {e}")

    return PrecioResponse(
        precio_sugerido=resultado.precio_sugerido,
        precio_minimo=resultado.precio_minimo,
        precio_maximo=resultado.precio_maximo,
        precio_base=resultado.precio_base,
        nivel_confianza=resultado.nivel_confianza,
        desglose=[
            FactorBreakdownOut(
                factor=fb.factor,
                valor_aplicado=fb.valor_aplicado,
                descripcion=fb.descripcion,
                fuente=fb.fuente,
            )
            for fb in resultado.desglose
        ],
    )


@app.get("/calcular-precio", response_model=PrecioResponse, tags=["Pricing"])
async def calcular_precio_get(
    fecha: str = Query(..., description="Fecha de entrada (YYYY-MM-DD)", examples=["2026-06-06"]),
    tipo_habitacion: str = Query(..., description="Tipo de habitacion",
                                   examples=["Suite Castellana (vista Patio)"]),
    num_noches: int = Query(1, ge=1, le=30, description="Numero de noches"),
    num_huespedes: int = Query(1, ge=1, le=6, description="Numero de huespedes"),
    canal: str = Query("Booking", description="Canal de reserva"),
):
    """Version GET de calcular-precio (para pruebas desde navegador)."""
    return await calcular_precio(CalcularPrecioRequest(
        fecha=fecha,
        tipo_habitacion=tipo_habitacion,
        num_noches=num_noches,
        num_huespedes=num_huespedes,
        canal=canal,
    ))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

"""
Motor de Pricing Dinmico  Hotel Boutique Posada de la Sillera (Toledo)
======================================================================
Modelo hbrido base (reglas + regresin lineal simple) 100% explicable.
Cada factor de ajuste es una funcin independiente y testeable.

Uso:
    from pricing_engine import PricingEngine
    engine = PricingEngine()
    resultado = engine.calcular_precio_sugerido(
        fecha="2026-06-06",
        tipo_habitacion="Suite Castellana (vista Patio)",
        num_noches=2,
        num_huespedes=2,
        canal="Booking"
    )
"""

import requests
import json
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field, asdict


# 
# CONFIGURACIN
# 
API_KEY = "ik_371927c198260f2bf08eb13ba70a8d42"
BASE_URL = "https://v63axieg.us-east.insforge.app"
HEADERS = {
    "x-api-key": API_KEY,
    "Content-Type": "application/json",
}

# Cache para datos que no cambian frecuentemente
_cache: Dict[str, Any] = {}


# 
# ESTRUCTURA DEL RESULTADO
# 

@dataclass
class FactorBreakdown:
    """Desglose de un factor individual"""
    factor: str
    valor_aplicado: float
    descripcion: str
    fuente: str


@dataclass
class PrecioResultado:
    """Resultado completo del clculo de precio"""
    precio_sugerido: float          # EUR/noche final
    precio_minimo: float            # EUR/noche suelo rentabilidad
    precio_maximo: float            # EUR/noche techo psicolgico
    precio_base: float              # EUR/noche tarifa base
    desglose: List[FactorBreakdown]
    nivel_confianza: str            # alto / medio / bajo


# 
# CAPA DE ACCESO A DATOS (InsForge REST API)
# 

def _query(sql: str, params: Optional[list] = None) -> list:
    """Ejecuta SQL en InsForge va REST API."""
    resp = requests.post(
        f"{BASE_URL}/api/database/advance/rawsql",
        headers=HEADERS,
        json={"query": sql, "params": params or []},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json().get("rows", [])


def _get_precio_base(tipo_habitacion: str) -> float:
    """Obtiene la tarifa base de un tipo de habitacin."""
    key = f"tarifa_base_{tipo_habitacion}"
    if key in _cache:
        return _cache[key]
    rows = _query(
        "SELECT tarifa_base FROM public.habitaciones WHERE tipo = $1 LIMIT 1;",
        [tipo_habitacion],
    )
    if not rows:
        raise ValueError(f"Tipo de habitacin '{tipo_habitacion}' no encontrado")
    val = float(rows[0]["tarifa_base"])
    _cache[key] = val
    return val


def _get_mult_temporada(fecha: date) -> Tuple[float, str]:
    """Busca el multiplicador de temporada para la fecha."""
    f = fecha.isoformat()
    rows = _query(
        """SELECT nombre, multiplicador_precio
           FROM public.temporadas
           WHERE $1::date BETWEEN fecha_inicio AND fecha_fin
           LIMIT 1;""",
        [f],
    )
    if rows:
        return float(rows[0]["multiplicador_precio"]), rows[0]["nombre"]
    return 1.0, "Temporada no definida (multiplicador 1.0 por defecto)"


def _get_evento_local(fecha: date) -> List[dict]:
    """Busca eventos locales que cubran la fecha."""
    f = fecha.isoformat()
    rows = _query(
        """SELECT nombre, tipo, impacto_estimado
           FROM public.eventos_locales
           WHERE $1::date BETWEEN fecha_inicio AND fecha_fin
           ORDER BY
             CASE impacto_estimado
               WHEN 'critico' THEN 1
               WHEN 'alto' THEN 2
               WHEN 'medio' THEN 3
               WHEN 'bajo' THEN 4
               ELSE 5
             END
           LIMIT 1;""",
        [f],
    )
    return rows


def _get_ocupacion_historica(fecha: date, dias_ventana: int = 7) -> float:
    """Ocupacin media en la misma fecha  ventana del ao anterior."""
    f = fecha.isoformat()
    ventana_anterior = fecha - timedelta(days=365)
    rows = _query(
        """SELECT ROUND(AVG(porcentaje_ocupacion), 1) as ocup_media
           FROM public.ocupacion_real
           WHERE fecha BETWEEN $1::date - $2::integer
             AND $1::date + $2::integer;""",
        [ventana_anterior.isoformat(), dias_ventana],
    )
    if rows and rows[0]["ocup_media"] is not None:
        return float(rows[0]["ocup_media"])
    # Fallback: si no hay ao anterior, usar datos del mismo periodo
    rows2 = _query(
        """SELECT ROUND(AVG(porcentaje_ocupacion), 1) as ocup_media
           FROM public.ocupacion_real
           WHERE EXTRACT(MONTH FROM fecha) = $1::integer
             AND EXTRACT(DOW FROM fecha) = $2::integer;""",
        [fecha.month, fecha.weekday()],
    )
    if rows2 and rows2[0]["ocup_media"] is not None:
        return float(rows2[0]["ocup_media"])
    return -1  # Sin datos


def _get_precios_competencia(fecha: date, dias_ventana: int = 3) -> List[dict]:
    """Precios de competencia alrededor de la fecha."""
    f = fecha.isoformat()
    return _query(
        """SELECT hotel, tipo_habitacion, precio
           FROM public.precios_competencia
           WHERE fecha BETWEEN $1::date - $2::integer
             AND $1::date + $2::integer
           ORDER BY fecha;""",
        [f, dias_ventana],
    )


def _get_tiempo(fecha: date) -> dict:
    """Datos meteorolgicos para la fecha."""
    f = fecha.isoformat()
    rows = _query(
        """SELECT temp_max, temp_min, precipitacion
           FROM public.tiempo_toledo
           WHERE fecha = $1::date
           LIMIT 1;""",
        [f],
    )
    return rows[0] if rows else {}


def _get_coste_por_habitacion(mes: int, anio: int) -> float:
    """Coste medio por habitacin-noche para el mes."""
    # Calcular das del mes
    import calendar
    dias_mes = calendar.monthrange(anio, mes)[1]
    
    rows = _query(
        """SELECT total FROM public.costes_mensuales
           WHERE mes = $1 AND anio = $2
           LIMIT 1;""",
        [mes, anio],
    )
    if rows:
        total_mes = float(rows[0]["total"])
        return round(total_mes / (19 * dias_mes), 2)
    return 0


# 
# FUNCIONES DE AJUSTE (cada una es un factor)
# 

def ajuste_precio_base(tipo_habitacion: str) -> Tuple[float, FactorBreakdown]:
    """Factor 1: Precio base desde la tabla habitaciones."""
    base = _get_precio_base(tipo_habitacion)
    return base, FactorBreakdown(
        factor="precio_base",
        valor_aplicado=base,
        descripcion=f"Tarifa base para {tipo_habitacion}",
        fuente="public.habitaciones.tarifa_base",
    )


def ajuste_temporada(fecha: date) -> Tuple[float, FactorBreakdown]:
    """Factor 2: Multiplicador por temporada."""
    mult, nombre_temp = _get_mult_temporada(fecha)
    return mult, FactorBreakdown(
        factor="multiplicador_temporada",
        valor_aplicado=mult,
        descripcion=f"Temporada: {nombre_temp} (x{mult})",
        fuente="public.temporadas.multiplicador_precio",
    )


def ajuste_evento_local(
    fecha: date, tipo_habitacion: str
) -> Tuple[float, FactorBreakdown]:
    """Factor 3: Ajuste por evento local."""
    eventos = _get_evento_local(fecha)
    if not eventos:
        return 1.0, FactorBreakdown(
            factor="evento_local",
            valor_aplicado=1.0,
            descripcion="Sin evento local",
            fuente="",
        )

    ev = eventos[0]
    impacto = ev.get("impacto_estimado", "").lower()
    nombre_ev = ev.get("nombre", "")
    tipo_ev = ev.get("tipo", "")

    if impacto == "critico":
        mult = 1.25
    elif impacto == "alto":
        mult = 1.25
    elif impacto == "medio":
        mult = 1.12
    elif impacto == "bajo":
        mult = 1.05
    else:
        mult = 1.0

    desc = f"Evento '{nombre_ev}' ({tipo_ev}, impacto {impacto}): +{round((mult-1)*100)}%"

    # Extra especial: Corpus + habitacin con vista a la calle
    extra_corpus = 1.0
    if "corpus" in nombre_ev.lower():
        habitaciones_vista = [
            "Suite Castellana (vista Patio)",
            "Doble Superior",
        ]
        if tipo_habitacion in habitaciones_vista:
            extra_corpus = 1.15
            desc += f" + vista a la calle (procesin Corpus): +15%"

    return mult * extra_corpus, FactorBreakdown(
        factor="evento_local",
        valor_aplicado=round(mult * extra_corpus, 4),
        descripcion=desc,
        fuente="public.eventos_locales",
    )


def ajuste_demanda_historica(fecha: date) -> Tuple[float, FactorBreakdown]:
    """Factor 4: Ajuste por demanda histrica en el mismo periodo."""
    ocup_media = _get_ocupacion_historica(fecha)

    if ocup_media < 0:
        # Sin datos histricos
        return 0.0, FactorBreakdown(
            factor="demanda_historica",
            valor_aplicado=0.0,
            descripcion="Sin datos de ocupacin histrica  ajuste neutral",
            fuente="",
        )

    if ocup_media > 85:
        mult = 1.10
        nivel = "alta"
    elif ocup_media >= 70:
        mult = 1.05
        nivel = "media-alta"
    elif ocup_media >= 50:
        mult = 1.0
        nivel = "media"
    elif ocup_media >= 30:
        mult = 0.92
        nivel = "baja"
    else:
        mult = 0.85
        nivel = "muy baja"

    return mult, FactorBreakdown(
        factor="demanda_historica",
        valor_aplicado=mult,
        descripcion=(
            f"Ocupacin histrica: {ocup_media}% ({nivel})  "
            f"{'' if mult >= 1 else ''}{round((mult-1)*100):+}%"
        ),
        fuente="public.ocupacion_real (7 das ao anterior)",
    )


def ajuste_dia_semana(fecha: date) -> Tuple[float, FactorBreakdown]:
    """Factor 5: Ajuste por da de la semana."""
    dow = fecha.weekday()  # 0=lunes ... 6=domingo
    nombres = ["lunes", "martes", "mircoles", "jueves", "viernes", "sbado", "domingo"]

    if dow == 4:  # viernes
        mult = 1.12
    elif dow == 5:  # sbado
        mult = 1.12
    elif dow == 6:  # domingo
        mult = 1.03
    elif dow == 3:  # jueves
        mult = 1.03
    else:  # lunes a mircoles
        mult = 0.95

    return mult, FactorBreakdown(
        factor="dia_semana",
        valor_aplicado=mult,
        descripcion=f"Da: {nombres[dow]}  {'' if mult >= 1 else ''}{round((mult-1)*100):+}%",
        fuente="Regla de negocio (patrn semanal)",
    )


def ajuste_competencia(
    fecha: date, precio_actual: float
) -> Tuple[float, FactorBreakdown, str]:
    """Factor 6: Ajuste por comparativa de competencia.

    Returns:
        (multiplicador, breakdown, confianza_impactada)
    """
    competencia = _get_precios_competencia(fecha)
    if not competencia:
        return 1.0, FactorBreakdown(
            factor="competencia",
            valor_aplicado=1.0,
            descripcion="Sin datos de competencia para la fecha",
            fuente="",
        ), "medio"

    precios = [float(c["precio"]) for c in competencia]
    media_mercado = sum(precios) / len(precios)

    diff_pct = (precio_actual - media_mercado) / media_mercado * 100

    if diff_pct > 15:
        # Estamos >15% por encima  bajar a +10%
        precio_ajustado = media_mercado * 1.10
        mult = precio_ajustado / precio_actual
        desc = (
            f"Precio actual {diff_pct:.0f}% sobre media mercado ({media_mercado:.0f}EUR). "
            f"Ajustado a +10% ({precio_ajustado:.0f}EUR)."
        )
    elif diff_pct < -20:
        # Estamos >20% por debajo  subir a -10%
        precio_ajustado = media_mercado * 0.90
        mult = precio_ajustado / precio_actual
        desc = (
            f"Precio actual {abs(diff_pct):.0f}% bajo media mercado ({media_mercado:.0f}EUR). "
            f"Ajustado a -10% ({precio_ajustado:.0f}EUR)."
        )
    else:
        mult = 1.0
        desc = f"Diferencia del {diff_pct:.0f}% frente a media mercado ({media_mercado:.0f}EUR)  dentro del rango"

    return mult, FactorBreakdown(
        factor="competencia",
        valor_aplicado=round(mult, 4),
        descripcion=desc,
        fuente=f"public.precios_competencia ({len(competencia)} registros)",
    ), "alto"


def ajuste_tiempo(fecha: date) -> Tuple[float, FactorBreakdown]:
    """Factor 7: Ajuste por condiciones meteorolgicas."""
    tiempo = _get_tiempo(fecha)
    if not tiempo:
        return 1.0, FactorBreakdown(
            factor="tiempo",
            valor_aplicado=1.0,
            descripcion="Sin datos meteorolgicos para la fecha",
            fuente="",
        )

    temp_max = float(tiempo.get("temp_max", 20))
    precipitacion = float(tiempo.get("precipitacion", 0))

    if precipitacion > 5 or temp_max < 5 or temp_max > 38:
        mult = 0.95
        razon = []
        if precipitacion > 5:
            razon.append(f"lluvia {precipitacion}mm")
        if temp_max < 5:
            razon.append(f"fro {temp_max} gradosC")
        if temp_max > 38:
            razon.append(f"calor extremo {temp_max} gradosC")
        desc = f"Mal tiempo ({', '.join(razon)}): -5%"
    elif 18 <= temp_max <= 28 and precipitacion == 0:
        mult = 1.03
        desc = f"Tiempo ideal ({temp_max} gradosC, sin lluvia): +3%"
    else:
        mult = 1.0
        desc = f"Tiempo neutro ({temp_max} gradosC, {precipitacion}mm lluvia): 0%"

    return mult, FactorBreakdown(
        factor="tiempo",
        valor_aplicado=mult,
        descripcion=desc,
        fuente="public.tiempo_toledo",
    )


def ajuste_estancia_larga(num_noches: int) -> Tuple[float, FactorBreakdown]:
    """Factor 8: Descuento por estancia larga."""
    if num_noches >= 5:
        mult = 0.90
        desc = f"{num_noches} noches  -10% (estancia larga)"
    elif num_noches >= 3:
        mult = 0.95
        desc = f"{num_noches} noches  -5% (estancia media)"
    else:
        mult = 1.0
        desc = f"{num_noches} noches  0%"

    return mult, FactorBreakdown(
        factor="descuento_estancia_larga",
        valor_aplicado=mult,
        descripcion=desc,
        fuente="Regla de negocio",
    )


def ajuste_canal(canal: str) -> Tuple[float, FactorBreakdown]:
    """Factor 9: Ajuste por canal de reserva."""
    canal_lower = canal.lower().strip()
    if canal_lower in ("booking", "expedia", "ota otro"):
        mult = 1.0
        desc = f"Canal {canal}: precio bruto (comisin del canal aparte)"
    elif canal_lower in ("directo", "web directa", "telfono", "email"):
        mult = 0.92
        desc = f"Canal {canal}: -8% descuento reserva directa"
    else:
        mult = 1.0
        desc = f"Canal {canal}: precio bruto"

    return mult, FactorBreakdown(
        factor="ajuste_canal",
        valor_aplicado=mult,
        descripcion=desc,
        fuente="Regla de negocio",
    )


# 
# FUNCIN PRINCIPAL
# 

def calcular_precio_sugerido(
    fecha: str,
    tipo_habitacion: str,
    num_noches: int = 1,
    num_huespedes: int = 1,
    canal: str = "Booking",
) -> PrecioResultado:
    """
    Calcula el precio sugerido para una reserva aplicando todos los factores.

    Args:
        fecha: Fecha de entrada (formato YYYY-MM-DD)
        tipo_habitacion: Nombre exacto del tipo de habitacin
        num_noches: Nmero de noches de estancia
        num_huespedes: Nmero de huspedes
        canal: Canal de reserva

    Returns:
        PrecioResultado con precio sugerido, mnimo, mximo y desglose
    """
    fecha_dt = datetime.strptime(fecha, "%Y-%m-%d").date()

    desglose: List[FactorBreakdown] = []
    nivel_confianza = "alto"

    #  Factor 1: Precio Base 
    precio_base, fb1 = ajuste_precio_base(tipo_habitacion)
    desglose.append(fb1)
    precio_acumulado = precio_base

    #  Factor 2: Temporada 
    mult_temp, fb2 = ajuste_temporada(fecha_dt)
    desglose.append(fb2)
    precio_acumulado *= mult_temp

    #  Factor 3: Evento Local 
    mult_evento, fb3 = ajuste_evento_local(fecha_dt, tipo_habitacion)
    desglose.append(fb3)
    precio_acumulado *= mult_evento

    #  Factor 4: Demanda Histrica 
    mult_demanda, fb4 = ajuste_demanda_historica(fecha_dt)
    desglose.append(fb4)
    if mult_demanda == 0:
        nivel_confianza = "bajo"  # Sin datos histricos
    else:
        precio_acumulado *= mult_demanda

    #  Factor 5: Da de Semana 
    mult_dia, fb5 = ajuste_dia_semana(fecha_dt)
    desglose.append(fb5)
    precio_acumulado *= mult_dia

    #  Factor 6: Competencia (se aplica sobre el precio acumulado) 
    mult_comp, fb6, conf_comp = ajuste_competencia(fecha_dt, precio_acumulado)
    desglose.append(fb6)
    if conf_comp == "medio" and nivel_confianza != "bajo":
        nivel_confianza = "medio"
    precio_acumulado *= mult_comp

    #  Factor 7: Tiempo 
    mult_tiempo, fb7 = ajuste_tiempo(fecha_dt)
    desglose.append(fb7)
    precio_acumulado *= mult_tiempo

    #  Factor 8: Estancia Larga 
    mult_estancia, fb8 = ajuste_estancia_larga(num_noches)
    desglose.append(fb8)
    precio_acumulado *= mult_estancia

    #  Factor 9: Canal (se aplica sobre el acumulado) 
    mult_canal, fb9 = ajuste_canal(canal)
    desglose.append(fb9)
    precio_acumulado *= mult_canal

    #  Precio final sugerido 
    precio_sugerido = round(precio_acumulado, 2)

    #  Factor 10: Suelo de rentabilidad 
    coste_unitario = _get_coste_por_habitacion(fecha_dt.month, fecha_dt.year)
    if coste_unitario > 0:
        precio_minimo = round(coste_unitario * 1.20, 2)
        desglose.append(FactorBreakdown(
            factor="suelo_rentabilidad",
            valor_aplicado=precio_minimo,
            descripcion=(
                f"Coste unitario: {coste_unitario}EUR/hab-noche x 1.20 = "
                f"{precio_minimo}EUR (margen 20%)"
            ),
            fuente="public.costes_mensuales / (19 hab x das del mes)",
        ))
    else:
        precio_minimo = round(precio_base * 0.75, 2)
        desglose.append(FactorBreakdown(
            factor="suelo_rentabilidad",
            valor_aplicado=precio_minimo,
            descripcion=f"Sin datos de costes  suelo estimado al 75% de tarifa base",
            fuente="Estimacin",
        ))

    # Asegurar que precio sugerido no baje del mnimo
    if precio_sugerido < precio_minimo:
        precio_sugerido = precio_minimo
        desglose.append(FactorBreakdown(
            factor="ajuste_suelo",
            valor_aplicado=precio_minimo,
            descripcion=f"Precio ajustado al suelo de rentabilidad ({precio_minimo}EUR)",
            fuente="Regla de negocio",
        ))

    #  Factor 11: Techo psicolgico 
    precio_maximo = round(precio_base * 2.0, 2)
    desglose.append(FactorBreakdown(
        factor="techo_psicologico",
        valor_aplicado=precio_maximo,
        descripcion=f"Doble de tarifa base ({precio_base}EUR x 2 = {precio_maximo}EUR)",
        fuente="Regla de negocio (precio_max = tarifa_base x 2.0)",
    ))

    if precio_sugerido > precio_maximo:
        precio_sugerido = precio_maximo
        desglose.append(FactorBreakdown(
            factor="ajuste_techo",
            valor_aplicado=precio_maximo,
            descripcion=f"Precio ajustado al techo psicolgico ({precio_maximo}EUR)",
            fuente="Regla de negocio",
        ))

    return PrecioResultado(
        precio_sugerido=precio_sugerido,
        precio_minimo=precio_minimo,
        precio_maximo=precio_maximo,
        precio_base=precio_base,
        desglose=desglose,
        nivel_confianza=nivel_confianza,
    )


# 
# FORMATEO PARA PRESENTACIN
# 

def formatear_resultado(r: PrecioResultado) -> str:
    """Devuelve el resultado formateado como texto legible."""
    sep = "=" * 70
    sep2 = "-" * 70
    lines = []
    lines.append(sep)
    lines.append(f"  PRECIO SUGERIDO:    {r.precio_sugerido:.2f} EUR/noche")
    lines.append(f"  Precio minimo:       {r.precio_minimo:.2f} EUR/noche")
    lines.append(f"  Precio maximo:       {r.precio_maximo:.2f} EUR/noche")
    lines.append(f"  Precio base:         {r.precio_base:.2f} EUR/noche")
    lines.append(f"  Confianza:           {r.nivel_confianza}")
    lines.append(sep2)
    lines.append("  DESGLOSE DE FACTORES:")
    lines.append("")
    for i, fb in enumerate(r.desglose, 1):
        lines.append(f"  [{i}] {fb.factor}")
        lines.append(f"      Valor: {fb.valor_aplicado}")
        lines.append(f"      -> {fb.descripcion}")
        lines.append(f"      Fuente: {fb.fuente}")
        lines.append("")
    lines.append(sep)
    return "\n".join(lines)


# 
# MAIN / TEST
# 

if __name__ == "__main__":
    print("MOTOR DE PRICING DINAMICO - Hotel Posada de la Silleria")
    print("=" * 70)
    print()

    escenarios = [
        {
            "nombre": "1. Martes random de febrero, Doble Boutique, 2 noches, Directo",
            "fecha": "2026-02-10",
            "tipo_habitacion": "Doble Boutique",
            "num_noches": 2,
            "num_huespedes": 2,
            "canal": "Directo",
        },
        {
            "nombre": "2. Sbado Corpus Christi, Suite Castellana, 2 noches, Booking",
            "fecha": "2026-06-06",
            "tipo_habitacion": "Suite Castellana (vista Patio)",
            "num_noches": 2,
            "num_huespedes": 2,
            "canal": "Booking",
        },
        {
            "nombre": "3. Domingo de agosto, Doble Superior, 3 noches, Directo",
            "fecha": "2026-08-16",
            "tipo_habitacion": "Doble Superior",
            "num_noches": 3,
            "num_huespedes": 2,
            "canal": "Directo",
        },
        {
            "nombre": "4. Mircoles de noviembre con lluvia, Individual, 1 noche, Expedia",
            "fecha": "2026-11-18",
            "tipo_habitacion": "Individual",
            "num_noches": 1,
            "num_huespedes": 1,
            "canal": "Expedia",
        },
        {
            "nombre": "5. Sbado puente Constitucin, Doble Posada, 4 noches, Directo",
            "fecha": "2026-12-06",
            "tipo_habitacion": "Doble Posada",
            "num_noches": 4,
            "num_huespedes": 2,
            "canal": "Directo",
        },
    ]

    for escenario in escenarios:
        sep = "=" * 70
        print(f"\n{sep}")
        print(f"  ESCENARIO: {escenario['nombre']}")
        print(f"{sep}")
        resultado = calcular_precio_sugerido(
            fecha=escenario["fecha"],
            tipo_habitacion=escenario["tipo_habitacion"],
            num_noches=escenario["num_noches"],
            num_huespedes=escenario["num_huespedes"],
            canal=escenario["canal"],
        )
        print(formatear_resultado(resultado))




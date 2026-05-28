"""
rag_buscador.py — Bloque 7.2: Buscador RAG que entiende preguntas en
lenguaje natural y extrae informacion relevante de la base de
conocimiento del hotel.

Flujo:
  1) Recibe pregunta en texto
  2) Clasifica: ocupacion / precio / evento / coste + extrae fechas
  3) Extrae datos relevantes de la base de conocimiento
  4) Devuelve estructura con lo encontrado (sin redactar respuesta)
"""
import re
import sys
from datetime import datetime, date
from typing import Optional

from rag_base import build_knowledge_base

# Mapeo meses español -> numero
MESES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4,
    "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
    "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
}

# Año por defecto para referencias sin año (prediccion es mayo 2026)
ANIO_POR_DEFECTO = 2026


# =====================================================================
#  1. CLASIFICADOR DE INTENCION
# =====================================================================

def clasificar_intencion(pregunta: str) -> list[str]:
    """
    Analiza la pregunta y devuelve una lista de categorias detectadas.
    Puede devolver multiples categorias (ej: precio + ocupacion).
    """
    p = pregunta.lower()
    categorias = []

    # ── Ocupacion ──────────────────────────────────────
    if any(palabra in p for palabra in [
        "ocupacion", "ocupado", "ocupada", "lleno", "llena",
        "llenarse", "aforo", "porcentaje", "huespedes", "huesped",
        "gente", "entrada", "habitaciones libres", "flojo", "fuerte",
    ]):
        categorias.append("ocupacion")

    # ── Precio ─────────────────────────────────────────
    if any(palabra in p for palabra in [
        "precio", "precios", "tarifa", "tarifas", "subir", "bajar",
        "subo", "bajo", "aumentar", "reducir", "caro", "barato",
        "costar", "vale", "dinamico", "competencia",
    ]):
        categorias.append("precio")

    # ── Evento ─────────────────────────────────────────
    if any(palabra in p for palabra in [
        "evento", "eventos", "festividad", "festivo", "festividades",
        "celebracion", "procesion", "fiesta", "feria",
        "semana santa", "corpus", "navidad", "nochevieja",
        "año nuevo", "virgen", "sagrario", "el greco",
        "constitucion", "puente",
    ]):
        categorias.append("evento")

    # ── Coste ──────────────────────────────────────────
    if any(palabra in p for palabra in [
        "coste", "costes", "gasto", "gastos", "gastar",
        "operativos", "mantenimiento", "personal", "suministros",
        "factura", "dinero gastado",
    ]):
        categorias.append("coste")

    # ── Fallback: si no detecto nada, asumir ocupacion ──
    if not categorias:
        categorias.append("ocupacion")

    return categorias


# =====================================================================
#  2. EXTRACTOR DE FECHAS
# =====================================================================

def extraer_fechas(pregunta: str) -> dict:
    """
    Extrae referencias temporales de la pregunta.
    Devuelve un dict con las claves que se hayan podido determinar:
      - "tipo": "dia" | "mes" | "rango" | "semana" | "proximos" | "todo"
      - "dia": int (si tipo="dia")
      - "mes": int (si tipo="mes" o "dia")
      - "anio": int
      - "inicio": str "YYYY-MM-DD" (si tipo="rango")
      - "fin": str "YYYY-MM-DD" (si tipo="rango")
      - "dias": int (si tipo="proximos")
    """
    p = pregunta.lower()
    resultado = {"tipo": "todo"}

    # ── "proximos X dias" / "proximos X meses" ────────
    m = re.search(r"proximos?\s+(\d+)\s+(dias|día|días|mes|meses)", p)
    if m:
        cantidad = int(m.group(1))
        unidad = m.group(2)
        if unidad.startswith("d"):
            resultado["tipo"] = "proximos"
            resultado["dias"] = cantidad
        else:
            # proximos N meses -> convertimos aprox a 30*dias
            resultado["tipo"] = "proximos"
            resultado["dias"] = cantidad * 30
        return resultado

    # ── "esta semana" ──────────────────────────────────
    if "esta semana" in p:
        resultado["tipo"] = "semana"
        return resultado

    # ── "este mes" ─────────────────────────────────────
    if "este mes" in p:
        hoy = date.today()
        resultado["tipo"] = "mes"
        resultado["mes"] = hoy.month
        resultado["anio"] = hoy.year
        return resultado

    # ── Buscar meses en el texto ───────────────────────
    mes_detectado = None
    for nombre_mes, num in MESES.items():
        if nombre_mes in p:
            mes_detectado = num
            break

    # ── Buscar año (4 digitos) ─────────────────────────
    anio_detectado = None
    m_anio = re.search(r"\b(20\d{2})\b", p)
    if m_anio:
        anio_detectado = int(m_anio.group(1))

    # ── Buscar rango "de X a Y" o "entre X y Y" ───────
    m_rango = re.search(r"(?:del?\s+)?(\d+)\s*(?:de\s+)?([a-z]+)\s*(?:al?\s+|a\s+|y\s+|hasta\s+)(?:del?\s+)?(\d+)\s*(?:de\s+)?([a-z]+)", p)
    if m_rango:
        dia_ini = int(m_rango.group(1))
        mes_ini_nombre = m_rango.group(2)
        dia_fin = int(m_rango.group(3))
        mes_fin_nombre = m_rango.group(4)

        mes_ini = MESES.get(mes_ini_nombre)
        mes_fin = MESES.get(mes_fin_nombre)
        if mes_ini and mes_fin:
            anio = anio_detectado or ANIO_POR_DEFECTO
            resultado["tipo"] = "rango"
            resultado["inicio"] = f"{anio}-{mes_ini:02d}-{dia_ini:02d}"
            resultado["fin"] = f"{anio}-{mes_fin:02d}-{dia_fin:02d}"
            return resultado

    # ── Buscar "dia de mes" (ej: "15 de junio") ───────
    m_dia = re.search(r"(\d+)\s*(?:de\s+)?([a-z]+)", p)
    if m_dia and mes_detectado:
        # Confirmar que el match cayo en el mes
        dia = int(m_dia.group(1))
        if 1 <= dia <= 31:
            anio = anio_detectado or ANIO_POR_DEFECTO
            resultado["tipo"] = "dia"
            resultado["dia"] = dia
            resultado["mes"] = mes_detectado
            resultado["anio"] = anio
            return resultado

    # ── Solo mes (ej: "en junio", "que ocupacion habra en mayo") ──
    if mes_detectado:
        anio = anio_detectado or ANIO_POR_DEFECTO
        resultado["tipo"] = "mes"
        resultado["mes"] = mes_detectado
        resultado["anio"] = anio
        return resultado

    # ── Solo año ───────────────────────────────────────
    if anio_detectado:
        resultado["tipo"] = "anio"
        resultado["anio"] = anio_detectado
        return resultado

    return resultado


# =====================================================================
#  3. EXTRACTOR DE DATOS RELEVANTES
# =====================================================================

def filtrar_por_fecha(registros: list[dict], campo_fecha: str,
                      ref_fecha: dict) -> list[dict]:
    """
    Filtra una lista de registros con campo_fecha (str "YYYY-MM-DD")
    segun la referencia temporal extraida.
    """
    if ref_fecha["tipo"] == "todo":
        return registros

    filtrados = []
    for r in registros:
        f = r.get(campo_fecha, "")
        if not f:
            continue
        try:
            f_dt = date.fromisoformat(f)
            f_mes = f_dt.month
            f_anio = f_dt.year
            f_dia = f_dt.day
        except ValueError:
            continue

        if ref_fecha["tipo"] == "dia":
            if (f_dia == ref_fecha.get("dia") and
                f_mes == ref_fecha.get("mes") and
                f_anio == ref_fecha.get("anio")):
                filtrados.append(r)

        elif ref_fecha["tipo"] == "mes":
            if f_mes == ref_fecha.get("mes") and f_anio == ref_fecha.get("anio"):
                filtrados.append(r)

        elif ref_fecha["tipo"] == "rango":
            try:
                inicio = date.fromisoformat(ref_fecha["inicio"])
                fin = date.fromisoformat(ref_fecha["fin"])
                if inicio <= f_dt <= fin:
                    filtrados.append(r)
            except KeyError:
                filtrados.append(r)

        elif ref_fecha["tipo"] == "proximos":
            # Filtramos por fechas dentro de los proximos N dias
            # desde el inicio de la prediccion
            pass  # lo manejamos aparte

    return filtrados


def extraer_ocupacion(kb: dict, ref_fecha: dict) -> dict:
    """Extrae datos de prediccion segun la referencia temporal."""
    resultado = {
        "categoria": "ocupacion",
        "fuente": "prediccion SARIMA",
        "media_realista": kb["prediccion"]["media_realista"],
        "dias": [],
    }

    for dia in kb["prediccion"]["diario"]:
        incluir = False
        f = date.fromisoformat(dia["fecha"])
        f_mes = f.month

        if ref_fecha["tipo"] == "todo":
            incluir = True
        elif ref_fecha["tipo"] == "mes" and f_mes == ref_fecha.get("mes"):
            incluir = True
        elif ref_fecha["tipo"] == "dia":
            f_dia = f.day
            if (f_dia == ref_fecha.get("dia") and
                f_mes == ref_fecha.get("mes")):
                incluir = True
        elif ref_fecha["tipo"] == "proximos":
            idx = kb["prediccion"]["diario"].index(dia)
            if idx < ref_fecha.get("dias", 30):
                incluir = True
        elif ref_fecha["tipo"] == "semana":
            idx = kb["prediccion"]["diario"].index(dia)
            if idx < 7:
                incluir = True

        if incluir:
            resultado["dias"].append(dia)

    # Anadir estadisticas del periodo filtrado
    if resultado["dias"]:
        realistas = [d["realista"] for d in resultado["dias"]]
        resultado["media_periodo"] = round(sum(realistas) / len(realistas), 1)
        resultado["min_periodo"] = min(realistas)
        resultado["max_periodo"] = max(realistas)
        resultado["dias_mostrados"] = len(resultado["dias"])

    return resultado


def extraer_precios(kb: dict, ref_fecha: dict) -> dict:
    """Extrae datos de competencia y ocupacion para decisiones de precio."""
    resultado = {
        "categoria": "precio",
        "fuentes": ["precios_competencia", "prediccion_ocupacion"],
        "competencia": {
            "hoteles": kb["competencia"]["hoteles"],
            "total_registros": kb["competencia"]["total"],
            "precios": filtrar_por_fecha(kb["competencia"]["precios"], "fecha", ref_fecha),
        },
        "ocupacion_actual": {
            "media_historica": kb["ocupacion_historica"]["media"],
        },
    }

    # Si no hay filtro, mostrar todos los precios; si hay filtro
    # de fecha, mostrar solo los de ese periodo
    if not resultado["competencia"]["precios"] and ref_fecha["tipo"] == "todo":
        resultado["competencia"]["precios"] = kb["competencia"]["precios"]

    return resultado


def extraer_eventos(kb: dict, ref_fecha: dict) -> dict:
    """Extrae eventos segun la referencia temporal."""
    resultado = {
        "categoria": "evento",
        "total": kb["eventos"]["total"],
        "eventos": kb["eventos"]["lista"][:],  # copia
    }

    if ref_fecha["tipo"] != "todo":
        resultado["eventos"] = filtrar_por_fecha(
            kb["eventos"]["lista"], "fecha_inicio", ref_fecha
        )

    return resultado


def extraer_costes(kb: dict, ref_fecha: dict) -> dict:
    """Extrae datos de costes."""
    resultado = {
        "categoria": "coste",
        "media_mensual": kb["costes"]["media_mensual"],
        "total_anual": kb["costes"]["total_anual"],
        "por_mes": kb["costes"]["por_mes"][:],
    }

    if ref_fecha["tipo"] == "mes":
        resultado["por_mes"] = [
            m for m in kb["costes"]["por_mes"]
            if m["mes"] == ref_fecha["mes"]
        ]
    elif ref_fecha["tipo"] == "anio":
        resultado["por_mes"] = [
            m for m in kb["costes"]["por_mes"]
            if m["anio"] == ref_fecha["anio"]
        ]

    if resultado["por_mes"]:
        totales = [m["total"] for m in resultado["por_mes"]]
        resultado["media_filtrada"] = round(sum(totales) / len(totales), 2)
        resultado["meses_mostrados"] = len(resultado["por_mes"])

    return resultado


# =====================================================================
#  4. ORQUESTADOR: preguntar()
# =====================================================================

def preguntar(pregunta: str, kb: Optional[dict] = None) -> dict:
    """
    Punto de entrada: recibe una pregunta y devuelve los datos
    relevantes extraidos de la base de conocimiento.

    Si no se pasa kb, lo construye automaticamente.
    """
    if kb is None:
        print("(Construyendo base de conocimiento...)")
        kb = build_knowledge_base(verbose=False)

    # 1. Clasificar
    categorias = clasificar_intencion(pregunta)

    # 2. Extraer fechas
    ref_fecha = extraer_fechas(pregunta)

    # 3. Extraer datos por cada categoria detectada
    datos = {
        "pregunta_original": pregunta,
        "categorias_detectadas": categorias,
        "referencia_temporal": ref_fecha,
        "resultados": [],
    }

    for cat in categorias:
        if cat == "ocupacion":
            datos["resultados"].append(extraer_ocupacion(kb, ref_fecha))
        elif cat == "precio":
            datos["resultados"].append(extraer_precios(kb, ref_fecha))
        elif cat == "evento":
            datos["resultados"].append(extraer_eventos(kb, ref_fecha))
        elif cat == "coste":
            datos["resultados"].append(extraer_costes(kb, ref_fecha))

    return datos


# =====================================================================
#  5. PRUEBAS CON 3 EJEMPLOS
# =====================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("BLOQUE 7.2: BUSCADOR RAG — PRUEBAS")
    print("=" * 60)
    print("(Construyendo base de conocimiento... esto toma unos segundos)\n")

    kb = build_knowledge_base(verbose=False)

    preguntas_ejemplo = [
        "¿qué ocupación habrá en junio?",
        "¿cuándo subo precios?",
        "¿qué días estaré flojo?",
    ]

    for i, pregunta in enumerate(preguntas_ejemplo, 1):
        print("\n" + "=" * 60)
        print(f"  PREGUNTA {i}: \"{pregunta}\"")
        print("=" * 60)

        resultado = preguntar(pregunta, kb=kb)

        print(f"\n  Categorias detectadas: {resultado['categorias_detectadas']}")
        print(f"  Referencia temporal:   {resultado['referencia_temporal']}")

        for r in resultado["resultados"]:
            print(f"\n  --- DATOS EXTRAIDOS ({r['categoria']}) ---")

            if r["categoria"] == "ocupacion":
                print(f"  Fuente: {r['fuente']}")
                print(f"  Media general:      {r['media_realista']}%")
                if "media_periodo" in r:
                    print(f"  Media del periodo:  {r['media_periodo']}%")
                    print(f"  Rango del periodo:  {r['min_periodo']}% - {r['max_periodo']}%")
                    print(f"  Dias encontrados:   {r['dias_mostrados']}")
                    print(f"  Primeros 5 dias:")
                    for d in r['dias'][:5]:
                        print(f"    {d['fecha']}  PES={d['pesimista']}%  "
                              f"REAL={d['realista']}%  OPT={d['optimista']}%")

            elif r["categoria"] == "precio":
                print(f"  Hoteles vigilados: {len(r['competencia']['hoteles'])}")
                print(f"  Registros totales: {r['competencia']['total_registros']}")
                print(f"  Media ocupacion historica: {r['ocupacion_actual']['media_historica']}%")
                if r['competencia']['precios']:
                    print(f"  Precios disponibles ({len(r['competencia']['precios'])} registros):")
                    for p in r['competencia']['precios'][:6]:
                        print(f"    {p['hotel']:35s} {p['tipo_habitacion']:20s} "
                              f"{p['fecha']}  {p['precio']}EUR ({p['fuente']})")

            elif r["categoria"] == "evento":
                print(f"  Total eventos en BD: {r['total']}")
                print(f"  Eventos en este resultado: {len(r['eventos'])}")
                for ev in r['eventos']:
                    impacto = ev['impacto']
                    print(f"    - {ev['nombre']:40s} {ev['fecha_inicio']} -> "
                          f"{ev['fecha_fin']}  [impacto {impacto}]")

            elif r["categoria"] == "coste":
                print(f"  Media mensual: {r['media_mensual']:,.2f} EUR")
                print(f"  Total anual:   {r['total_anual']:,.2f} EUR")
                if "media_filtrada" in r:
                    print(f"  Media filtrada: {r['media_filtrada']:,.2f} EUR")
                    print(f"  Meses mostrados: {r['meses_mostrados']}")
                for m in r['por_mes'][:4]:
                    print(f"    {m['anio']}-{m['mes']:02d}: total={m['total']:,.2f} EUR  "
                          f"(operativos={m['operativos']}, "
                          f"personal={m['personal']}, "
                          f"mantenimiento={m['mantenimiento']})")

        print()

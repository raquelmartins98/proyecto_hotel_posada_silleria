"""
rag_respuestas.py -- Bloque 7.3: Redaccion de respuestas en lenguaje
natural para el asistente IA del hotel.

Toma los datos extraidos por rag_buscador.py y los convierte en
recomendaciones claras y accionables, como las daria un revenue manager.
"""
import sys
from datetime import date, datetime
from typing import Optional

from rag_buscador import preguntar, build_knowledge_base


# =====================================================================
#  FUNCIONES AUXILIARES
# =====================================================================

def formatear_fecha(fecha_str: str) -> str:
    """Convierte '2026-05-15' a '15 de mayo de 2026'."""
    try:
        f = date.fromisoformat(fecha_str)
        meses = ["enero", "febrero", "marzo", "abril", "mayo", "junio",
                 "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
        return f"{f.day} de {meses[f.month - 1]} de {f.year}"
    except ValueError:
        return fecha_str


def nombre_mes(mes_num: int) -> str:
    meses = ["enero", "febrero", "marzo", "abril", "mayo", "junio",
             "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
    return meses[mes_num - 1] if 1 <= mes_num <= 12 else str(mes_num)


def formatear_rango(f_inicio: str, f_fin: str) -> str:
    """Convierte rango '2026-05-01' -> '2026-05-05' a texto."""
    try:
        inicio = date.fromisoformat(f_inicio)
        fin = date.fromisoformat(f_fin)
        meses = ["enero", "febrero", "marzo", "abril", "mayo", "junio",
                 "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]

        if inicio.month == fin.month and inicio.year == fin.year:
            return f"del {inicio.day} al {fin.day} de {meses[fin.month - 1]} de {fin.year}"
        elif inicio.year == fin.year:
            return f"del {inicio.day} de {meses[inicio.month - 1]} al {fin.day} de {meses[fin.month - 1]} de {fin.year}"
        else:
            return f"del {inicio.day} de {meses[inicio.month - 1]} de {inicio.year} al {fin.day} de {meses[fin.month - 1]} de {fin.year}"
    except ValueError:
        return f"{f_inicio} a {f_fin}"


def clasificar_ocupacion(porcentaje: float) -> str:
    """Clasifica un % de ocupacion en etiqueta descriptiva."""
    if porcentaje >= 90:
        return "llenazo absoluto"
    elif porcentaje >= 80:
        return "muy alta"
    elif porcentaje >= 70:
        return "alta"
    elif porcentaje >= 60:
        return "moderada"
    elif porcentaje >= 50:
        return "baja"
    else:
        return "muy baja"


# =====================================================================
#  GENERADORES DE RESPUESTAS POR CATEGORIA
# =====================================================================

def responder_ocupacion(resultado: dict, ref_fecha: dict) -> str:
    """Redacta respuesta para preguntas de ocupacion."""
    dias = resultado.get("dias", [])
    if not dias:
        # No hay datos para la fecha solicitada
        return _responder_fuera_rango(ref_fecha)

    media = resultado["media_periodo"]
    minimo = resultado["min_periodo"]
    maximo = resultado["max_periodo"]

    # Separar dias flojos (por debajo de la media) y fuertes
    flojos = [d for d in dias if d["realista"] < media]
    fuertes = [d for d in dias if d["realista"] > media]

    # Primer y ultimo dia del periodo
    primera = dias[0]["fecha"]
    ultima = dias[-1]["fecha"]
    rango_texto = formatear_rango(primera, ultima)

    lineas = []
    lineas.append(f"[DATOS] Prevision de ocupacion {rango_texto}")
    lineas.append("")
    lineas.append(f"De media, espero una ocupacion del **{media:.1f}%**, "
                  f"con un rango de **{minimo:.1f}%** a **{maximo:.1f}%**.")

    # Tres escenarios
    if dias:
        pes_media = sum(d["pesimista"] for d in dias) / len(dias)
        opt_media = sum(d["optimista"] for d in dias) / len(dias)
        lineas.append(f"En el mejor escenario (optimista) podrias llegar al "
                      f"{opt_media:.1f}%, y en el peor (pesimista) al {pes_media:.1f}%.")

    # Dias fuertes
    lineas.append("")
    if fuertes:
        top_fuertes = sorted(fuertes, key=lambda d: -d["realista"])[:3]
        lineas.append("**Dias mas fuertes:**")
        for d in top_fuertes:
            etiq = clasificar_ocupacion(d["realista"])
            fecha_leg = formatear_fecha(d["fecha"])
            lineas.append(f"  * {fecha_leg}: **{d['realista']:.1f}%** ({etiq})")

    # Dias flojos
    if flojos:
        top_flojos = sorted(flojos, key=lambda d: d["realista"])[:3]
        lineas.append("**Dias mas flojos:**")
        for d in top_flojos:
            etiq = clasificar_ocupacion(d["realista"])
            fecha_leg = formatear_fecha(d["fecha"])
            lineas.append(f"  * {fecha_leg}: **{d['realista']:.1f}%** ({etiq})")

    # Recomendacion
    lineas.append("")
    if media >= 80:
        lineas.append("[REC] **Recomendacion:** La ocupacion es alta. "
                      "Considera subir tarifas los dias punta y minimizar descuentos. "
                      "Si tienes overbooking, prioriza a huespedes de mayor gasto.")
    elif media >= 65:
        lineas.append("[REC] **Recomendacion:** Ocupacion moderada-alta. "
                      "Manten tarifas estables pero prepara ofertas de ultimo minuto "
                      "para los dias mas flojos de la semana.")
    elif media >= 50:
        lineas.append("[REC] **Recomendacion:** Ocupacion baja-media. "
                      "Activa promociones para los dias flojos (ej: descuento por "
                      "estancia de 2+ noches, pack cena + habitacion). "
                      "Revisa si hay eventos locales que puedas aprovechar.")
    else:
        lineas.append("[REC] **Recomendacion:** Ocupacion baja. "
                      "Considero campañas agresivas de captacion: descuentos, "
                      "colaboracion con agencias locales, o paquetes con actividades "
                      "en Toledo para atraer turismo de fin de semana.")

    return "\n".join(lineas)


def responder_precio(resultado: dict, ref_fecha: dict) -> str:
    """
    Redacta respuesta para preguntas de precio.
    Cruza datos de competencia + ocupacion para recomendar accion.
    """
    comp = resultado.get("competencia", {})
    precios = comp.get("precios", [])
    ocup_media = resultado.get("ocupacion_actual", {}).get("media_historica", 0)

    lineas = []
    lineas.append("[REC] **Analisis de precios y competencia**")
    lineas.append("")

    # Resumen de competencia
    if precios:
        hoteles_unicos = set(p["hotel"] for p in precios)
        lineas.append(f"Actualmente vigilamos **{len(hoteles_unicos)} hoteles** "
                      f"con **{len(precios)} precios registrados**.")

        # Precio medio de la competencia
        precios_sin_cero = [p["precio"] for p in precios if p["precio"] > 0]
        if precios_sin_cero:
            precio_medio_comp = sum(precios_sin_cero) / len(precios_sin_cero)
            precio_min_comp = min(precios_sin_cero)
            precio_max_comp = max(precios_sin_cero)

            lineas.append(f"La competencia tiene precios entre "
                          f"**{precio_min_comp:.0f} EUR** y **{precio_max_comp:.0f} EUR**, "
                          f"con una media de **{precio_medio_comp:.0f} EUR** por noche.")

            # Precios por tipo de habitacion
            dobles = [p["precio"] for p in precios if "doble" in p["tipo_habitacion"].lower() and p["precio"] > 0]
            suites = [p["precio"] for p in precios if "suite" in p["tipo_habitacion"].lower() and p["precio"] > 0]

            if dobles:
                media_dobles = sum(dobles) / len(dobles)
                lineas.append(f"  * Habitaciones dobles: media **{media_dobles:.0f} EUR**")
            if suites:
                media_suites = sum(suites) / len(suites)
                lineas.append(f"  * Suites: media **{media_suites:.0f} EUR**")
    else:
        lineas.append("No hay datos de precios de competencia para el periodo indicado.")

    # Ocupacion como indicador de demanda
    lineas.append("")
    lineas.append(f"**Contexto de demanda:** la ocupacion media historica "
                  f"es del **{ocup_media:.1f}%**.")

    # Obtener prediccion de ocupacion para los mismos dias
    # (se pasa en el resultado de precio)
    if "prediccion_asociada" in resultado:
        pred = resultado["prediccion_asociada"]
        lineas.append(f"Y para este periodo concreto, la prediccion estima "
                      f"una ocupacion del **{pred['media']:.1f}%** "
                      f"(rango {pred['minimo']:.1f}% - {pred['maximo']:.1f}%).")

    # Recomendacion
    lineas.append("")
    lineas.append("[REC] **Recomendacion de precios:**")

    if precios_sin_cero:
        precio_medio_comp = sum(precios_sin_cero) / len(precios_sin_cero)
    else:
        precio_medio_comp = 0

    # Logica combinada: ocupacion + competencia
    if ocup_media >= 75 or precio_medio_comp == 0:
        lineas.append("  [OK] **Subir tarifas.** La demanda es alta. Tus precios "
                      "pueden estar por debajo del optimo. Ajusta al alza "
                      "especialmente los fines de semana y dias de evento.")
    elif ocup_media >= 60:
        lineas.append("  [->] **Mantener tarifas** con ajustes selectivos. "
                      "Sube un 5-10% en dias con ocupacion prevista > 75% "
                      "(fines de semana), y ofrece descuentos para captar "
                      "los dias entre semana.")
    else:
        lineas.append("  [v] **Revisar a la baja o promocionar.** La ocupacion "
                      "baja no justifica precios altos. Considera: descuento "
                      "por reserva anticipada, tarifa no reembolsable mas baja, "
                      "o paquetes con actividades en Toledo.")

    return "\n".join(lineas)


def responder_evento(resultado: dict, ref_fecha: dict) -> str:
    """Redacta respuesta para preguntas sobre eventos."""
    eventos = resultado.get("eventos", [])

    lineas = []
    lineas.append("? **Eventos locales detectados**")
    lineas.append("")

    if not eventos:
        lineas.append("No hay eventos programados para el periodo indicado.")
        lineas.append("")
        lineas.append("[REC] **Recomendacion:** Aprovecha para centrarte en "
                      "campañas genericas y captar turismo de fin de semana "
                      "con paquetes atractivos.")
        return "\n".join(lineas)

    lineas.append(f"He encontrado **{len(eventos)} eventos** en el periodo:")

    for ev in eventos:
        impacto = ev["impacto"]
        icono = "[!!]" if impacto == "critico" else "[!]" if impacto == "alto" else "[i]"
        fecha_texto = formatear_rango(ev["fecha_inicio"], ev["fecha_fin"])
        repite = " (repite cada año)" if ev.get("repite_anual") else ""

        lineas.append(f"\n{icono} **{ev['nombre']}**{repite}")
        lineas.append(f"   {fecha_texto}")
        lineas.append(f"   Tipo: {ev['tipo']} | Impacto: {impacto}")

        # Recomendacion especifica segun el evento
        nombre_lower = ev["nombre"].lower()

        if "corpus" in nombre_lower:
            lineas.append(f"   [!] **IMPORTANTE:** La procesion de Corpus Christi "
                          f"pasa por la Calle Sillería, justo donde esta el hotel. "
                          f"Es el evento con mas potencial del año. Sube tarifas "
                          f"al maximo y activa reserva anticipada con deposito.")
        elif "semana santa" in nombre_lower:
            lineas.append(f"   [*] Semana Santa = alta demanda en Toledo. "
                          f"Sube tarifas progresivamente desde 2 semanas antes. "
                          f"Minimo de estancia recomendado: 2 noches.")
        elif "navidad" in nombre_lower or "nochevieja" in nombre_lower:
            lineas.append(f"   [!] Temporada alta navideña. Sube tarifas, exige "
                          f"minimo de estancia y considera paquete con cena "
                          f"de Nochevieja incluida.")
        elif "el greco" in nombre_lower or "festival" in nombre_lower:
            lineas.append(f"   [*] Festival cultural atrae visitantes. Precios "
                          f"premium durante el evento. Coordina con la "
                          f"organizacion para posibles acuerdos.")
        elif "constitucion" in nombre_lower or "puente" in nombre_lower:
            lineas.append(f"   [*] Puente festivo = escapada nacional. "
                          f"Demanda alta, sube tarifas y activa minimo de "
                          f"estancia de 2-3 noches.")
        elif "virgen" in nombre_lower or "sagrario" in nombre_lower:
            lineas.append(f"   [i] Festividad religiosa local. Demanda media-alta. "
                          f"Ajusta tarifas al alza moderadamente.")

    # Recomendacion general
    lineas.append("")
    criticos = [ev for ev in eventos if ev["impacto"] == "critico"]
    altos = [ev for ev in eventos if ev["impacto"] == "alto"]

    if criticos:
        lineas.append(f"[REC] **Recomendacion:** Tienes **{len(criticos)} evento(s) "
                      f"de impacto critico** en el periodo. Activa YA la estrategia "
                      f"de precios premium, minimo de estancia y deposito "
                      f"no reembolsable.")
    elif altos:
        lineas.append(f"[REC] **Recomendacion:** Hay **{len(altos)} evento(s) de alto impacto** "
                      f"en el periodo. Sube tarifas y prepara la operativa "
                      f"(refuerzo de personal, minimo de estancia).")

    return "\n".join(lineas)


def responder_costes(resultado: dict, ref_fecha: dict) -> str:
    """Redacta respuesta para preguntas sobre costes."""
    por_mes = resultado.get("por_mes", [])
    media_mensual = resultado["media_mensual"]
    total_anual = resultado["total_anual"]

    lineas = []
    lineas.append("[REC] **Resumen de costes**")
    lineas.append("")

    if "media_filtrada" in resultado:
        lineas.append(f"Para el periodo solicitado, los costes mensuales "
                      f"suman **{resultado['media_filtrada']:,.2f} EUR** de media "
                      f"al mes ({resultado['meses_mostrados']} mes(es) analizados).")
    else:
        lineas.append(f"De media, los costes mensuales del hotel son de "
                      f"**{media_mensual:,.2f} EUR**, con un total anual de "
                      f"**{total_anual:,.2f} EUR**.")

    # Desglose por categoria si tenemos datos
    if por_mes:
        ultimo = por_mes[-1]
        lineas.append("")
        lineas.append(f"**Desglose del ultimo mes disponible** "
                      f"({nombre_mes(ultimo['mes'])}/{ultimo['anio']}):")
        lineas.append(f"  * Operativos:   {ultimo['operativos']:,.2f} EUR")
        lineas.append(f"  * Mantenimiento: {ultimo['mantenimiento']:,.2f} EUR")
        lineas.append(f"  * Personal:     {ultimo['personal']:,.2f} EUR")
        lineas.append(f"  * Suministros:  {ultimo['suministros']:,.2f} EUR")
        lineas.append(f"  * Otros:        {ultimo['otros']:,.2f} EUR")
        lineas.append(f"  ---------------------------")
        lineas.append(f"  * **TOTAL:**     {ultimo['total']:,.2f} EUR")

        # Porcentaje del personal sobre el total (suele ser el mayor coste)
        pct_personal = (ultimo['personal'] / ultimo['total']) * 100
        lineas.append(f"")
        lineas.append(f"El personal representa el **{pct_personal:.1f}%** del total, "
                      f"el mayor coste fijo del hotel.")

    # Recomendacion
    lineas.append("")
    lineas.append("[REC] **Recomendacion:**")
    if por_mes:
        # Buscar el mes mas caro
        mes_caro = max(por_mes, key=lambda m: m["total"])
        mes_barato = min(por_mes, key=lambda m: m["total"])
        lineas.append(f"  * El mes mas costoso fue {nombre_mes(mes_caro['mes'])} "
                      f"({mes_caro['total']:,.2f} EUR)")
        lineas.append(f"  * El mas economico fue {nombre_mes(mes_barato['mes'])} "
                      f"({mes_barato['total']:,.2f} EUR)")
        diferencia = mes_caro["total"] - mes_barato["total"]
        lineas.append(f"  * Diferencia entre ambos: **{diferencia:,.2f} EUR**")

    lineas.append(f"  * Revisa si los costes de personal se ajustan a la "
                  f"ocupacion: en meses flojos podrias optimizar turnos.")
    lineas.append(f"  * Vigila mantenimiento: suele ser el primer coste "
                  f"recortable si necesitas ajustar.")

    return "\n".join(lineas)


def _responder_fuera_rango(ref_fecha: dict) -> str:
    """Responde cuando la pregunta pide datos fuera del horizonte."""
    tipo = ref_fecha.get("tipo", "todo")

    if tipo == "mes":
        mes = ref_fecha.get("mes", 0)
        anio = ref_fecha.get("anio", 0)
        texto_fecha = f"{nombre_mes(mes)} de {anio}" if anio else nombre_mes(mes)
    elif tipo == "dia":
        texto_fecha = f"{ref_fecha.get('dia', '?')} de {nombre_mes(ref_fecha.get('mes', 0))}"
    elif tipo == "rango":
        texto_fecha = f"{ref_fecha.get('inicio', '?')} a {ref_fecha.get('fin', '?')}"
    else:
        texto_fecha = "esa fecha"

    return (
        f"[REC] **Fuera de mi horizonte de prediccion**\n\n"
        f"Mi prediccion actual cubre hasta el **30 de mayo de 2026** "
        f"(30 dias a partir de los datos historicos).\n\n"
        f"Para {texto_fecha} no tengo prediccion generada.\n\n"
        f"[REC] **Recomendacion:** Si necesitas previsión para {texto_fecha}, "
        f"puedo reentrenar el modelo con datos adicionales o ampliar "
        f"el horizonte de prediccion. Actualmente tengo 365 dias de "
        f"historico (mayo 2025 - abril 2026) y genero 30 dias de "
        f"prediccion."
    )


# =====================================================================
#  ORQUESTADOR PRINCIPAL
# =====================================================================

def responder(pregunta: str, kb: Optional[dict] = None) -> str:
    """
    Punto de entrada: recibe una pregunta y devuelve una respuesta
    redactada en lenguaje natural con recomendacion accionable.
    """
    if kb is None:
        kb = build_knowledge_base(verbose=False)

    # Obtener datos del buscador
    datos = preguntar(pregunta, kb=kb)

    categorias = datos["categorias_detectadas"]
    ref_fecha = datos["referencia_temporal"]
    resultados = datos["resultados"]

    respuestas = []
    for r in resultados:
        cat = r["categoria"]

        if cat == "ocupacion":
            # Si la pregunta es de precio, la ocupacion se incluye como contexto
            respuestas.append(responder_ocupacion(r, ref_fecha))

        elif cat == "precio":
            # Para precio, anadimos la prediccion de ocupacion como contexto
            pred_ocup = extraer_prediccion_contexto(kb, ref_fecha)
            if pred_ocup:
                r["prediccion_asociada"] = pred_ocup
            respuestas.append(responder_precio(r, ref_fecha))

        elif cat == "evento":
            respuestas.append(responder_evento(r, ref_fecha))

        elif cat == "coste":
            respuestas.append(responder_costes(r, ref_fecha))

    return "\n\n---\n\n".join(respuestas)


def extraer_prediccion_contexto(kb: dict, ref_fecha: dict) -> Optional[dict]:
    """Extrae un resumen de la prediccion para usarlo como contexto."""
    from rag_buscador import extraer_ocupacion

    resultado = extraer_ocupacion(kb, ref_fecha)
    if resultado.get("dias") and "media_periodo" in resultado:
        return {
            "media": resultado["media_periodo"],
            "minimo": resultado["min_periodo"],
            "maximo": resultado["max_periodo"],
            "dias": resultado["dias_mostrados"],
        }
    return None


# =====================================================================
#  PRUEBAS CON LAS 3 PREGUNTAS
# =====================================================================

if __name__ == "__main__":
    print("=" * 68)
    print("  BLOQUE 7.3: ASISTENTE RAG -- RESPUESTAS EN LENGUAJE NATURAL")
    print("=" * 68)

    print("\n(Construyendo base de conocimiento...)\n")
    kb = build_knowledge_base(verbose=False)

    preguntas = [
        "¿qué ocupación habrá en junio?",
        "¿cuándo subo precios?",
        "¿qué días estaré flojo?",
    ]

    for i, pregunta in enumerate(preguntas, 1):
        print("\n" + "=" * 68)
        print(f"  PREGUNTA {i}: \"{pregunta}\"")
        print("=" * 68)
        print()

        respuesta = responder(pregunta, kb=kb)
        print(respuesta)

    print("\n" + "=" * 68)
    print("  FIN DE PRUEBAS")
    print("=" * 68)

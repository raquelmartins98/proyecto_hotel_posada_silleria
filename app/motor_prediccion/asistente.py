"""
asistente.py — Bloque 7.4: Interfaz interactiva en terminal para el
Asistente de Revenue Management del Hotel Posada de la Silleria.

Permite hacer preguntas en lenguaje natural y recibir respuestas con
recomendaciones accionables. Bucle hasta que el usuario escriba "salir".
"""
import sys
import io
import warnings

warnings.filterwarnings("ignore")

# Forzar UTF-8 en stdout para evitar problemas con emojis sustitutos
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from rag_respuestas import responder, build_knowledge_base


# ── Construir base de conocimiento al arrancar ────────────

print("=" * 68)
print("  [HOTEL] Asistente de Revenue Management")
print("  Hotel Boutique Posada de la Silleria")
print("  Toledo - 19 habitaciones")
print("=" * 68)

print("\nConectando con Insforge...", end=" ", flush=True)
try:
    kb = build_knowledge_base(verbose=False)
    print("[OK]")
except Exception as e:
    print("[FAIL]")
    print(f"\nError de conexion: {e}")
    print("Verifica que frontend/.env tenga las credenciales correctas")
    print("y que el servidor Insforge este activo.")
    sys.exit(1)


def mostrar_ayuda():
    """Muestra el menu de ayuda con ejemplos."""
    print()
    print("-" * 68)
    print("  [i] Tipos de preguntas que entiendo:")
    print()
    print("    OCUPACION  -> prevision, dias flojos, dias fuertes,")
    print("                  porcentaje de ocupacion")
    print("    PRECIOS    -> subir/bajar tarifas, competencia,")
    print("                  precio por noche")
    print("    EVENTOS    -> festividades, Semana Santa, Corpus,")
    print("                  puentes, impacto en ocupacion")
    print("    COSTES     -> gastos mensuales, desglose, margenes")
    print()
    print("  Ejemplos que puedes probar:")
    for q in PLEGUNTAS_EJEMPLO:
        print(f'    - "{q["nombre"]}"')
    print()
    print("  Para salir escribe: adios, chao, salir, exit")
    print("-" * 68)


PLEGUNTAS_EJEMPLO = [
    {"nombre": "Que ocupacion habra el proximo fin de semana?",
     "desc": "Prediccion de ocupacion"},
    {"nombre": "Cuales son los 3 dias mas fuertes de la prediccion?",
     "desc": "Dias con mayor ocupacion"},
    {"nombre": "Cuando deberia subir las tarifas?",
     "desc": "Recomendacion de precios"},
    {"nombre": "Que eventos y festividades hay este mes?",
     "desc": "Proximos eventos locales"},
    {"nombre": "Cuales son los costes mensuales del hotel?",
     "desc": "Analisis de costes por mes"},
    {"nombre": "Como afecta el Corpus Christi a la ocupacion?",
     "desc": "Impacto de evento especifico"},
    {"nombre": "Que dias estare mas flojo la proxima semana?",
     "desc": "Dias con menor ocupacion"},
    {"nombre": "Cual sera la ocupacion en agosto?",
     "desc": "Pregunta fuera de rango"},
    {"nombre": "Cuanto cuesta una habitacion en la competencia?",
     "desc": "Precio de la combinacion"},
]


# ── Bucle principal ──────────────────────────────────────

print("\n[OK] Asistente listo. Escribe tu pregunta o 'ayuda' para ver ejemplos.\n")

while True:
    try:
        pregunta = input(">>> ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\n\n[FIN] Hasta luego!")
        break

    if not pregunta:
        continue

    pregunta_lower = pregunta.lower()

    # Comandos de salida
    if pregunta_lower in ("salir", "adios", "chao", "exit", "quit", "q"):
        print("\n[i] Hasta luego! Recuerda: revisa la prediccion cada semana.\n")
        break

    # Comando de ayuda
    if pregunta_lower in ("ayuda", "help", "ayudame", "que sabes hacer", "comandos"):
        mostrar_ayuda()
        continue

    # Procesar pregunta
    print()
    try:
        respuesta = responder(pregunta, kb=kb)
        print(respuesta)
        print()
    except Exception as e:
        print(f"\n[FAIL] El asistente encontro un error al procesar tu pregunta.")
        print(f"Detalle: {type(e).__name__}: {e}")
        print("\n[Sugerencia] Prueba a reformular la pregunta o escribe 'ayuda'")
        print("para ver ejemplos de preguntas que entiendo.\n")

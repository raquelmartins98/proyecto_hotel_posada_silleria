"""
volcar_asistente.py — Genera respuestas pre-generadas del asistente RAG
para 6 preguntas típicas y las inserta en la tabla asistente_respuestas
de Insforge via REST API.

Flujo:
  1) Construye base de conocimiento RAG (desde Insforge)
  2) Genera respuesta para cada una de las 6 preguntas
  3) Inserta (upsert) cada pregunta+respuesta en asistente_respuestas
  4) Verifica los datos insertados
"""
import sys
import os
import warnings
from pathlib import Path
from datetime import datetime, timezone

from dotenv import load_dotenv
import requests

warnings.filterwarnings("ignore")

from rag_respuestas import responder, build_knowledge_base

# ── Config ────────────────────────────────────────────────

ENV_PATH = Path(__file__).resolve().parents[1] / "frontend" / ".env"

# API Key de admin (del MCP) para writes
ADMIN_KEY = "ik_371927c198260f2bf08eb13ba70a8d42"

# ── 6 preguntas típicas ──────────────────────────────────

PREGUNTAS = [
    {
        "pregunta": "¿Qué ocupación habrá los próximos días?",
        "categoria": "ocupacion",
        "orden": 1,
    },
    {
        "pregunta": "¿Qué días estaré más flojo?",
        "categoria": "ocupacion",
        "orden": 2,
    },
    {
        "pregunta": "¿Cuándo debería subir las tarifas?",
        "categoria": "precio",
        "orden": 3,
    },
    {
        "pregunta": "¿Qué eventos y festividades hay este mes?",
        "categoria": "evento",
        "orden": 4,
    },
    {
        "pregunta": "¿Cómo afecta el Corpus Christi a la ocupación?",
        "categoria": "evento",
        "orden": 5,
    },
    {
        "pregunta": "¿Cuáles son los costes del hotel?",
        "categoria": "coste",
        "orden": 6,
    },
]

print("=" * 60)
print("VOLCAR ASISTENTE RAG A INSFORGE")
print("=" * 60)

# =====================================================================
#  1. CONECTAR A INSFORGE
# =====================================================================

print("\n[1/4] Conectando con Insforge...", end=" ", flush=True)

load_dotenv(ENV_PATH)
API_URL = os.getenv("VITE_INSFORGE_URL")
ANON_KEY = os.getenv("VITE_INSFORGE_ANON_KEY")

if not API_URL or not ANON_KEY:
    print("[FAIL]")
    print("  Faltan credenciales en frontend/.env")
    sys.exit(1)

BASE = API_URL.rstrip("/")
HEADERS_WRITE = {
    "Authorization": f"Bearer {ADMIN_KEY}",
    "Content-Type": "application/json",
}
HEADERS_READ = {
    "Authorization": f"Bearer {ANON_KEY}",
    "Accept": "application/json",
}

print("[OK]")

# =====================================================================
#  2. CONSTRUIR BASE DE CONOCIMIENTO
# =====================================================================

print("\n[2/4] Construyendo base de conocimiento RAG...", end=" ", flush=True)
try:
    kb = build_knowledge_base(verbose=False)
    print("[OK]")
except Exception as e:
    print(f"[FAIL]\n  Error: {e}")
    sys.exit(1)

# =====================================================================
#  3. GENERAR RESPUESTAS E INSERTAR EN INSFORGE
# =====================================================================

print(f"\n[3/4] Generando {len(PREGUNTAS)} respuestas e insertando en Insforge...")

ahora = datetime.now(timezone.utc).isoformat()

for i, item in enumerate(PREGUNTAS, 1):
    pregunta = item["pregunta"]
    categoria = item["categoria"]
    orden = item["orden"]

    print(f"\n  [{i}/{len(PREGUNTAS)}] \"{pregunta}\"")
    print(f"         Categoría: {categoria}", end="", flush=True)

    # Generar respuesta usando el RAG
    try:
        respuesta_texto = responder(pregunta, kb=kb)
        print(f" — {len(respuesta_texto)} chars", end="", flush=True)
    except Exception as e:
        respuesta_texto = f"[Error al generar respuesta] {type(e).__name__}: {e}"
        print(f" [FAIL] {e}", end="", flush=True)

    # Insertar via REST API POST
    registro = {
        "pregunta": pregunta,
        "respuesta": respuesta_texto,
        "categoria": categoria,
        "orden": orden,
    }

    insert_url = f"{BASE}/api/database/records/asistente_respuestas"
    insert_headers = {
        **HEADERS_WRITE,
        "Prefer": "return=representation",
    }

    try:
        resp = requests.post(
            insert_url, headers=insert_headers, json=[registro], timeout=30
        )
        if resp.status_code in (200, 201):
            print(" [INSERT OK]")
        else:
            print(f" [FAIL] Status {resp.status_code}: {resp.text[:150]}")
    except requests.RequestException as e:
        print(f" [FAIL] Error de conexión: {e}")

print(f"\n  ---")

# =====================================================================
#  4. VERIFICAR DATOS INSERTADOS
# =====================================================================

print(f"\n[4/4] Verificando datos en Insforge...")

try:
    resp_check = requests.get(
        f"{BASE}/api/database/records/asistente_respuestas?order=orden.asc",
        headers=HEADERS_READ,
        timeout=15,
    )
    resp_check.raise_for_status()
    raw = resp_check.json()
    records = raw if isinstance(raw, list) else raw.get("value", [])

    total = len(records)
    print(f"\n  Total filas en tabla asistente_respuestas: {total}")

    if total > 0:
        print(f"\n  {'#':<4} {'Pregunta':<50} {'Categoría':<12} {'Respuesta':<20}")
        print(f"  {'-'*4} {'-'*50} {'-'*12} {'-'*20}")
        for row in records:
            preview = row["respuesta"][:60].replace("\n", " ") + "..."
            print(f"  {row['orden']:<4} {row['pregunta'][:48]:<50} "
                  f"{row['categoria']:<12} {preview:<20}")

        print(f"\n  Primera pregunta:")
        p1 = records[0]
        print(f"    Pregunta: {p1['pregunta']}")
        print(f"    Respuesta: {p1['respuesta'][:200]}...")

    print(f"\n{'=' * 60}")
    print(f"[OK] Asistente RAG volcado a Insforge correctamente.")
    print(f"     Tabla: asistente_respuestas ({total} filas)")
    print(f"{'=' * 60}")

except Exception as e:
    print(f"\n  [FAIL] Error al verificar: {e}")
    sys.exit(1)

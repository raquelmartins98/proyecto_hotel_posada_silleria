"""
test_conexion_insforge.py — Verifica conexion Python -> Insforge API.

Lee las credenciales del .env del frontend y hace una peticion GET
a la tabla ocupacion_real via REST API.
"""
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
import requests

# El .env esta en frontend/.env (raiz del proyecto)
env_path = Path(__file__).resolve().parents[1] / "frontend" / ".env"
if not env_path.exists():
    print(f"[FAIL] No se encuentra .env en: {env_path}")
    sys.exit(1)

load_dotenv(env_path)

API_URL = os.getenv("VITE_INSFORGE_URL")
ANON_KEY = os.getenv("VITE_INSFORGE_ANON_KEY")

if not API_URL or not ANON_KEY:
    print("[FAIL] Faltan VITE_INSFORGE_URL o VITE_INSFORGE_ANON_KEY en el .env")
    sys.exit(1)

# Endpoint REST: GET /api/database/records/{tabla}
url = f"{API_URL.rstrip('/')}/api/database/records/ocupacion_real"
headers = {
    "Authorization": f"Bearer {ANON_KEY}",
    "Accept": "application/json",
}

print(f"Conectando a: {url}")
print(f"Authorization: Bearer {ANON_KEY[:20]}...")

try:
    resp = requests.get(url, headers=headers, timeout=15)
    resp.raise_for_status()
    data = resp.json()
except requests.exceptions.Timeout:
    print("[FAIL] Timeout — el servidor no respondio en 15s")
    sys.exit(1)
except requests.exceptions.RequestException as e:
    print(f"[FAIL] Error de conexion: {e}")
    if hasattr(e, "response") and e.response is not None:
        print(f"  Status: {e.response.status_code}")
        print(f"  Body:   {e.response.text[:500]}")
    sys.exit(1)

# Normalizar: Insforge devuelve { "records": [...] } o directamente [...]
if isinstance(data, dict) and "records" in data:
    records = data["records"]
else:
    records = data if isinstance(data, list) else []

total = len(records)
print(f"\n[OK] Tabla ocupacion_real: {total} filas recibidas")

if total > 0:
    print(f"\n-- Primeras {min(3, total)} fila(s) --")
    for i, row in enumerate(records[:3]):
        print(f"  {i+1}. {row}")
else:
    print("  (sin datos — RLS puede estar bloqueando)")

print("\n[OK] Conexion Python -> Insforge verificada correctamente.")

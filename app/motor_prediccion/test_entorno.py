"""
test_entorno.py -- Verifica que todas las librerias del motor de prediccion
se importan correctamente en el entorno virtual.

NOTA: Sin emojis -- la consola Windows (CP1252) no los soporta.
"""
import sys


LIBRERIAS = [
    ("pandas", "pd"),
    ("numpy", "np"),
    ("statsmodels.api", None),
    ("statsmodels.tsa.arima.model", None),
    ("statsmodels.tsa.statespace.sarimax", None),
    ("pmdarima", None),
    ("matplotlib", "mpl"),
    ("matplotlib.pyplot", "plt"),
    ("sklearn.metrics", None),
    ("requests", None),
    ("dotenv", None),
]

errores = []

for modulo, alias in LIBRERIAS:
    try:
        lib = __import__(modulo)
        if alias:
            globals()[alias] = lib
        version = getattr(lib, "__version__", "?")
        print(f"  [OK] {modulo:<40} -- v{version}")
    except Exception as e:
        errores.append((modulo, str(e)))
        print(f"  [FAIL] {modulo:<40} -- {e}")

print(f"\nPython {sys.version}")
print(f"Plataforma: {sys.platform}")

# Resumen

print("\n" + "=" * 50)
if errores:
    print(f"[FAIL] FALLARON {len(errores)} importacion(es):")
    for mod, err in errores:
        print(f"   - {mod}: {err}")
    sys.exit(1)
else:
    print(f"[OK] TODAS las {len(LIBRERIAS)} librerias importadas correctamente")
    print("    Entorno listo para construir modelos.")
    sys.exit(0)

# Posada Revenue — Sistema de Revenue Management

**Hotel Posada de la Sillería (Toledo, España)**

Sistema de pricing dinámico, break-even y simulación financiera para hotelería boutique.

## Instalación

```bash
cd posada_revenue
pip install -e .
pip install -e ".[dev]"     # + herramientas de desarrollo
pip install -e ".[dashboard]"  # + dashboard Streamlit
```

## Uso rápido

```bash
# Inicializar base de datos y cargar configuración
posada init

# Ver categorías de habitación
posada rooms list

# Calcular precio para una fecha concreta
posada price compute --date 2026-06-04 --room "suite"

# Simular un año completo
posada simulate --from 2026-01-01 --to 2026-12-31 --target-margin 0.30

# Generar reporte mensual en Excel
posada report monthly --month 2026-06 --output excel

# Calcular payback de una inversión
posada roi --investment 850000 --horizon-months 120
```

## Arquitectura

```
┌──────────────────────────────────────────────────────────┐
│                        CLI (Typer)                        │
│              posada init | simulate | report | roi        │
└──────────┬──────────────────────────────────┬──────────────┘
           │                                  │
    ┌──────▼──────┐                  ┌───────▼────────┐
    │    io/       │                  │    engine/      │
    │  db.py       │                  │  breakeven.py   │
    │  importers.py│ ◄──────────────► │  marginal_cost  │
    │  reporters.py│     pydantic     │  dynamic_pricing│
    └──────┬──────┘     models       │  roi.py         │
           │                          │  profit_alloc   │
    ┌──────▼──────┐                  └───────▲─────────┘
    │  SQLite     │                          │
    │  (sqlmodel) │                puro cálculo sin I/O
    └─────────────┘
```

**Regla de arquitectura:** `engine/` es código **puro** — funciones sin efectos secundarios,
sin tocar BD ni ficheros. Esto permite testear los cálculos de forma aislada.

## Líneas de negocio

- **Alojamiento** (núcleo del modelo, 4 categorías de habitación)
- **Restauración** (desayunos + servicio a la carta)
- **Eventos privados** (bodas íntimas, reuniones corporativas)

## Configuración

Los ficheros `config/*.json` son editables por el usuario:

| Fichero | Propósito |
|---------|-----------|
| `hotel_config.json` | Inventario de habitaciones, líneas de negocio |
| `costs_baseline.json` | Costes fijos y variables |
| `seasonality_toledo.json` | Calendario estacional y coeficientes |

Ejecutar `posada reload` para recargar los cambios.

## Tests

```bash
pytest              # Ejecutar todos los tests
pytest --cov-report=html  # Reporte de cobertura HTML
pytest -k "test_1"  # Test específico
```

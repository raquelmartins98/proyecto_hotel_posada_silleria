# Modelo Predictivo de Revenue Management
## Hotel Posada de la Sillería — Toledo

Sistema completo de optimización de precios dinámicos, análisis de rentabilidad y
proyección de ocupación para hotel boutique en el casco histórico de Toledo.

---

## Arquitectura del Sistema

```
revenue_engine/
├── engine/               → Motores de cálculo (core del algoritmo)
│   ├── cost_engine.py        → Motor de costes fijos y variables
│   ├── elasticity.py         → Elasticidad precio-demanda segmentada
│   ├── seasonal.py           → Coeficientes estacionales Toledo
│   ├── ota.py               → Modelo de comisiones OTA y canales
│   ├── breakeven.py          → Punto de equilibrio y márgenes
│   ├── roi_calculator.py     → ROI, payback y rentabilidad
│   ├── profit_distribution.py→ Reparto homogéneo entre líneas
│   ├── booking_pace.py       → Forecasting por ritmo de reservas
│   ├── pricing_engine.py     → Orquestador principal
│   └── smoothing.py          → Suavizado de cambios de precio
├── api/                  → FastAPI REST endpoints
│   ├── app.py               → Configuración de la aplicación
│   └── routes.py            → Endpoints REST
├── dashboard/            → Streamlit dashboard interactivo
│   └── app.py               → Panel de control y simulación
├── models.py             → Pydantic models / dataclasses
├── config.py             → Configuración global
└── toledo_calendar.py    → Calendario turístico de Toledo
```

## Stack Tecnológico

| Componente | Tecnología |
|-----------|------------|
| Lenguaje | Python 3.12+ |
| API REST | FastAPI + Uvicorn |
| Dashboard | Streamlit |
| Datos | Pandas + NumPy |
| Modelos de dominio | `@dataclass` |
| Validación API | Pydantic `BaseModel` |
| Testing | pytest |
| Persistencia | JSON + SQLAlchemy (SQLite opcional) |

## Instalación Rápida

```bash
# Clonar el repositorio
git clone https://github.com/raquelmartins98/proyecto_hotel_posada_silleria.git
cd proyecto_hotel_posada_silleria/modelo-predictivo-revenue

# Crear entorno virtual
python -m venv .venv
.venv\Scripts\activate   # Windows
# source .venv/bin/activate  # Linux/Mac

# Instalar dependencias
pip install -r requirements.txt

# Ejecutar demo de simulación completa
python -m revenue_engine.engine.pricing_engine

# Iniciar API REST
python run_api.py

# Iniciar Dashboard
python run_dashboard.py
```

## Endpoints de la API

| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/api/v1/simulate` | Simulación completa de pricing |
| POST | `/api/v1/prices/daily` | Precios dinámicos para un rango de fechas |
| POST | `/api/v1/breakeven` | Cálculo de punto de equilibrio |
| POST | `/api/v1/roi` | Proyección de ROI y payback |
| GET  | `/api/v1/seasonality` | Matriz de coeficientes estacionales |
| POST | `/api/v1/booking-pace` | Proyección por booking pace |
| POST | `/api/v1/report/csv` | Exportar reporte mensual a CSV |
| POST | `/api/v1/report/excel` | Exportar reporte completo a Excel |

## Simulación Rápida desde Python

```python
from revenue_engine.models import HotelConfig, SimulationInput
from revenue_engine.engine.pricing_engine import RevenueManager

# Cargar configuración del hotel
config = HotelConfig.from_seed("posada_silleria")

# Ejecutar simulación
manager = RevenueManager(config)
result = manager.run_simulation(
    occupancy=0.75,
    target_margin=20.0,
    target_roi=15.0,
    total_investment=1_200_000,
)

print(result.executive_summary())
```

## Estructura del Proyecto

```
modelo-predictivo-revenue/
├── revenue_engine/        → Código fuente del motor
├── data/seed/             → Datos semilla del hotel
├── tests/                 → Tests unitarios
├── notebooks/             → Jupyter notebooks de análisis
├── docs/                  → Documentación técnica
├── run_api.py             → Script para lanzar API
├── run_dashboard.py       → Script para lanzar dashboard
├── requirements.txt       → Dependencias
├── pyproject.toml         → Configuración del proyecto
└── README.md              → Este archivo
```

## Autor

Desarrollado como parte del sistema de gestión hotelera para la
**Posada de la Sillería** — Toledo, España.

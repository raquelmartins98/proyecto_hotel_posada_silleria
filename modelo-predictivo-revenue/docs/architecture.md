# Revenue Management Engine

## Arquitectura del Sistema

### Principios de Diseño

1. **Separación de Responsabilidades**: Cada submotor (costes, elasticidad, estacionalidad, etc.)
   es independiente y testable por separado.

2. **Orquestador Único**: `RevenueManager` coordina todos los submotores.
   No hay lógica de negocio duplicada.

3. **Datos de Configuración vs. Datos de Ejecución**:
   - `HotelConfig`: datos estáticos del hotel (categorías, costes, inversión)
   - `SimulationInput`: parámetros dinámicos de cada simulación

4. **Inmutabilidad**: Los resultados de simulación son objetos inmutables
   que no modifican el estado del motor.

### Flujo de Datos

```
Input (ocupación, margen, ROI)
    │
    ▼
┌─────────────────────────────────────────┐
│  RevenueManager.run_simulation()        │
│                                         │
│  1. CostEngine.calculate()              │
│     → Asigna costes fijos y variables   │
│     → Precios base por categoría        │
│                                         │
│  2. BreakEvenEngine.breakeven_report()  │
│     → Punto de equilibrio               │
│                                         │
│  3. ROICalculator.calculate()           │
│     → ROI, Payback, EVA                 │
│                                         │
│  4. ProfitDistribution.distribute()     │
│     → Reparto homogéneo                 │
│                                         │
│  5. SeasonalEngine.generate_prices()    │
│     → Precios dinámicos anuales         │
│                                         │
│  6. PricingEngine.apply_all()           │
│     → Corrección por BVI + smoothing    │
│                                         │
│  → SimulationResult                     │
└─────────────────────────────────────────┘
```

### Stack Tecnológico

```
Python 3.14
├── FastAPI + Uvicorn    → API REST
├── Streamlit + Plotly   → Dashboard
├── Pandas + NumPy       → Procesamiento de datos
└── Pydantic             → Validación de modelos
```

### Estructura de Directorios

```
revenue_engine/
├── engine/              → Lógica de negocio (core)
│   ├── cost_engine.py      → Motor de costes
│   ├── elasticity.py       → Elasticidad precio-demanda
│   ├── seasonal.py         → Ajuste estacional
│   ├── ota.py             → Modelo OTA y canales
│   ├── breakeven.py        → Break-even
│   ├── roi_calculator.py   → ROI y payback
│   ├── profit_distribution.py → Reparto homogéneo
│   ├── booking_pace.py     → Booking pace forecasting
│   ├── pricing_engine.py   → Orquestador principal
│   └── smoothing.py        → Suavizado de precios
│
├── api/                 → FastAPI endpoints
│   ├── routes.py
│   └── app.py
│
├── dashboard/           → Streamlit UI
│   └── app.py
│
├── models.py            → Pydantic/dataclass models
├── config.py            → Configuración global
└── toledo_calendar.py   → Calendario turístico de Toledo
```

### Fórmulas Clave Implementadas

| Fórmula | Expresión | Módulo |
|---------|-----------|--------|
| Coste Marginal | MC = VC + FC × sigmoid(occ) | cost_engine |
| Precio Óptimo (Lerner) | P* = MC / (1 + 1/ε) | elasticity |
| Break-Even Ocupación | BE_occ = FC / Σ(Price - VC) × rooms × days | breakeven |
| ROI | ROI = NetProfit / Investment × 100 | roi_calculator |
| Payback | Payback = Investment / AnnualProfit | roi_calculator |
| EVA | EVA = NetProfit - (Capital × WACC) | roi_calculator |
| Booking Velocity Index | BVI = ActualPickup / ExpectedPickup | booking_pace |
| Coste Marginal Dinámico | MC = VC + FC × 1/(1+e^(-slope(occ-mid))) | cost_engine |

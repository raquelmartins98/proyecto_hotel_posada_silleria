# 🏨 Hotel Boutique Posada de la Sillería — Revenue Management System

Sistema de **Revenue Management** para el **Hotel Boutique Posada de la Sillería** (Toledo, España). Combina un panel de administración web, un motor de predicción de ocupación multi-modelo y un reporte financiero en Power BI para la toma de decisiones basada en datos.

---

## 📂 Estructura del proyecto

```
proyecto_hotel_posada_silleria/
├── app/                          ← Código principal
│   ├── frontend/                 ← Panel administración React + Vite + Tailwind
│   │   ├── src/pages/            ← 7 secciones: Dashboard, Ocupación, Predicción,
│   │   │                           Reservas, Costes, Festividades, Competencia, Tiempo
│   │   └── src/lib/insforge.js   ← Cliente REST para backend Insforge
│   ├── motor_prediccion/         ← Motor Python de predicción de ocupación
│   │   ├── modelo_sarima.py      ← SARIMA con estacionalidad semanal
│   │   ├── modelo_arima.py       ← ARIMA baseline
│   │   ├── modelo_holtwinters.py ← Holt-Winters (rápido para dashboard)
│   │   ├── ensemble.py           ← Ensemble ponderado de los 3 modelos
│   │   ├── escenarios.py         ← 3 escenarios: Pesimista, Realista, Optimista
│   │   ├── rag_base.py           ← Asistente RAG con datos reales del hotel
│   │   └── graficas/             ← Gráficas comparativas de modelos
│   └── src/                      ← Backend Python (arquitectura limpia, en desarrollo)
└── informes/                     ← Reporte financiero Power BI
    ├── data/                     ← Datos del modelo (7 tablas CSV)
    ├── docs/                     ← Documentación DAX, alertas, guías
    └── scripts/                  ← Scripts de generación de datos
```

---

## 🧠 Motor de predicción

El motor entrena **4 modelos** sobre 365 días de ocupación histórica real:

| Modelo | MAE | Descripción |
|--------|-----|-------------|
| SARIMA(2,1,1)(1,0,2,7) | **8.13%** | Captura estacionalidad semanal (mejor precisión) |
| Holt-Winters Add-Add | 11.05% | Entrenamiento instantáneo, ideal para dashboard |
| ARIMA(5,1,2) | 12.96% | Baseline sin estacionalidad |
| Ensemble ponderado | 9.55% | Combinación de los 3 modelos |

Genera **3 escenarios** a 30 días: Pesimista (~38%), Realista (~67%), Optimista (~91%) con intervalos de confianza del 95%.

Incluye un **Asistente RAG** que responde preguntas en lenguaje natural sobre ocupación, precios, eventos y costes, cruzando datos de Insforge + predicción SARIMA.

---

## 🛠️ Tecnologías

| Capa | Tecnologías |
|------|-------------|
| **Frontend** | React 19, Vite, Tailwind CSS 4, Recharts, React Router |
| **Backend datos** | Insforge (PostgreSQL + REST API + RLS) |
| **Motor Python** | Python 3.14, statsmodels, pmdarima, pandas, scikit-learn |
| **BI** | Power BI (.pbip), DAX, modelo semántico |
| **Diseño** | Stitch, sistema de diseño propio (Gold #b8860b, Brown #3e2c1c) |

---

## 🚀 Cómo arrancar el frontend

```bash
cd app/frontend
npm install
npm run dev
```

El panel se abre en `http://localhost:5173` (o el puerto que asigne Vite).

---

## 📊 Reporte Power BI

El proyecto `informes/` contiene un reporte Power BI con:
- 7 tablas de datos (DimAccount, DimAlerts, DimDate, DimDepartment, DimRoomStats, FactActuals, FactBudget)
- Medidas DAX para KPI financieros
- Alertas configurables de rendimiento
- Guía completa en `informes/docs/REPORT-GUIDE.md`

Abrir el archivo `informes/PosadaDeSilleria.pbip/PosadaDeSilleria.Report/definition.pbir` en Power BI Desktop.

---

## 📌 Estado del proyecto

- ✅ Backend Insforge: 9 tablas, RLS activado, datos sintéticos 12 meses
- ✅ Frontend: 7 páginas funcionales conectadas a Insforge vía REST
- ✅ Motor de predicción: 4 modelos, 3 escenarios, asistente RAG
- 🔄 Backend `src/`: arquitectura limpia parcial — pendientes breakeven, pricing dinámico, ROI, CLI
- 🔄 Tests: pendientes de implementar

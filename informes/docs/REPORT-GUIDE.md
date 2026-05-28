# Guía del Reporte Power BI — Cierre Mensual Financiero
## Hotel Boutique Posada de Sillería · Toledo

---

## Índice
1. [Modelo de Datos](#1-modelo-de-datos)
2. [Página 1 — Executive Dashboard](#2-página-1--executive-dashboard)
3. [Página 2 — Revenue Deep Dive](#3-página-2--revenue-deep-dive)
4. [Página 3 — Expense & Cost Control](#4-página-3--expense--cost-control)
5. [Página 4 — Profitability & GOP Bridge](#5-página-4--profitability--gop-bridge)
6. [Página 5 — Alerts & Narrativa](#6-página-5--alerts--narrativa)
7. [Formato Condicional y Temas](#7-formato-condicional-y-temas)
8. [Configuración de Relaciones](#8-configuración-de-relaciones)

---

## 1. Modelo de Datos

### Esquema Estrella (Star Schema)

```
                          ┌─────────────┐
                          │   DimDate    │
                          ├─────────────┤
                          │ DateKey (PK)│◄────┐
                          │ Year        │     │
                          │ MonthNumber │     │
                          │ MonthName   │     │
                          │ Quarter     │     │
                          │ Estacion    │     │
                          │ IsTemporada-│     │
                          │ Alta        │     │
                          └─────────────┘     │
                                              │
┌──────────────┐    ┌──────────────────┐      │
│  DimAccount   │    │  FactActuals     │      │
├──────────────┤    ├──────────────────┤      │
│ AccountKey PK│───►│ DateKey (FK)     ├──────┘
│ AccountCode   │    │ AccountKey (FK)  │◄────┐
│ AccountName   │    │ DepartmentKey(FK)│     │
│ AccountType   │    │ Amount           │     │
│ FinancialClass│    │ Scenario         │     │
│ IsRevenue     │    │ Version          │     │
│ IsExpense     │    └──────────────────┘     │
└──────────────┘                              │
                                              │
┌──────────────┐    ┌──────────────────┐      │
│ DimDepartment │    │  FactBudget      │      │
├──────────────┤    ├──────────────────┤      │
│ DeptKey PK   │───►│ DateKey (FK)     ├──────┘
│ DeptCode      │    │ AccountKey (FK)  │◄────┐
│ DeptName      │    │ DepartmentKey(FK)│     │
│ IsRevenue-    │    │ Amount           │     │
│   Center      │    │ Scenario         │     │
│ Color         │    └──────────────────┘     │
└──────────────┘                              │
                                              │
┌──────────────┐    ┌──────────────────┐      │
│ DimRoomStats  │    │  DimAlerts       │      │
├──────────────┤    ├──────────────────┤      │
│ DateKey (FK) ├────┘ │ AlertCode (PK)  │      │
│ ADR_Actual    │    │ AlertName        │      │
│ ADR_Budget    │    │ Severity         │      │
│ Ocupacion_    │    │ Threshold        │      │
│   Actual      │    │ MetricName       │      │
│ RevPAR_Actual │    └──────────────────┘      │
└──────────────┘                               │
```

### Relaciones (Configurar en Power BI)

| Desde | Hasta | Cardinalidad | Dirección de Filtro |
|-------|-------|-------------|---------------------|
| DimDate[DateKey] | FactActuals[DateKey] | 1:N | Simple |
| DimDate[DateKey] | FactBudget[DateKey] | 1:N | Simple |
| DimDate[DateKey] | DimRoomStats[DateKey] | 1:1 | Simple |
| DimAccount[AccountKey] | FactActuals[AccountKey] | 1:N | Simple |
| DimAccount[AccountKey] | FactBudget[AccountKey] | 1:N | Simple |
| DimDepartment[DepartmentKey] | FactActuals[DepartmentKey] | 1:N | Simple |
| DimDepartment[DepartmentKey] | FactBudget[DepartmentKey] | 1:N | Simple |

> ⚠️ **IMPORTANTE**: Crear una **tabla de fechas desconectada** o marcar DimDate como tabla de fechas.
> En Power BI: click derecho en DimDate → "Marcar como tabla de fechas" → columna DateKey.

### Estrategia de Actualización

- **FactActuals**: Sobrescritura completa cada mes (240 filas)
- **FactBudget**: Carga inicial anual (240 filas), solo se modifica si hay revisión presupuestaria
- **DimRoomStats**: Actualización mensual con datos de PMS (Property Management System)
- **Dimensiones**: Estables, actualización bajo demanda

---

## 2. Página 1 — Executive Dashboard

### Objetivo
Visión global del mes: ¿Cómo le fue al hotel? El CFO debe entender la situación en <5 segundos.

### Layout (Landscape - 1920x1080)

```
┌──────────────────────────────────────────────────────────────────────┐
│  🏨 POSADA DE SILLERÍA · CIERRE MENSUAL          📅 [Segmentación]  │
├──────────────────────────────────────────────────────────────────────┤
│ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌───────────────┐  │
│ │ Revenue  │ │ Revenue │ │  GOP    │ │  GOP    │ │   Alertas     │  │
│ │ Actual   │ │ Var %   │ │ Actual  │ │ Margin  │ │  🔴 2 🟡 1    │  │
│ │ €95.340  │ │  -3.2%  │ │ €15.340 │ │  16.1%  │ │               │  │
│ └─────────┘ └─────────┘ └─────────┘ └─────────┘ │ Revenue:  🟡  │  │
├──────────────────────────────────────────────────┤ OpEx:     🟢  │  │
│ ┌───────────────────┐ ┌──────────────────────────┤ GOP:      🔴  │  │
│ │ Revenue Trend     │ │  GOP vs Budget           │ Ocupación: 🟢  │  │
│ │ (Líneas: Actual   │ │  (Columnas agrupadas)    │               │  │
│ │  vs Budget)       │ │  Actual | Budget | Var%  │               │  │
│ │                   │ │                          └───────────────┘  │
│ └───────────────────┘ └─────────────────────────────────────────────│
├──────────────────────────────────────────────────────────────────────┤
│ ┌──────────────────────┐ ┌────────────────┐ ┌──────────────────────┐│
│ │ Revenue Mix (Donut)  │ │ KPIs Hotel     │ │ Top Alertas          ││
│ │ Rooms: 68%           │ │ Ocu: 83.2%     │ │ ⚠ GOP Margin -5.2%  ││
│ │ F&B:   22%           │ │ ADR: €234.50   │ │ ⚠ Rev -3.2% vs Bgt  ││
│ │ Spa:    6%           │ │ RevPAR: €194.20│ │                      ││
│ │ Eventos: 4%          │ │                │ │                      ││
│ └──────────────────────┘ └────────────────┘ └──────────────────────┘│
└──────────────────────────────────────────────────────────────────────┘
```

### Visuales Específicos

| Visual | Tipo | Campos |
|--------|------|--------|
| Revenue Actual | **Card** (KPI) | `[Total Revenue]` — Formato: € #,##0 |
| Revenue Var % | **Card** (KPI) | `[Revenue Variance %]` — Formato: 0.0%; +0.0%; -0.0% |
| GOP Actual | **Card** (KPI) | `[GOP]` — Formato: € #,##0 |
| GOP Margin | **Card** (KPI) | `[GOP Margin]` — Formato: 0.0% |
| Revenue Trend | **Line Chart** | Eje X: DimDate[MonthName]; Líneas: `[Total Revenue]`, `[Total Revenue Budget]` |
| GOP vs Budget | **Clustered Column Chart** | Eje X: DimDate[MonthName]; Valores: `[GOP]`, `[GOP Budget]` |
| Revenue Mix | **Donut Chart** | Leyenda: DimDepartment[DepartmentName]; Valores: `[Total Revenue]` |
| KPIs Hotel | **Multi-row Card** | `[Occupancy % Actual]`, `[ADR Actual]`, `[RevPAR Actual]` |
| Alertas | **Card** con formato condicional | `[Alert Count]` |
| Top Alertas | **Table** | AlertCode, AlertName, Severity (con iconos) |

### Formato Condicional (Crítico)

**Revenue Var % Card:**
- Valor < -10% → Fondo ROJO, icono 🔴
- Entre -10% y -5% → Fondo ÁMBAR, icono 🟡
- Entre -5% y 0% → Fondo NARANJA CLARO
- >= 0% → Fondo VERDE, icono 🟢

*Configurar en "Formato > Formato condicional > Color de fondo" con reglas.*

---

## 3. Página 2 — Revenue Deep Dive

### Objetivo
Análisis granular de ingresos: ¿Qué departamento está impulsando o lastrando el resultado?

### Layout

```
┌──────────────────────────────────────────────────────────────────────┐
│  💰 ANÁLISIS DE INGRESOS                    📅 [Seg. mes] [Depto]   │
├──────────────────────────────────────────────────────────────────────┤
│ ┌──────────────────────────────────────────────────────────────────┐ │
│ │ Revenue por Departamento (Actual vs Budget)                      │ │
│ │ ██ ROOMS:  €62,262 vs €64,800  ▼ -3.9%                          │ │
│ │ ██ F&B:    €19,850 vs €20,100  ▼ -1.2%                          │ │
│ │ ██ SPA:    €5,432  vs €5,800   ▼ -6.3%                          │ │
│ │ ██ EVENTS: €7,896  vs €7,200   ▲ +9.7%                          │ │
│ │ (Barra horizontal apilada con variance %)                        │ │
│ └──────────────────────────────────────────────────────────────────┘ │
├─────────────────┬────────────────────┬───────────────────────────────┤
│ ┌─────────────┐│ ┌─────────────────┐│ ┌───────────────────────────┐ │
│ │ ADR Trend   ││ │ Occupancy Trend ││ │ Revenue Waterfall         │ │
│ │ (Línea:     ││ │ (Líneas:        ││ │ (Month-over-Month)        │ │
│ │ Actual vs   ││ │ Actual vs Bgt)  ││ │ ▲ Rooms: +€2,340         │ │
│ │ Budget)     ││ │                 ││ │ ▼ F&B:   -€1,200         │ │
│ │             ││ │                 ││ │ ▲ Events: +€4,500         │ │
│ └─────────────┘│ └─────────────────┘│ └───────────────────────────┘ │
├────────────────┴────────────────────┴───────────────────────────────┤
│ ┌──────────────────────────────────────────────────────────────────┐ │
│ │ Desglose Mensual - Revenue por Departamento (100% Stacked Bar)   │ │
│ │ Muestra cómo cambia el mix de ingresos mes a mes                │ │
│ └──────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────┘
```

### Visuales Específicos

| Visual | Tipo | Detalle |
|--------|------|---------|
| Revenue por Depto | **Bar Chart** | Eje Y: DimDepartment[DepartmentName], Valor: `[Total Revenue]` y `[Total Revenue Budget]`. Añadir etiqueta de data con `[Revenue Variance %]` |
| ADR Trend | **Line Chart** | Eje X: DimDate[MonthName], Valores: `[ADR Actual]`, `[ADR Budget]`. Formato eje Y: € |
| Occupancy Trend | **Line Chart** | Eje X: DimDate[MonthName], Valores: `[Occupancy % Actual]`, `[Occupancy % Budget]`. Formato: 0% |
| Revenue Waterfall | **Waterfall Chart** | Categoría: DimDepartment[DepartmentName], Valor: `[Revenue Variance]` (mes seleccionado). Desglosa qué departamento aporta/cae |
| Mix Mensual | **100% Stacked Column Chart** | Eje X: DimDate[MonthName], Valores: `[Revenue Rooms]`, `[Revenue F&B]`, `[Revenue Spa]`, `[Revenue Events]` |

### Interacciones (Recomendado)

- Segmentación de mes afecta toda la página
- Segmentación de departamento (segmentación en la parte superior) filtra Revenue por Depto y Waterfall
- Al seleccionar un mes en Revenue Trend, se resalta en Mix Mensual

---

## 4. Página 3 — Expense & Cost Control

### Objetivo
Control de gastos: ¿Dónde estamos gastando de más? Semáforo por cuenta contable.

### Layout

```
┌──────────────────────────────────────────────────────────────────────┐
│  💸 CONTROL DE GASTOS                          📅 [Seg. mes]        │
├──────────────────────────────────────────────────────────────────────┤
│ ┌─────────────────┐ ┌─────────────────┐ ┌──────────────────────────┐│
│ │ Total OpEx      │ │ OpEx Var %      │ │ Payroll % Revenue       ││
│ │ €79,240         │ │ +4.2%  🟡       │ │ 38.5% (Bgt: 36.0%)  🟡 ││
│ └─────────────────┘ └─────────────────┘ └──────────────────────────┘│
├──────────────────────────────────────────────────────────────────────┤
│ ┌──────────────────────────────────────────────────────────────────┐ │
│ │ OpEx Treemap - Gastos por Categoría                              │ │
│ │ ┌─────────────────┐ ┌─────────┐ ┌──────────┐                   │ │
│ │ │  Personal       │ │Limpeza  │ │Marketing │                   │ │
│ │ │  €38,500 (48.6%)│ │€5,200   │ │€4,100    │                   │ │
│ │ │  🟡 +4.1% vs    │ │🟢 +1.2% │ │🔴 +12.3% │                   │ │
│ │ │  Budget         │ │         │ │          │                   │ │
│ │ └─────────────────┘ └─────────┘ └──────────┘                   │ │
│ │ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐          │ │
│ │ │ COGS F&B │ │  OTAs    │ │Utilities │ │ Admin    │          │ │
│ │ │ €6,800   │ │ €9,340   │ │€2,800    │ │€2,500    │          │ │
│ │ └──────────┘ └──────────┘ └──────────┘ └──────────┘          │ │
│ └──────────────────────────────────────────────────────────────────┘ │
├──────────────────────────────────────────────────────────────────────┤
│ ┌────────────────────────────────────┬──────────────────────────────┐│
│ │ OpEx Trend (Actual vs Budget)     │ Expense Variance Table       ││
│ │ (Line Chart con monthly break)    │ Cuenta | Actual | Bgt | Var% ││
│ │                                   │ Personal| 38.5K | 36.9K|+4.1%││
│ │                                   │ Limpieza| 5.2K  | 5.1K |+2.0%││
│ └────────────────────────────────────┴──────────────────────────────┘│
└──────────────────────────────────────────────────────────────────────┘
```

### Visuales Específicos

| Visual | Tipo | Detalle |
|--------|------|---------|
| OpEx Treemap | **Treemap** | Grupo: DimAccount[AccountName]; Valor: `[Total OpEx]`. Color por `[OpEx Variance %]` (gradiente rojo-verde) |
| OpEx Trend | **Line Chart** | Eje X: DimDate[MonthName]; Valores: `[Total OpEx]`, `[Total OpEx Budget]` |
| Expense Variance Table | **Table** | Columnas: DimAccount[AccountName], `[Total OpEx]`, `[Total OpEx Budget]`, `[OpEx Variance %]`. **Barra de datos** en columna Variance % |
| Payroll % Revenue | **Gauge** | Valor: `[Payroll % Revenue]`, Objetivo: 0.36. Mín: 0.30, Máx: 0.45 |
| Food Cost % | **Gauge** | Valor: `[Food Cost %]`, Objetivo: 0.33. Mín: 0.25, Máx: 0.40 |

### Formato Condicional en Tabla

**Columna OpEx Variance %:**
- < 0% → icono ✅ verde (vamos mejor que presupuesto)
- 0% a 5% → icono ⚠️ ámbar (ligera desviación)
- > 5% → icono 🚫 rojo (sobrecoste significativo)

---

## 5. Página 4 — Profitability & GOP Bridge

### Objetivo
¿Estamos siendo rentables? Análisis de GOP, márgenes y EBITDA.

### Layout

```
┌──────────────────────────────────────────────────────────────────────┐
│  📈 RENTABILIDAD                            📅 [Seg. mes]           │
├──────────────────────────────────────────────────────────────────────┤
│ ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────────────┐│
│ │  GOP       │ │ GOP Margin │ │  EBITDA    │ │ EBITDA Margin      ││
│ │  €16,135   │ │  16.1%     │ │  €11,685   │ │ 11.7%              ││
│ │  Bgt:18,761│ │  Bgt:17.4% │ │  Bgt:14,311│ │ Bgt:13.3%          ││
│ └────────────┘ └────────────┘ └────────────┘ └────────────────────┘│
├──────────────────────────────────────────────────────────────────────┤
│ ┌──────────────────────────────────────────────────────────────────┐ │
│ │ GOP Bridge - Waterfall Chart                                    │ │
│ │                                                                │ │
│ │  €18,761                                                        │ │
│ │    │                                                            │ │
│ │    │  ▼ Rooms  ▼ F&B    ▲ OpEx   ▲ Payroll   ▲ COGS            │ │
│ │    │  -€1,200  -€800   +€900   +€1,100     +€600              │ │
│ │    │                                                            │ │
│ │  €15,340 ← GOP Actual                                          │ │
│ │                                                                │ │
│ │  [GOP Budget] → [Revenue Var] → [COGS Var] → [OpEx Var] → GOP │ │
│ └──────────────────────────────────────────────────────────────────┘ │
├──────────────────────────────────────────────────────────────────────┤
│ ┌───────────────────────────────────┬──────────────────────────────┐│
│ │ Monthly GOP Trend                │ Income Statement Table       ││
│ │ (Columnas: GOP, GOP Budget       │ Concepto     | Actual | Bgt  ││
│ │  Línea: GOP Margin %)            │ Revenue      | 107.7K|107.7K ││
│ │                                  │ - OpEx       |  -91.6K|-89.9K││
│ │                                  │ = GOP        | 16.1K | 18.8K ││
│ │                                  │ - Fixed      |  -4.5K| -4.5K ││
│ │                                  │ = EBITDA     | 11.7K | 14.3K ││
│ │                                  │ - NonOp      |  -6.0K| -6.0K ││
│ │                                  │ = Net Result |  5.7K |  8.3K ││
│ └───────────────────────────────────┘ └────────────────────────────┘│
└──────────────────────────────────────────────────────────────────────┘
```

### Visual "Income Statement"

Este visual es una **Matrix** con diseño personalizado:

| Filas (jerarquía) | Columnas | Valores |
|-------------------|----------|---------|
| Indicador (grupo de cuentas) | Scenario (Actual, Budget) | Sum of Amount |

Crear una **tabla calculada** para la jerarquía del P&L:

```dax
P&L Hierarchy = 
DATATABLE(
    "RowOrder", INTEGER,
    "Section", STRING,
    "DisplayName", STRING,
    "AccountFilter", STRING,
    {
        {1, "Revenue", "📊 INGRESOS OPERATIVOS", "REVENUE"},
        {2, "Revenue", "  · Habitaciones", "ROOMS"},
        {3, "Revenue", "  · Restaurante & Bar", "FNB"},
        {4, "Revenue", "  · Spa", "SPA"},
        {5, "Revenue", "  · Eventos", "EVENTS"},
        {6, "Revenue", "  · Otros Ingresos", "OTHER"},
        {7, "COGS", "📦 COSTES DIRECTOS", "COGS"},
        {8, "COGS", "  · Food Cost", "F&B COGS"},
        {9, "COGS", "  · Productos Spa", "SPA COGS"},
        {10, "COGS", "  · Comisiones OTAs", "OTA COMS"},
        {11, "GrossMargin", "📏 MARGEN BRUTO", "GROSS_MARGIN"},
        {12, "OpEx", "⚙️ GASTOS OPERATIVOS", "OPEX"},
        {13, "OpEx", "  · Personal", "PAYROLL"},
        {14, "OpEx", "  · Limpieza y Lavandería", "CLEANING"},
        {15, "OpEx", "  · Suministros", "SUPPLIES"},
        {16, "OpEx", "  · Marketing", "MARKETING"},
        {17, "OpEx", "  · Mantenimiento", "MAINTENANCE"},
        {18, "OpEx", "  · Servicios Públicos", "UTILITIES"},
        {19, "OpEx", "  · Administración", "ADMIN"},
        {20, "OpEx", "  · Varios", "MISC"},
        {21, "GOP", "💰 GOP (Gross Operating Profit)", "GOP"},
        {22, "Fixed", "🏛️ GASTOS FIJOS", "FIXED"},
        {23, "Fixed", "  · Seguros y Licencias", "INSURANCE"},
        {24, "EBITDA", "📈 EBITDA", "EBITDA"},
        {25, "NonOp", "📉 GASTOS NO OPERATIVOS", "NONOP"},
        {26, "NonOp", "  · Depreciación", "DEPRECIATION"},
        {27, "NonOp", "  · Gastos Financieros", "FINANCIAL"},
        {28, "NetResult", "✅ RESULTADO NETO", "NET_RESULT"}
    }
)
```

---

## 6. Página 5 — Alerts & Narrativa

### Objetivo
Alertas automáticas + comentarios narrativos para la reunión del comité financiero.

### Layout

```
┌──────────────────────────────────────────────────────────────────────┐
│  ⚠️ ALERTAS Y NARRATIVA                       📅 [Seg. mes]        │
├──────────────────────────────────────────────────────────────────────┤
│ ┌──────────────────────────────────────────────────────────────────┐ │
│ │  🔴 ALERTAS CRÍTICAS (2)                                       │ │
│ │  ┌─────────────────────────────────────────────────────────┐   │ │
│ │  │ 🚨 GOP Margin 5.2% por debajo de objetivo (16.1% vs    │   │ │
│ │  │      objetivo 17.4%) — impacto estimado: -€2,626       │   │ │
│ │  │ 🚨 EBITDA 18.4% por debajo de presupuesto — requiere   │   │ │
│ │  │      revisión de estructura de costes fijos             │   │ │
│ │  └─────────────────────────────────────────────────────────┘   │ │
│ │                                                               │ │
│ │  🟡 ALERTAS DE ADVERTENCIA (1)                                │ │
│ │  ┌─────────────────────────────────────────────────────────┐   │ │
│ │  │ ⚠️ Revenue -3.2% vs Budget, liderado por Rooms (-4.8%) │   │ │
│ │  │      y Spa (-6.3%)                                     │   │ │
│ │  └─────────────────────────────────────────────────────────┘   │ │
│ └──────────────────────────────────────────────────────────────────┘ │
├──────────────────────────────────────────────────────────────────────┤
│ ┌──────────────────────────────────────────────────────────────────┐ │
│ │ 📝 COMENTARIO DEL DIRECTOR FINANCIERO                           │ │
│ │ ┌──────────────────────────────────────────────────────────────┐│ │
│ │ │ "Septiembre cierra con ingresos en línea con presupuesto     ││ │
│ │ │ (€107,707 vs €107,679, -0.0%), pero el GOP se sitúa en      ││ │
│ │ │ €16,135 (-14.0% vs presupuesto). La desviación se explica    ││ │
│ │ │ por: (1) sobrecoste en personal +4.1% por cobertura de baja  ││ │
│ │ │ médica no prevista, (2) marketing +12.3% por campaña punta-  ││ │
│ │ │ de puente, (3) food cost al 35.2% vs objetivo 33%.          ││ │
│ │ │                                                              ││ │
│ │ │ 🔴 Acción requerida: Revisar política de contratación        ││ │
│ │ │ temporal y negociar con proveedores F&B.                     ││ │
│ │ │                                                              ││ │
│ │ │ En positivo: Eventos crece +9.7% vs presupuesto, con         ││ │
│ │ │ tendencia alcista. ADR en €233.98, ligeramente por encima    ││ │
│ │ │ de lo presupuestado (+0.2%). Ocupación al 83.2%, en línea."  ││ │
│ │ └──────────────────────────────────────────────────────────────┘│ │
│ └──────────────────────────────────────────────────────────────────┘ │
├──────────────────────────────────────────────────────────────────────┤
│ ┌───────────────────────────┬──────────────────────────────────────┐│
│ │ Alert History (Table)    │ Acciones Correctivas (Plan)          ││
│ │ Mes │ Alerta │ Estado    │ Alerta | Acción | Responsable | Fecha││
│ │──────────────────────────│──────────────────────────────────────││
│ │ Sep │ GOP    │ Activa    │ GOP   | Rev personal RRHH | 15-Oct  ││
│ │ Sep │ Rev    │ Activa    │ Mar-  | Campaña nov-dic   | 01-Oct  ││
│ │ Sep │ OpEx   │ Monitoreo │ ket   | Auditoria gastos  | 20-Oct  ││
│ └───────────────────────────┴──────────────────────────────────────┘│
└──────────────────────────────────────────────────────────────────────┘
```

### Visual "Anomaly Detection" (Power BI Decomposition Tree)

Añadir un **Decomposition Tree** que permita navegar:
- Partir de `[Revenue Variance]`
- Desglosar por: DimDepartment → DimAccount → DimDate[MonthName]
- Útil para reuniones: "¿Por qué no cumplimos revenue? → Por Rooms → Porque bajan las noches ocupadas"

---

## 7. Formato Condicional y Temas

### Tema Corporativo

```json
{
    "name": "Posada de Sillería - Hotel Boutique",
    "dataColors": [
        "#1E88E5",  // Rooms - Azul
        "#43A047",  // F&B - Verde
        "#8E24AA",  // Spa - Púrpura
        "#FB8C00",  // Events - Naranja
        "#546E7A",  // General - Gris
        "#D32F2F",  // Alert - Rojo
        "#FBC02D",  // Warning - Ámbar
        "#388E3C"   // OK - Verde oscuro
    ],
    "visualStyles": {
        "*": {
            "*": {
                "fontFamily": "Segoe UI",
                "fontSize": 12
            }
        }
    }
}
```

### Reglas de Formato Condicional

**Color de fondo en Cards de Variance:**
| Regla | Color |
|-------|-------|
| Revenue Var% < -10% | `#D32F2F` (rojo) |
| Revenue Var% entre -10% y -5% | `#FBC02D` (ámbar) |
| Revenue Var% entre -5% y 0% | `#FFF9C4` (amarillo claro) |
| Revenue Var% >= 0% | `#388E3C` (verde) |

**Iconos en Tabla de Alertas:**
- Severity = "CRITICAL" → 🔴
- Severity = "WARNING" → 🟡
- Severity = "MINOR" → 🟠
- Severity = "OK" → 🟢

**Barra de datos en columna Variance:**
- Negativo → barra roja hacia izquierda
- Positivo → barra verde hacia derecha (para ingresos; inverso para gastos)

---

## 8. Pasos para Importar en Power BI Desktop

```
1. Abrir Power BI Desktop
2. Obtener datos → CSV → Seleccionar todos los archivos en /data/
3. Power Query:
   a. Promover cabeceras en todas las tablas
   b. Cambiar tipo de DateKey a Número Entero
   c. Cambiar Amount a Número Decimal
   d. Cerrar y Aplicar
4. Modelo → Administrar relaciones → Crear relaciones según tabla
5. Marcar DimDate como tabla de fechas (DateKey)
6. Nueva medida → Pegar medidas de DAX-MEASURES.md
7. Crear páginas según este guide
8. Aplicar formato condicional
9. Publicar en Power BI Service
```

---

## Notas para el Equipo Financiero

🔄 **Cadencia de actualización:**
- Día 1-2 del mes: Cargar FactActuals con datos del mes cerrado
- Día 3: Actualizar DimRoomStats desde el PMS
- Día 5: Reunión de revisión mensual con el reporte

📌 **Responsables:**
- **Revenue & Rooms**: Dirección Comercial
- **F&B Cost Control**: Chef Ejecutivo + Dirección F&B
- **Payroll**: Dirección de RRHH
- **OpEx Global**: Dirección Financiera

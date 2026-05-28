# Medidas DAX — Cierre Mensual Financiero
## Hotel Boutique Posada de Sillería, Toledo

---

## 1. Medidas Base (Importes)

### Ingresos
```dax
Total Revenue = 
CALCULATE(
    SUM(FactActuals[Amount]),
    DimAccount[IsRevenue] = TRUE()
)

Total Revenue Budget = 
CALCULATE(
    SUM(FactBudget[Amount]),
    DimAccount[IsRevenue] = TRUE()
)

Revenue Variance = [Total Revenue] - [Total Revenue Budget]

Revenue Variance % = 
DIVIDE([Revenue Variance], [Total Revenue Budget], 0)
```

### Ingresos por Departamento
```dax
Revenue Rooms = 
CALCULATE(
    [Total Revenue],
    DimDepartment[DepartmentCode] = "ROOMS"
)

Revenue F&B = 
CALCULATE(
    [Total Revenue],
    DimDepartment[DepartmentCode] = "FNB"
)

Revenue Spa = 
CALCULATE(
    [Total Revenue],
    DimDepartment[DepartmentCode] = "SPA"
)

Revenue Events = 
CALCULATE(
    [Total Revenue],
    DimDepartment[DepartmentCode] = "EVENTS"
)
```

### Gastos Operativos
```dax
Total OpEx = 
CALCULATE(
    SUM(FactActuals[Amount]),
    DimAccount[FinancialClass] = "OpEx" || DimAccount[FinancialClass] = "COGS"
)

Total OpEx Budget = 
CALCULATE(
    SUM(FactBudget[Amount]),
    DimAccount[FinancialClass] = "OpEx" || DimAccount[FinancialClass] = "COGS"
)

OpEx Variance = [Total OpEx] - [Total OpEx Budget]

OpEx Variance % = DIVIDE([OpEx Variance], [Total OpEx Budget], 0)

Total COGS = 
CALCULATE(
    SUM(FactActuals[Amount]),
    DimAccount[FinancialClass] = "COGS"
)
```

### GOP (Gross Operating Profit)
```dax
GOP = [Total Revenue] - [Total OpEx]

GOP Budget = [Total Revenue Budget] - [Total OpEx Budget]

GOP Variance = [GOP] - [GOP Budget]

GOP Margin = DIVIDE([GOP], [Total Revenue], 0)

GOP Margin Budget = DIVIDE([GOP Budget], [Total Revenue Budget], 0)

GOP Margin Variance = [GOP Margin] - [GOP Margin Budget]
```

### EBITDA
```dax
Total Fixed Costs = 
CALCULATE(
    SUM(FactActuals[Amount]),
    DimAccount[FinancialClass] = "Fixed"
)

Total NonOp = 
CALCULATE(
    SUM(FactActuals[Amount]),
    DimAccount[FinancialClass] = "NonOp"
)

EBITDA = [GOP] - [Total Fixed Costs]

EBITDA Budget = [GOP Budget] - 
    CALCULATE(
        SUM(FactBudget[Amount]),
        DimAccount[FinancialClass] = "Fixed"
    )

EBITDA Variance = [EBITDA] - [EBITDA Budget]

EBITDA Margin = DIVIDE([EBITDA], [Total Revenue], 0)
```

### Gastos de Personal
```dax
Payroll = 
CALCULATE(
    SUM(FactActuals[Amount]),
    DimAccount[AccountCode] = "501000"
)

Payroll Budget = 
CALCULATE(
    SUM(FactBudget[Amount]),
    DimAccount[AccountCode] = "501000"
)

Payroll Variance % = 
DIVIDE([Payroll] - [Payroll Budget], [Payroll Budget], 0)

Payroll % Revenue = DIVIDE([Payroll], [Total Revenue], 0)
```

---

## 2. KPIs Habitaciones

```dax
// Requieren tabla DimRoomStats relacionada por DateKey

ADR Actual = 
AVERAGEX(
    DimRoomStats,
    DimRoomStats[ADR_Actual]
)

ADR Budget = 
AVERAGEX(
    DimRoomStats,
    DimRoomStats[ADR_Budget]
)

Occupancy % Actual = 
AVERAGEX(
    DimRoomStats,
    DimRoomStats[Ocupacion_Actual]
)

Occupancy % Budget = 
AVERAGEX(
    DimRoomStats,
    DimRoomStats[Ocupacion_Budget]
)

RevPAR Actual = 
AVERAGEX(
    DimRoomStats,
    DimRoomStats[RevPAR_Actual]
)

RevPAR Budget = 
AVERAGEX(
    DimRoomStats,
    DimRoomStats[RevPAR_Budget]
)

Noches Ocupadas = SUM(DimRoomStats[NochesOcupadas_Actual])

Occupancy Variance (pp) = 
[Occupancy % Actual] - [Occupancy % Budget]

ADR Variance % = 
DIVIDE([ADR Actual] - [ADR Budget], [ADR Budget], 0)
```

---

## 3. Medidas de Alertas (TRAFICO LUMINOSO)

### Semáforos de Desviación
```dax
// --- Semáforo de Revenue ---
Alert Revenue Traffic = 
VAR Variance = [Revenue Variance %]
RETURN
    SWITCH(
        TRUE(),
        Variance < -0.10, "CRITICAL",    // Rojo
        Variance < -0.05, "WARNING",     // Ámbar
        Variance < 0,     "MINOR",       // Amarillo claro
        "OK"                              // Verde
    )

// --- Semáforo de GOP ---
Alert GOP Traffic = 
VAR Variance = [GOP Margin Variance]
RETURN
    SWITCH(
        TRUE(),
        Variance < -0.05, "CRITICAL",
        Variance < -0.03, "WARNING",
        Variance < 0,     "MINOR",
        "OK"
    )

// --- Semáforo de OpEx ---
Alert OpEx Traffic = 
VAR Variance = [OpEx Variance %]
RETURN
    SWITCH(
        TRUE(),
        Variance > 0.10,  "CRITICAL",
        Variance > 0.06,  "WARNING",
        Variance > 0.03,  "MINOR",
        "OK"
    )

// --- Semáforo de Ocupación ---
Alert Occupancy Traffic = 
VAR VarPP = [Occupancy Variance (pp)]
RETURN
    SWITCH(
        TRUE(),
        VarPP < -8, "CRITICAL",
        VarPP < -5, "WARNING",
        VarPP < -3, "MINOR",
        "OK"
    )
```

### Contador de Alertas por Severidad
```dax
Alert Count = 
VAR Critical = 
    IF([Alert Revenue Traffic] = "CRITICAL", 1, 0) +
    IF([Alert OpEx Traffic] = "CRITICAL", 1, 0) +
    IF([Alert GOP Traffic] = "CRITICAL", 1, 0) +
    IF([Alert Occupancy Traffic] = "CRITICAL", 1, 0)

VAR Warnings = 
    IF([Alert Revenue Traffic] = "WARNING", 1, 0) +
    IF([Alert OpEx Traffic] = "WARNING", 1, 0) +
    IF([Alert GOP Traffic] = "WARNING", 1, 0) +
    IF([Alert Occupancy Traffic] = "WARNING", 1, 0)

RETURN
    Critical & " 🔴 / " & Warnings & " 🟡"
```

---

## 4. Medidas de Tendencias (Time Intelligence)

```dax
// YTD
Revenue YTD = 
TOTALYTD(
    [Total Revenue],
    DimDate[DateKey]
)

Revenue Budget YTD = 
TOTALYTD(
    [Total Revenue Budget],
    DimDate[DateKey]
)

Revenue YTD Variance = [Revenue YTD] - [Revenue Budget YTD]

GOP YTD = 
TOTALYTD(
    [GOP],
    DimDate[DateKey]
)

// Promedio Móvil 3 Meses
Revenue MA3 = 
CALCULATE(
    AVERAGEX(
        DATESINPERIOD(DimDate[DateKey], LASTDATE(DimDate[DateKey]), -3, MONTH),
        [Total Revenue]
    ),
    ALL(DimDate)
)
```

---

## 5. Medidas de Composición

```dax
Revenue % Rooms = DIVIDE([Revenue Rooms], [Total Revenue], 0)

Revenue % F&B = DIVIDE([Revenue F&B], [Total Revenue], 0)

Revenue % Spa = DIVIDE([Revenue Spa], [Total Revenue], 0)

Revenue % Events = DIVIDE([Revenue Events], [Total Revenue], 0)

Food Cost % = 
VAR FoodCost = 
    CALCULATE(
        SUM(FactActuals[Amount]),
        DimAccount[AccountCode] = "509000"
    )
VAR FnBRevenue = [Revenue F&B]
RETURN
    DIVIDE(FoodCost, FnBRevenue, 0)
```

---

## 6. Medida para Gráfico Waterfall (Cascada)

```dax
Waterfall GOP Bridge = 
VAR SelectedMonth = SELECTEDVALUE(DimDate[MonthNumber])
VAR PrevMonth = SelectedMonth - 1
VAR PrevGOP = 
    CALCULATE(
        [GOP],
        DimDate[MonthNumber] = PrevMonth,
        ALL(DimDate)
    )
VAR CurrentGOP = [GOP]
VAR Delta = CurrentGOP - PrevGOP
RETURN
    Delta
```

---

## 7. Medida Narrativa (para visual "Narrative" de Power BI)

```dax
Executive Summary = 
VAR MesActual = SELECTEDVALUE(DimDate[MonthName])
VAR Rev = FORMAT([Total Revenue], "#,##0")
VAR RevBud = FORMAT([Total Revenue Budget], "#,##0")
VAR RevVar = FORMAT([Revenue Variance %], "0.0%")
VAR GOPVal = FORMAT([GOP], "#,##0")
VAR GOPVar = FORMAT([GOP Variance], "#,##0")
VAR Ocu = FORMAT([Occupancy % Actual], "0.0")
VAR OcuVar = FORMAT([Occupancy Variance (pp)], "0.0")
VAR ADRVal = FORMAT([ADR Actual], "#,##0")
VAR AlertStatus = [Alert Revenue Traffic]

RETURN
    "📊 Cierre Mensual - " & MesActual & " 2025" & UNICHAR(10) &
    "Ingresos: " & Rev & "€ vs Presupuesto: " & RevBud & "€ (" & RevVar & ")" & UNICHAR(10) &
    "GOP: " & GOPVal & "€ (Var: " & GOPVar & "€)" & UNICHAR(10) &
    "Ocupación: " & Ocu & "% | ADR: " & ADRVal & "€" & UNICHAR(10) &
    "Estado: " & AlertStatus
```

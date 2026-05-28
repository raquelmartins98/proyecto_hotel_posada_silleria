# Sistema de Alertas — Cierre Mensual
## Hotel Boutique Posada de Sillería · Toledo

---

## Arquitectura de Alertas

El sistema tiene **3 capas** de alertas, desde automáticas en Power BI hasta gobernanza:

```
┌────────────────────────────────────────────┐
│  CAPA 1: POWER BI (automática)             │
│  • Semáforos en DAX (medidas traffic light)│
│  • Formato condicional en tarjetas/tablas  │
│  • Alertas por correo desde Power BI       │
│    Service (suscripciones)                 │
├────────────────────────────────────────────┤
│  CAPA 2: POWER AUTOMATE (notificaciones)   │
│  • Flujo: Alerta en dataset → Teams/Email  │
│  • Resumen ejecutivo cada cierre mensual   │
│  • Escalado si alertas críticas no se      │
│    resuelven en 5 días                     │
├────────────────────────────────────────────┤
│  CAPA 3: GOBERNANZA (comité financiero)    │
│  • Acciones correctivas con responsables   │
│  • Revisión trimestral de umbrales         │
│  • Histórico de alertas y resolución       │
└────────────────────────────────────────────┘
```

---

## Umbrales de Alerta por Métrica

### ⚠️ REGLA GENERAL — Umbrales por severidad

| Severidad | Color | Acción |
|-----------|-------|--------|
| 🔴 **CRITICAL** | Rojo | Notificación inmediata al CFO |
| 🟡 **WARNING** | Ámbar | Incluir en informe mensual |
| 🟠 **MINOR** | Naranja | Monitoreo, mencionar si persiste |
| 🟢 **OK** | Verde | Sin acción requerida |

---

### 📊 Revenue — Desviación de Ingresos

| Severidad | Umbral | Acción |
|-----------|--------|--------|
| 🔴 CRITICAL | < -10% vs Budget | Reunión extraordinaria comercial |
| 🟡 WARNING | < -5% vs Budget | Revisar estrategia de precios y OTAs |
| 🟠 MINOR | < 0% vs Budget | Monitorear tendencia |
| 🟢 OK | >= 0% | Sin acción |

### 🏨 Ocupación — Desviación en puntos porcentuales

| Severidad | Umbral (pp) | Acción |
|-----------|-------------|--------|
| 🔴 CRITICAL | < -8 pp | Revisar campañas marketing + OTAs |
| 🟡 WARNING | < -5 pp | Analizar competencia y demanda |
| 🟠 MINOR | < -3 pp | Ajustar tactical pricing |
| 🟢 OK | >= -3 pp | Sin acción |

### 💰 GOP — Margen Bruto Operativo

| Severidad | Umbral (pp) | Acción |
|-----------|-------------|--------|
| 🔴 CRITICAL | < -5 pp vs objetivo | Auditoría de gastos urgente |
| 🟡 WARNING | < -3 pp vs objetivo | Revisión estructura costes |
| 🟠 MINOR | < 0 pp vs objetivo | Optimización progresiva |
| 🟢 OK | >= 0 pp | Sin acción |

### 💸 OpEx — Sobrecoste Operativo

| Severidad | Umbral | Acción |
|-----------|--------|--------|
| 🔴 CRITICAL | > +10% vs Budget | Congelación de gastos no críticos |
| 🟡 WARNING | > +6% vs Budget | Revisión por centro de coste |
| 🟠 MINOR | > +3% vs Budget | Identificar partidas concretas |
| 🟢 OK | <= +3% | Sin acción |

### 👥 Payroll — Desviación en Personal

| Severidad | Umbral | Acción |
|-----------|--------|--------|
| 🔴 CRITICAL | > +8% vs Budget | Revisión plantilla y horas extra |
| 🟡 WARNING | > +5% vs Budget | Analizar cobertura de bajas |
| 🟠 MINOR | > +3% vs Budget | Monitorear tendencia |
| 🟢 OK | <= +3% | Sin acción |

### 🍽️ Food Cost — Porcentaje sobre ingresos F&B

| Severidad | Umbral | Acción |
|-----------|--------|--------|
| 🔴 CRITICAL | > 38% | Auditoría de inventario y proveedores |
| 🟡 WARNING | > 35% | Revisión de recetas y desperdicio |
| 🟠 MINOR | > 33% | Optimización de carta |
| 🟢 OK | <= 33% (objetivo) | Sin acción |

---

## Cálculo de Alertas en Power BI

```dax
// ─────────────────────────────────────────────
// SISTEMA DE ALERTAS UNIFICADO
// ─────────────────────────────────────────────

// Devuelve: "CRITICAL", "WARNING", "MINOR", "OK"
Alert Status = 
VAR RevAlert = [Alert Revenue Traffic]
VAR OcuAlert = [Alert Occupancy Traffic]
VAR GOPAlert = [Alert GOP Traffic]
VAR OpExAlert = [Alert OpEx Traffic]

VAR MaxSeverity = 
    SWITCH(
        TRUE(),
        RevAlert = "CRITICAL" || OcuAlert = "CRITICAL" || GOPAlert = "CRITICAL" || OpExAlert = "CRITICAL", "CRITICAL",
        RevAlert = "WARNING" || OcuAlert = "WARNING" || GOPAlert = "WARNING" || OpExAlert = "WARNING", "WARNING",
        RevAlert = "MINOR" || OcuAlert = "MINOR" || GOPAlert = "MINOR" || OpExAlert = "MINOR", "MINOR",
        "OK"
    )
RETURN MaxSeverity

// Contador de alertas críticas activas
Critical Alert Count = 
VAR Alerts = {
    ("Revenue", [Alert Revenue Traffic]),
    ("Occupancy", [Alert Occupancy Traffic]),
    ("GOP", [Alert GOP Traffic]),
    ("OpEx", [Alert OpEx Traffic])
}
RETURN
    COUNTROWS(
        FILTER(Alerts, [Value] = "CRITICAL")
    )

// Texto descriptivo de alertas activas
Alert Details = 
VAR AlertsList = 
    UNION(
        ROW("Metric", "Revenue", "Status", [Alert Revenue Traffic]),
        ROW("Metric", "Occupancy", "Status", [Alert Occupancy Traffic]),
        ROW("Metric", "GOP", "Status", [Alert GOP Traffic]),
        ROW("Metric", "OpEx", "Status", [Alert OpEx Traffic])
    )
VAR ActiveAlerts = FILTER(AlertsList, [Status] <> "OK")
VAR AlertCount = COUNTROWS(ActiveAlerts)
VAR AlertText = 
    CONCATENATEX(
        ActiveAlerts,
        [Metric] & ": " & [Status],
        UNICHAR(10)
    )
RETURN
    IF(AlertCount > 0,
        "Alertas activas (" & AlertCount & "):" & UNICHAR(10) & AlertText,
        "✅ Sin alertas activas este mes"
    )
```

---

## Acciones Correctivas por Tipo de Alerta

### Revenue CRITICAL
```yaml
alerta: "Caída de ingresos >10% vs presupuesto"
acciones:
  - action: "Revisar estrategia de precios en OTAs"
    responsable: "Revenue Manager"
    plazo: "48 horas"
  - action: "Lanzar campaña de último minuto"
    responsable: "Marketing"
    plazo: "24 horas"
  - action: "Contactar a clientes corporativos históricos"
    responsable: "Director Comercial"
    plazo: "1 semana"
escalada: "CFO + Director General"
```

### GOP CRITICAL
```yaml
alerta: "Margen GOP >5pp por debajo de objetivo"
acciones:
  - action: "Congelación de gastos discrecionales"
    responsable: "CFO"
    plazo: "Inmediato"
  - action: "Auditoría de costes operativos línea por línea"
    responsable: "Controller Financiero"
    plazo: "1 semana"
  - action: "Revisión de contratos con proveedores"
    responsable: "Director de Operaciones"
    plazo: "2 semanas"
escalada: "CFO + Consejo"
```

### OpEx CRITICAL
```yaml
alerta: "Sobrecoste operativo >10%"
acciones:
  - action: "Identificar partidas responsables del overrun"
    responsable: "Controller Financiero"
    plazo: "72 horas"
  - action: "Reunión con responsables de departamento"
    responsable: "CFO"
    plazo: "1 semana"
  - action: "Implementar medidas de contención"
    responsable: "Director de Operaciones"
    plazo: "2 semanas"
escalada: "Comité de Dirección"
```

---

## Dashboard de Seguimiento de Alertas

Para incluir en el reporte mensual, una tabla que muestre:

```
┌─────────┬──────────────┬──────────┬───────────────┬──────────┬──────────────┐
│ Mes     │ Alerta       │ Severidad│ Días Activa   │ Acción   │ Responsable  │
├─────────┼──────────────┼──────────┼───────────────┼──────────┼──────────────┤
│ Sep 2025│ GOP Margin   │ 🔴       │ 5 días        │ Auditoría│ M. García    │
│ Sep 2025│ Revenue      │ 🟡       │ 12 días       │ Campaña  │ L. Rodríguez │
│ Ago 2025│ OpEx         │ 🟡       │ 28 días       │ Revisión │ A. López     │
│ Jul 2025│ Ocupación    │ 🟡       │ 45 días       │ Pricing  │ L. Rodríguez │
└─────────┴──────────────┴──────────┴───────────────┴──────────┴──────────────┘
```

> ⏱ **Regla de escalado**: Si una alerta CRITICAL permanece activa >7 días, se escala automáticamente al Director General. Si una WARNING persiste >30 días, se revisa el umbral o se eleva a CRITICAL.

---

## Power Automate Flow (Recomendación)

```
Disparador: 
  - Programado: Día 5 de cada mes a las 9:00 AM
  - O: Cuando se actualice el dataset de Power BI

Pasos:
  1. Obtener datos del reporte "Alert Status" (API Power BI)
  2. Si alguna métrica = "CRITICAL":
     a. Enviar email a CFO + Dirección
     b. Publicar mensaje en Teams #alertas-financieras
     c. Crear tarea en Planner "Revisión alerta CRITICAL"
  3. Si todas = "OK":
     a. Enviar resumen por email "Cierre sin incidencias"
  4. Generar resumen ejecutivo en PDF (Power Automate + Word Template)
```

---

## Cadencia de Revisión de Umbrales

| Frecuencia | Acción | Responsable |
|-----------|--------|-------------|
| Mensual | Validar alertas del cierre | Controller |
| Trimestral | Revisar si los umbrales siguen siendo adecuados | CFO + Controller |
| Anual | Ajustar umbrales para nuevo presupuesto | Dirección |
| Ad-hoc | Si hay 3+ meses seguidos con la misma alerta | Comité Financiero |

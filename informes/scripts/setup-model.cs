// ════════════════════════════════════════════════════════════════
//  Tabular Editor 2 C# Script
//  Configuración completa del modelo semántico
//  Hotel Boutique Posada de Sillería — Cierre Mensual Financiero
// ════════════════════════════════════════════════════════════════
//  INSTRUCCIONES:
//  1. Power BI Desktop: Obtener datos → CSV → importar los 7 archivos
//     de la carpeta /data/
//  2. Guardar el .pbix (ej: "PosadaDeSilleria.pbix")
//  3. Abrir Tabular Editor 2 → File → Open → seleccionar .pbix
//     (Power BI Desktop debe estar abierto con el .pbix cargado)
//  4. Tabular Editor: File → Open from Power BI Desktop → conectar
//  5. Pegar este script en Advanced Scripting (F5 o Run)
//  6. Tabular Editor: File → Save to Power BI Desktop
//  7. Volver a Power BI Desktop, las relaciones y medidas están listas
// ════════════════════════════════════════════════════════════════

// ───────────────────────────────────────────
// 1. VERIFICACIÓN DE TABLAS
// ───────────────────────────────────────────

var expectedTables = new[] { "DimDate", "DimAccount", "DimDepartment", "DimRoomStats", "DimAlerts", "FactActuals", "FactBudget" };
var missingTables = expectedTables.Where(t => !Model.Tables.Contains(t)).ToList();

if (missingTables.Any())
{
    throw new Exception("FALTAN TABLAS: " + string.Join(", ", missingTables) + 
        "\nAsegúrate de haber importado TODOS los 7 CSVs en Power BI Desktop antes de ejecutar este script.");
}

Info("✅ Todas las tablas encontradas. Procediendo con la configuración...");

// ───────────────────────────────────────────
// 2. CONFIGURACIÓN DE COLUMNAS
// ───────────────────────────────────────────

// Aseguramos tipos de datos correctos y formato
void ConfigureColumns()
{
    // DimDate
    var dimDate = Model.Tables["DimDate"];
    SetColumnType(dimDate, "DateKey", ColumnDataType.Int64, "Standard", "0");
    SetColumnType(dimDate, "Year", ColumnDataType.Int64, "Standard", "0");
    SetColumnType(dimDate, "MonthNumber", ColumnDataType.Int64, "Standard", "0");
    SetColumnType(dimDate, "DiasDelMes", ColumnDataType.Int64, "Standard", "0");
    SetColumnType(dimDate, "WeekendDays", ColumnDataType.Int64, "Standard", "0");
    SetColumnType(dimDate, "WeekdayDays", ColumnDataType.Int64, "Standard", "0");
    SetColumnType(dimDate, "IsTemporadaAlta", ColumnDataType.Boolean, "Standard", "");
    dimDate.Columns["DateKey"].SortByColumn = dimDate.Columns["DateKey"];
    dimDate.Columns["MonthNumber"].SortByColumn = dimDate.Columns["MonthNumber"];
    dimDate.Columns["MonthShort"].SortByColumn = dimDate.Columns["MonthNumber"];
    
    // DimAccount
    var dimAccount = Model.Tables["DimAccount"];
    SetColumnType(dimAccount, "AccountKey", ColumnDataType.Int64, "Standard", "0");
    SetColumnType(dimAccount, "OrderBy", ColumnDataType.Int64, "Standard", "0");
    SetColumnType(dimAccount, "IsRevenue", ColumnDataType.Boolean, "Standard", "");
    SetColumnType(dimAccount, "IsExpense", ColumnDataType.Boolean, "Standard", "");
    SetColumnType(dimAccount, "FinancialClass", ColumnDataType.String, "Standard", "");
    dimAccount.Columns["AccountName"].SortByColumn = dimAccount.Columns["OrderBy"];
    
    // DimDepartment
    var dimDept = Model.Tables["DimDepartment"];
    SetColumnType(dimDept, "DepartmentKey", ColumnDataType.Int64, "Standard", "0");
    SetColumnType(dimDept, "OrderBy", ColumnDataType.Int64, "Standard", "0");
    SetColumnType(dimDept, "IsRevenueCenter", ColumnDataType.Boolean, "Standard", "");
    dimDept.Columns["DepartmentName"].SortByColumn = dimDept.Columns["OrderBy"];
    
    // DimRoomStats
    var dimRooms = Model.Tables["DimRoomStats"];
    SetColumnType(dimRooms, "DateKey", ColumnDataType.Int64, "Standard", "0");
    SetColumnType(dimRooms, "Year", ColumnDataType.Int64, "Standard", "0");
    SetColumnType(dimRooms, "Month", ColumnDataType.Int64, "Standard", "0");
    SetColumnType(dimRooms, "NochesOcupadas_Actual", ColumnDataType.Int64, "Standard", "0");
    SetColumnType(dimRooms, "NochesOcupadas_Budget", ColumnDataType.Int64, "Standard", "0");
    SetColumnType(dimRooms, "HabitacionesDisponibles", ColumnDataType.Int64, "Standard", "0");
    SetColumnType(dimRooms, "ADR_Actual", ColumnDataType.Double, "Standard", "#,##0.00");
    SetColumnType(dimRooms, "ADR_Budget", ColumnDataType.Double, "Standard", "#,##0.00");
    SetColumnType(dimRooms, "RevPAR_Actual", ColumnDataType.Double, "Standard", "#,##0.00");
    SetColumnType(dimRooms, "RevPAR_Budget", ColumnDataType.Double, "Standard", "#,##0.00");
    SetColumnType(dimRooms, "Ocupacion_Actual", ColumnDataType.Double, "Standard", "0.0%");
    SetColumnType(dimRooms, "Ocupacion_Budget", ColumnDataType.Double, "Standard", "0.0%");
    
    // FactActuals / FactBudget
    foreach (var tblName in new[] { "FactActuals", "FactBudget" })
    {
        var tbl = Model.Tables[tblName];
        SetColumnType(tbl, "DateKey", ColumnDataType.Int64, "Standard", "0");
        SetColumnType(tbl, "AccountKey", ColumnDataType.Int64, "Standard", "0");
        SetColumnType(tbl, "DepartmentKey", ColumnDataType.Int64, "Standard", "0");
        SetColumnType(tbl, "Amount", ColumnDataType.Double, "Standard", "#,##0");
        tbl.Columns["Amount"].SummarizeBy = AggregateFunction.Sum;
    }
}

void SetColumnType(Table table, string columnName, ColumnDataType type, string dataCategory, string formatString)
{
    if (!table.Columns.Contains(columnName)) return;
    var col = table.Columns[columnName];
    col.DataType = type;
    col.DataCategory = dataCategory;
    if (!string.IsNullOrEmpty(formatString))
        col.FormatString = formatString;
}

ConfigureColumns();
Info("✅ Columnas configuradas correctamente.");

// ───────────────────────────────────────────
// 3. RELACIONES
// ───────────────────────────────────────────

// Limpiar relaciones existentes que puedan interferir
foreach (var rel in Model.Relationships.ToList())
    rel.Delete();

Info("Creando relaciones del esquema estrella...");

void CreateRelationship(string fromTable, string fromColumn, string toTable, string toColumn, CrossFilteringBehavior crossFilter)
{
    Model.AddRelationship(
        Model.Tables[fromTable].Columns[fromColumn],
        Model.Tables[toTable].Columns[toColumn],
        crossFilter
    );
}

// DimDate → FactActuals
CreateRelationship("DimDate", "DateKey", "FactActuals", "DateKey", CrossFilteringBehavior.SingleDirection);
// DimDate → FactBudget
CreateRelationship("DimDate", "DateKey", "FactBudget", "DateKey", CrossFilteringBehavior.SingleDirection);
// DimDate → DimRoomStats
CreateRelationship("DimDate", "DateKey", "DimRoomStats", "DateKey", CrossFilteringBehavior.SingleDirection);

// DimAccount → FactActuals
CreateRelationship("DimAccount", "AccountKey", "FactActuals", "AccountKey", CrossFilteringBehavior.SingleDirection);
// DimAccount → FactBudget
CreateRelationship("DimAccount", "AccountKey", "FactBudget", "AccountKey", CrossFilteringBehavior.SingleDirection);

// DimDepartment → FactActuals
var relDeptAct = CreateRelationship("DimDepartment", "DepartmentKey", "FactActuals", "DepartmentKey", CrossFilteringBehavior.SingleDirection);
// DimDepartment → FactBudget
var relDeptBgt = CreateRelationship("DimDepartment", "DepartmentKey", "FactBudget", "DepartmentKey", CrossFilteringBehavior.SingleDirection);

Info("✅ 7 relaciones creadas: Esquema estrella completo.");

// ───────────────────────────────────────────
// 4. MEDIDAS — INGRESOS
// ───────────────────────────────────────────

Info("Creando medidas...");
var fact = Model.Tables["FactActuals"];

// --- Medidas Base ---
Measure NewMeasure(Table table, string name, string expression, string formatString, string displayFolder)
{
    var m = table.AddMeasure(name, expression, displayFolder);
    m.FormatString = formatString;
    return m;
}

// ── 4.1 INGRESOS ──
NewMeasure(fact, "Total Revenue", 
    "CALCULATE(SUM(FactActuals[Amount]), DimAccount[IsRevenue] = TRUE())", 
    "#,##0 €", "01 - Ingresos");

NewMeasure(fact, "Total Revenue Budget", 
    "CALCULATE(SUM(FactBudget[Amount]), DimAccount[IsRevenue] = TRUE())", 
    "#,##0 €", "01 - Ingresos");

NewMeasure(fact, "Revenue Variance", 
    "[Total Revenue] - [Total Revenue Budget]", 
    "#,##0 €", "01 - Ingresos");

NewMeasure(fact, "Revenue Variance %", 
    "DIVIDE([Revenue Variance], [Total Revenue Budget], 0)", 
    "+0.0%;-0.0%;0.0%", "01 - Ingresos");

// ── 4.2 INGRESOS POR DEPARTAMENTO ──
NewMeasure(fact, "Revenue Rooms", 
    "CALCULATE([Total Revenue], DimDepartment[DepartmentCode] = \"ROOMS\")", 
    "#,##0 €", "01 - Ingresos");

NewMeasure(fact, "Revenue F&B", 
    "CALCULATE([Total Revenue], DimDepartment[DepartmentCode] = \"FNB\")", 
    "#,##0 €", "01 - Ingresos");

NewMeasure(fact, "Revenue Spa", 
    "CALCULATE([Total Revenue], DimDepartment[DepartmentCode] = \"SPA\")", 
    "#,##0 €", "01 - Ingresos");

NewMeasure(fact, "Revenue Events", 
    "CALCULATE([Total Revenue], DimDepartment[DepartmentCode] = \"EVENTS\")", 
    "#,##0 €", "01 - Ingresos");

NewMeasure(fact, "Revenue % Rooms", 
    "DIVIDE([Revenue Rooms], [Total Revenue], 0)", 
    "0.0%", "01 - Ingresos");

NewMeasure(fact, "Revenue % F&B", 
    "DIVIDE([Revenue F&B], [Total Revenue], 0)", 
    "0.0%", "01 - Ingresos");

NewMeasure(fact, "Revenue % Spa", 
    "DIVIDE([Revenue Spa], [Total Revenue], 0)", 
    "0.0%", "01 - Ingresos");

NewMeasure(fact, "Revenue % Events", 
    "DIVIDE([Revenue Events], [Total Revenue], 0)", 
    "0.0%", "01 - Ingresos");

// ── 4.3 GASTOS ──
NewMeasure(fact, "Total OpEx", 
    "CALCULATE(SUM(FactActuals[Amount]), DimAccount[FinancialClass] = \"OpEx\" || DimAccount[FinancialClass] = \"COGS\")", 
    "#,##0 €", "02 - Gastos");

NewMeasure(fact, "Total OpEx Budget", 
    "CALCULATE(SUM(FactBudget[Amount]), DimAccount[FinancialClass] = \"OpEx\" || DimAccount[FinancialClass] = \"COGS\")", 
    "#,##0 €", "02 - Gastos");

NewMeasure(fact, "OpEx Variance", 
    "[Total OpEx] - [Total OpEx Budget]", 
    "#,##0 €", "02 - Gastos");

NewMeasure(fact, "OpEx Variance %", 
    "DIVIDE([OpEx Variance], [Total OpEx Budget], 0)", 
    "+0.0%;-0.0%;0.0%", "02 - Gastos");

NewMeasure(fact, "Payroll", 
    "CALCULATE(SUM(FactActuals[Amount]), DimAccount[AccountCode] = \"501000\")", 
    "#,##0 €", "02 - Gastos");

NewMeasure(fact, "Payroll Budget", 
    "CALCULATE(SUM(FactBudget[Amount]), DimAccount[AccountCode] = \"501000\")", 
    "#,##0 €", "02 - Gastos");

NewMeasure(fact, "Payroll Variance %", 
    "DIVIDE([Payroll] - [Payroll Budget], [Payroll Budget], 0)", 
    "+0.0%;-0.0%;0.0%", "02 - Gastos");

NewMeasure(fact, "Payroll % Revenue", 
    "DIVIDE([Payroll], [Total Revenue], 0)", 
    "0.0%", "02 - Gastos");

NewMeasure(fact, "Food Cost %", 
    "VAR FoodCost = CALCULATE(SUM(FactActuals[Amount]), DimAccount[AccountCode] = \"509000\")\r\nVAR FnBRevenue = [Revenue F&B]\r\nRETURN DIVIDE(FoodCost, FnBRevenue, 0)", 
    "0.0%", "02 - Gastos");

// ── 4.4 GOP ──
NewMeasure(fact, "GOP", 
    "[Total Revenue] - [Total OpEx]", 
    "#,##0 €", "03 - GOP");

NewMeasure(fact, "GOP Budget", 
    "[Total Revenue Budget] - [Total OpEx Budget]", 
    "#,##0 €", "03 - GOP");

NewMeasure(fact, "GOP Variance", 
    "[GOP] - [GOP Budget]", 
    "#,##0 €", "03 - GOP");

NewMeasure(fact, "GOP Margin", 
    "DIVIDE([GOP], [Total Revenue], 0)", 
    "0.0%", "03 - GOP");

NewMeasure(fact, "GOP Margin Budget", 
    "DIVIDE([GOP Budget], [Total Revenue Budget], 0)", 
    "0.0%", "03 - GOP");

NewMeasure(fact, "GOP Margin Variance", 
    "[GOP Margin] - [GOP Margin Budget]", 
    "+0.0%;-0.0%", "03 - GOP");

// ── 4.5 EBITDA ──
NewMeasure(fact, "Total Fixed Costs", 
    "CALCULATE(SUM(FactActuals[Amount]), DimAccount[FinancialClass] = \"Fixed\")", 
    "#,##0 €", "04 - EBITDA");

NewMeasure(fact, "EBITDA", 
    "[GOP] - [Total Fixed Costs]", 
    "#,##0 €", "04 - EBITDA");

NewMeasure(fact, "EBITDA Budget", 
    "[GOP Budget] - CALCULATE(SUM(FactBudget[Amount]), DimAccount[FinancialClass] = \"Fixed\")", 
    "#,##0 €", "04 - EBITDA");

NewMeasure(fact, "EBITDA Variance", 
    "[EBITDA] - [EBITDA Budget]", 
    "#,##0 €", "04 - EBITDA");

NewMeasure(fact, "EBITDA Margin", 
    "DIVIDE([EBITDA], [Total Revenue], 0)", 
    "0.0%", "04 - EBITDA");

// ── 4.6 KPIs ──
var rooms = Model.Tables["DimRoomStats"];

NewMeasure(rooms, "ADR Actual", 
    "AVERAGEX(DimRoomStats, DimRoomStats[ADR_Actual])", 
    "#,##0.00 €", "KPIs");

NewMeasure(rooms, "ADR Budget", 
    "AVERAGEX(DimRoomStats, DimRoomStats[ADR_Budget])", 
    "#,##0.00 €", "KPIs");

NewMeasure(rooms, "ADR Variance %", 
    "DIVIDE([ADR Actual] - [ADR Budget], [ADR Budget], 0)", 
    "+0.0%;-0.0%;0.0%", "KPIs");

NewMeasure(rooms, "Occupancy % Actual", 
    "AVERAGEX(DimRoomStats, DimRoomStats[Ocupacion_Actual])", 
    "0.0%", "KPIs");

NewMeasure(rooms, "Occupancy % Budget", 
    "AVERAGEX(DimRoomStats, DimRoomStats[Ocupacion_Budget])", 
    "0.0%", "KPIs");

NewMeasure(rooms, "Occupancy Variance (pp)", 
    "[Occupancy % Actual] - [Occupancy % Budget]", 
    "+0.0;-0.0", "KPIs");

NewMeasure(rooms, "RevPAR Actual", 
    "AVERAGEX(DimRoomStats, DimRoomStats[RevPAR_Actual])", 
    "#,##0.00 €", "KPIs");

NewMeasure(rooms, "RevPAR Budget", 
    "AVERAGEX(DimRoomStats, DimRoomStats[RevPAR_Budget])", 
    "#,##0.00 €", "KPIs");

NewMeasure(rooms, "Noches Ocupadas", 
    "SUM(DimRoomStats[NochesOcupadas_Actual])", 
    "#,##0", "KPIs");

// ── 4.7 ALERTAS (Traffic Lights) ──
NewMeasure(fact, "Alert Revenue Traffic", 
    "VAR Variance = [Revenue Variance %]\r\nRETURN SWITCH(TRUE(),\r\nVariance < -0.10, \"🔴 CRITICAL\",\r\nVariance < -0.05, \"🟡 WARNING\",\r\nVariance < 0, \"🟠 MINOR\",\r\n\"🟢 OK\")", 
    "", "05 - Alertas");

NewMeasure(fact, "Alert OpEx Traffic", 
    "VAR Variance = [OpEx Variance %]\r\nRETURN SWITCH(TRUE(),\r\nVariance > 0.10, \"🔴 CRITICAL\",\r\nVariance > 0.06, \"🟡 WARNING\",\r\nVariance > 0.03, \"🟠 MINOR\",\r\n\"🟢 OK\")", 
    "", "05 - Alertas");

NewMeasure(fact, "Alert GOP Traffic", 
    "VAR Variance = [GOP Margin Variance]\r\nRETURN SWITCH(TRUE(),\r\nVariance < -0.05, \"🔴 CRITICAL\",\r\nVariance < -0.03, \"🟡 WARNING\",\r\nVariance < 0, \"🟠 MINOR\",\r\n\"🟢 OK\")", 
    "", "05 - Alertas");

NewMeasure(fact, "Alert Occupancy Traffic", 
    "VAR VarPP = [Occupancy Variance (pp)] / 100\r\nRETURN SWITCH(TRUE(),\r\nVarPP < -0.08, \"🔴 CRITICAL\",\r\nVarPP < -0.05, \"🟡 WARNING\",\r\nVarPP < -0.03, \"🟠 MINOR\",\r\n\"🟢 OK\")", 
    "", "05 - Alertas");

NewMeasure(fact, "Alert Status", 
    "VAR Alerts = {\r\n(\"Revenue\", [Alert Revenue Traffic]),\r\n(\"OpEx\", [Alert OpEx Traffic]),\r\n(\"GOP\", [Alert GOP Traffic]),\r\n(\"Occupancy\", [Alert Occupancy Traffic])\r\n}\r\nVAR Worst = MINX(Alerts,\r\nSWITCH([Value],\r\n\"🔴 CRITICAL\", 1,\r\n\"🟡 WARNING\", 2,\r\n\"🟠 MINOR\", 3,\r\n\"🟢 OK\", 4, 99))\r\nRETURN SWITCH(Worst,\r\n1, \"🔴 CRITICAL\",\r\n2, \"🟡 WARNING\",\r\n3, \"🟠 MINOR\",\r\n\"🟢 OK\")", 
    "", "05 - Alertas");

NewMeasure(fact, "Critical Alert Count", 
    "VAR t = {\r\n(\"Revenue\", [Alert Revenue Traffic]),\r\n(\"OpEx\", [Alert OpEx Traffic]),\r\n(\"GOP\", [Alert GOP Traffic]),\r\n(\"Occupancy\", [Alert Occupancy Traffic])\r\n}\r\nRETURN COUNTROWS(FILTER(t, [Value] = \"🔴 CRITICAL\"))", 
    "0", "05 - Alertas");

// ── 4.8 TIME INTELLIGENCE ──
NewMeasure(fact, "Revenue YTD", 
    "TOTALYTD([Total Revenue], DimDate[DateKey])", 
    "#,##0 €", "06 - Time Intelligence");

NewMeasure(fact, "Revenue Budget YTD", 
    "TOTALYTD([Total Revenue Budget], DimDate[DateKey])", 
    "#,##0 €", "06 - Time Intelligence");

NewMeasure(fact, "GOP YTD", 
    "TOTALYTD([GOP], DimDate[DateKey])", 
    "#,##0 €", "06 - Time Intelligence");

// ── 4.9 INCOME STATEMENT (for Matrix visual) ──
NewMeasure(fact, "IS Amount", 
    "VAR CurrentSection = SELECTEDVALUE('P&L Hierarchy'[AccountFilter])\r\nRETURN SWITCH(TRUE(),\r\nCurrentSection = \"GROSS_MARGIN\", [Total Revenue] - [Total COGS],\r\nCurrentSection = \"GOP\", [GOP],\r\nCurrentSection = \"EBITDA\", [EBITDA],\r\nCurrentSection = \"NET_RESULT\", [EBITDA] - CALCULATE(SUM(FactActuals[Amount]), DimAccount[FinancialClass] = \"NonOp\"),\r\nCurrentSection = \"REVENUE\" || CurrentSection = \"ROOMS\" || CurrentSection = \"FNB\" || CurrentSection = \"SPA\" || CurrentSection = \"OTHER\",\r\n    CALCULATE(SUM(FactActuals[Amount]), DimAccount[IsRevenue] = TRUE()),\r\nCurrentSection = \"COGS\" || CurrentSection = \"F&B COGS\" || CurrentSection = \"SPA COGS\" || CurrentSection = \"OTA COMS\",\r\n    CALCULATE(SUM(FactActuals[Amount]), DimAccount[FinancialClass] = \"COGS\"),\r\nCurrentSection = \"OPEX\" || CurrentSection = \"PAYROLL\" || CurrentSection = \"CLEANING\" || CurrentSection = \"SUPPLIES\" || CurrentSection = \"MARKETING\" || CurrentSection = \"MAINTENANCE\" || CurrentSection = \"UTILITIES\" || CurrentSection = \"ADMIN\" || CurrentSection = \"MISC\",\r\n    CALCULATE(SUM(FactActuals[Amount]), DimAccount[FinancialClass] = \"OpEx\"),\r\nCurrentSection = \"FIXED\" || CurrentSection = \"INSURANCE\",\r\n    CALCULATE(SUM(FactActuals[Amount]), DimAccount[FinancialClass] = \"Fixed\"),\r\nCurrentSection = \"NONOP\" || CurrentSection = \"DEPRECIATION\" || CurrentSection = \"FINANCIAL\",\r\n    CALCULATE(SUM(FactActuals[Amount]), DimAccount[FinancialClass] = \"NonOp\"),\r\nBLANK())", 
    "#,##0 €", "07 - Income Statement");

// ───────────────────────────────────────────
// FINALIZACIÓN
// ───────────────────────────────────────────
Info("═══════════════════════════════════════════════════");
Info("✅ MODELO CONFIGURADO COMPLETAMENTE");
Info("═══════════════════════════════════════════════════");
Info($"Tablas: {Model.Tables.Count}");
Info($"Relaciones: {Model.Relationships.Count}");
Info($"Medidas: {Model.AllMeasures.Count()}");
Info("");
Info("⚠️ PASO SIGUIENTE: File → Save to Power BI Desktop");
Info("Luego en Power BI Desktop: Construir las 5 páginas");
Info("según REPORT-GUIDE.md");
Info("═══════════════════════════════════════════════════");

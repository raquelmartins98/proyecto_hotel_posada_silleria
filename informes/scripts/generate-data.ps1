<#
.SYNOPSIS
    Generador de datos sintéticos para el Cierre Mensual Financiero
    Hotel Boutique Posada de Sillería - Toledo
    Destinado a Power BI

.DESCRIPTION
    Genera datos realistas con estacionalidad para Toledo (2025):
    - Temporada alta: Mar-Jun, Sep-Nov (turismo cultural)
    - Temporada muy alta: Semana Santa (Abr), Corpus Christi (Jun)
    - Temporada baja: Jul-Ago (calor extremo), Ene-Feb (frío)
    - Media: Dic (Navidad)
#>

$OutputDir = Join-Path $PSScriptRoot "..\data"
New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

# ─────────────────────────────────────────────
# PARÁMETROS DEL HOTEL
# ─────────────────────────────────────────────
$HotelParams = @{
    Habitaciones         = 12
    ADR_Base            = 200
    ADR_Baja            = 155
    ADR_Alta            = 285
    ADR_MuyAlta         = 330
    Ocupacion_Alta      = 0.82
    Ocupacion_Baja      = 0.42
    Ocupacion_MuyAlta   = 0.92
    Ocupacion_Media     = 0.65
}

# Factor estacional mensual (multiplicador de ingresos base)
$Estacionalidad = @{
    1  = @{Factor = 0.70; Etiqueta = "Temporada Baja - Invierno"; Ocu = $HotelParams.Ocupacion_Baja; ADR_Mult = 0.85}
    2  = @{Factor = 0.65; Etiqueta = "Temporada Baja - Invierno"; Ocu = $HotelParams.Ocupacion_Baja; ADR_Mult = 0.80}
    3  = @{Factor = 0.85; Etiqueta = "Temporada Media - Inicio Primavera"; Ocu = 0.60; ADR_Mult = 1.00}
    4  = @{Factor = 1.00; Etiqueta = "Temporada MUY Alta - Semana Santa"; Ocu = $HotelParams.Ocupacion_MuyAlta; ADR_Mult = 1.50}
    5  = @{Factor = 1.00; Etiqueta = "Temporada Alta - Primavera"; Ocu = $HotelParams.Ocupacion_Alta; ADR_Mult = 1.30}
    6  = @{Factor = 1.05; Etiqueta = "Temporada MUY Alta - Corpus Christi"; Ocu = $HotelParams.Ocupacion_MuyAlta; ADR_Mult = 1.55}
    7  = @{Factor = 0.60; Etiqueta = "Temporada Baja - Calor"; Ocu = $HotelParams.Ocupacion_Baja; ADR_Mult = 0.78}
    8  = @{Factor = 0.55; Etiqueta = "Temporada Baja - Calor extremo"; Ocu = 0.38; ADR_Mult = 0.75}
    9  = @{Factor = 0.95; Etiqueta = "Temporada Alta - Vuelta turismo"; Ocu = $HotelParams.Ocupacion_Alta; ADR_Mult = 1.20}
    10 = @{Factor = 0.90; Etiqueta = "Temporada Alta - Otoño"; Ocu = $HotelParams.Ocupacion_Alta; ADR_Mult = 1.15}
    11 = @{Factor = 0.80; Etiqueta = "Temporada Media - Otoño tardío"; Ocu = 0.60; ADR_Mult = 0.95}
    12 = @{Factor = 0.85; Etiqueta = "Temporada Media - Navidad"; Ocu = 0.65; ADR_Mult = 1.10}
}

# ─────────────────────────────────────────────
# DIMENSIONES
# ─────────────────────────────────────────────

# DIM_DATE
Write-Host "Generando DimDate..."
$DimDate = @()
for ($m = 1; $m -le 12; $m++) {
    $MonthName = (Get-Culture).DateTimeFormat.GetMonthName($m)
    $Quarter = [Math]::Ceiling($m / 3)
    $DiasMes = [DateTime]::DaysInMonth(2025, $m)
    
    # Días del mes que son fin de semana
    $WeekendDays = 0
    for ($d = 1; $d -le $DiasMes; $d++) {
        $DayOfWeek = (Get-Date -Year 2025 -Month $m -Day $d).DayOfWeek
        if ($DayOfWeek -eq [DayOfWeek]::Saturday -or $DayOfWeek -eq [DayOfWeek]::Sunday) {
            $WeekendDays++
        }
    }
    
    $DimDate += [PSCustomObject]@{
        DateKey          = 20250000 + $m * 100 + 1
        Year             = 2025
        MonthNumber      = $m
        MonthName        = $MonthName
        MonthShort       = $MonthName.Substring(0,3)
        Quarter          = "Q$Quarter"
        YearQuarter      = "2025-Q$Quarter"
        DiasDelMes       = $DiasMes
        WeekendDays      = $WeekendDays
        WeekdayDays      = $DiasMes - $WeekendDays
        Estacion         = $Estacionalidad[$m].Etiqueta
        IsTemporadaAlta  = $Estacionalidad[$m].Factor -ge 0.85
        Periodo          = "2025-$($m.ToString("00"))"
    }
}

# DIM_ACCOUNT - Plan de Cuentas
Write-Host "Generando DimAccount..."
$DimAccount = @(
    # ── INGRESOS ──
    [PSCustomObject]@{AccountKey = 1;  AccountCode = "401000"; AccountName = "Ingreso Habitaciones";     AccountType = "Ingreso";    FinancialClass = "Revenue";  IsRevenue = $true;  IsExpense = $false; DepartmentDefault = "Habitaciones";  OrderBy = 1}
    [PSCustomObject]@{AccountKey = 2;  AccountCode = "402000"; AccountName = "Ingreso Restaurante";      AccountType = "Ingreso";    FinancialClass = "Revenue";  IsRevenue = $true;  IsExpense = $false; DepartmentDefault = "Restaurante";  OrderBy = 2}
    [PSCustomObject]@{AccountKey = 3;  AccountCode = "403000"; AccountName = "Ingreso Bar & Terraza";    AccountType = "Ingreso";    FinancialClass = "Revenue";  IsRevenue = $true;  IsExpense = $false; DepartmentDefault = "Restaurante";  OrderBy = 3}
    [PSCustomObject]@{AccountKey = 4;  AccountCode = "404000"; AccountName = "Ingreso Spa";              AccountType = "Ingreso";    FinancialClass = "Revenue";  IsRevenue = $true;  IsExpense = $false; DepartmentDefault = "Spa";          OrderBy = 4}
    [PSCustomObject]@{AccountKey = 5;  AccountCode = "405000"; AccountName = "Ingreso Eventos";          AccountType = "Ingreso";    FinancialClass = "Revenue";  IsRevenue = $true;  IsExpense = $false; DepartmentDefault = "Eventos";      OrderBy = 5}
    [PSCustomObject]@{AccountKey = 6;  AccountCode = "406000"; AccountName = "Otros Ingresos";           AccountType = "Ingreso";    FinancialClass = "Revenue";  IsRevenue = $true;  IsExpense = $false; DepartmentDefault = "Habitaciones";  OrderBy = 6}
    # ── GASTOS OPERATIVOS ──
    [PSCustomObject]@{AccountKey = 7;  AccountCode = "501000"; AccountName = "Gastos de Personal";       AccountType = "Gasto";      FinancialClass = "OpEx";     IsRevenue = $false; IsExpense = $true;  DepartmentDefault = "General";      OrderBy = 7}
    [PSCustomObject]@{AccountKey = 8;  AccountCode = "502000"; AccountName = "Limpieza y Lavandería";    AccountType = "Gasto";      FinancialClass = "OpEx";     IsRevenue = $false; IsExpense = $true;  DepartmentDefault = "Habitaciones";  OrderBy = 8}
    [PSCustomObject]@{AccountKey = 9;  AccountCode = "503000"; AccountName = "Suministros y Amenities";  AccountType = "Gasto";      FinancialClass = "COGS";     IsRevenue = $false; IsExpense = $true;  DepartmentDefault = "Habitaciones";  OrderBy = 9}
    [PSCustomObject]@{AccountKey = 10; AccountCode = "504000"; AccountName = "Marketing y Comisiones";   AccountType = "Gasto";      FinancialClass = "OpEx";     IsRevenue = $false; IsExpense = $true;  DepartmentDefault = "General";      OrderBy = 10}
    [PSCustomObject]@{AccountKey = 11; AccountCode = "505000"; AccountName = "Mantenimiento y Reparaciones"; AccountType = "Gasto"; FinancialClass = "OpEx";   IsRevenue = $false; IsExpense = $true;  DepartmentDefault = "General";      OrderBy = 11}
    [PSCustomObject]@{AccountKey = 12; AccountCode = "506000"; AccountName = "Servicios Públicos (Luz, Agua, Gas)"; AccountType = "Gasto"; FinancialClass = "OpEx"; IsRevenue = $false; IsExpense = $true; DepartmentDefault = "General"; OrderBy = 12}
    [PSCustomObject]@{AccountKey = 13; AccountCode = "507000"; AccountName = "Gastos Administrativos";   AccountType = "Gasto";      FinancialClass = "OpEx";     IsRevenue = $false; IsExpense = $true;  DepartmentDefault = "General";      OrderBy = 13}
    [PSCustomObject]@{AccountKey = 14; AccountCode = "508000"; AccountName = "Seguros y Licencias";      AccountType = "Gasto";      FinancialClass = "Fixed";    IsRevenue = $false; IsExpense = $true;  DepartmentDefault = "General";      OrderBy = 14}
    [PSCustomObject]@{AccountKey = 15; AccountCode = "509000"; AccountName = "Coste F&B (Food Cost)";    AccountType = "Gasto";      FinancialClass = "COGS";     IsRevenue = $false; IsExpense = $true;  DepartmentDefault = "Restaurante";  OrderBy = 15}
    [PSCustomObject]@{AccountKey = 16; AccountCode = "510000"; AccountName = "Coste Productos Spa";      AccountType = "Gasto";      FinancialClass = "COGS";     IsRevenue = $false; IsExpense = $true;  DepartmentDefault = "Spa";          OrderBy = 16}
    [PSCustomObject]@{AccountKey = 17; AccountCode = "511000"; AccountName = "Comisiones OTAs";          AccountType = "Gasto";      FinancialClass = "COGS";     IsRevenue = $false; IsExpense = $true;  DepartmentDefault = "Habitaciones";  OrderBy = 17}
    [PSCustomObject]@{AccountKey = 18; AccountCode = "512000"; AccountName = "Gastos Varios";            AccountType = "Gasto";      FinancialClass = "OpEx";     IsRevenue = $false; IsExpense = $true;  DepartmentDefault = "General";      OrderBy = 18}
    # ── NO OPERATIVOS ──
    [PSCustomObject]@{AccountKey = 19; AccountCode = "601000"; AccountName = "Depreciación y Amortización"; AccountType = "Gasto";  FinancialClass = "NonOp";  IsRevenue = $false; IsExpense = $true; DepartmentDefault = "General"; OrderBy = 19}
    [PSCustomObject]@{AccountKey = 20; AccountCode = "602000"; AccountName = "Gastos Financieros";       AccountType = "Gasto";      FinancialClass = "NonOp";    IsRevenue = $false; IsExpense = $true;  DepartmentDefault = "General";      OrderBy = 20}
)

# DIM_DEPARTMENT
Write-Host "Generando DimDepartment..."
$DimDepartment = @(
    [PSCustomObject]@{DepartmentKey = 1;  DepartmentCode = "ROOMS";   DepartmentName = "Habitaciones";  IsRevenueCenter = $true;  OrderBy = 1; Color = "#1E88E5"}
    [PSCustomObject]@{DepartmentKey = 2;  DepartmentCode = "FNB";     DepartmentName = "Restaurante";   IsRevenueCenter = $true;  OrderBy = 2; Color = "#43A047"}
    [PSCustomObject]@{DepartmentKey = 3;  DepartmentCode = "SPA";     DepartmentName = "Spa";           IsRevenueCenter = $true;  OrderBy = 3; Color = "#8E24AA"}
    [PSCustomObject]@{DepartmentKey = 4;  DepartmentCode = "EVENTS";  DepartmentName = "Eventos";       IsRevenueCenter = $true;  OrderBy = 4; Color = "#FB8C00"}
    [PSCustomObject]@{DepartmentKey = 5;  DepartmentCode = "GEN";     DepartmentName = "General";       IsRevenueCenter = $false; OrderBy = 5; Color = "#546E7A"}
)

# ─────────────────────────────────────────────
# GENEACIÓN DE DATOS FINANCIEROS
# ─────────────────────────────────────────────

Write-Host "Generando FactActuals y FactBudget..."

$FactActuals = @()
$FactBudget = @()
$RoomStats = @()

$Random = [System.Random]::new(42)  # Seed for reproducibility

foreach ($mes in 1..12) {
    $est = $Estacionalidad[$mes]
    $diasMes = [DateTime]::DaysInMonth(2025, $mes)
    $diasFinSemana = $DimDate[$mes-1].WeekendDays
    $diasSemana = $DimDate[$mes-1].WeekdayDays
    
    $ocuActual = $est.Ocu + ($Random.NextDouble() - 0.5) * 0.08
    $ocuActual = [Math]::Max(0.30, [Math]::Min(0.95, $ocuActual))
    $adrMult = $est.ADR_Mult + ($Random.NextDouble() - 0.5) * 0.10
    $adrActual = $HotelParams.ADR_Base * $adrMult
    
    $nochesOcupadas = [Math]::Round($HotelParams.Habitaciones * $diasMes * $ocuActual)
    $ingresoHabitaciones = $nochesOcupadas * $adrActual
    
    # Budget (menos ruido, más "plan")
    $ocuBudget = $est.Ocu + ($Random.NextDouble() - 0.5) * 0.03
    $ocuBudget = [Math]::Max(0.35, [Math]::Min(0.93, $ocuBudget))
    $adrBudget = $HotelParams.ADR_Base * $est.ADR_Mult * (1 + ($Random.NextDouble() - 0.5) * 0.04)
    $nochesBudget = [Math]::Round($HotelParams.Habitaciones * $diasMes * $ocuBudget)
    $ingresoHabitacionesBudget = $nochesBudget * $adrBudget
    
    # ── ROOM STATS ──
    $RoomStats += [PSCustomObject]@{
        DateKey       = 20250000 + $mes * 100 + 1
        Year          = 2025
        Month         = $mes
        MonthName     = $DimDate[$mes-1].MonthName
        ADR_Actual    = [Math]::Round($adrActual, 2)
        ADR_Budget    = [Math]::Round($adrBudget, 2)
        Ocupacion_Actual = [Math]::Round($ocuActual * 100, 1)
        Ocupacion_Budget = [Math]::Round($ocuBudget * 100, 1)
        NochesOcupadas_Actual = $nochesOcupadas
        NochesOcupadas_Budget = $nochesBudget
        HabitacionesDisponibles = $HotelParams.Habitaciones * $diasMes
        RevPAR_Actual = [Math]::Round($adrActual * $ocuActual, 2)
        RevPAR_Budget = [Math]::Round($adrBudget * $ocuBudget, 2)
    }
    
    # ── INGRESOS POR DEPARTAMENTO (Actual y Budget) ──
    # Habitaciones (ya calculado)
    $actual_rooms  = [Math]::Round($ingresoHabitaciones, 0)
    $budget_rooms  = [Math]::Round($ingresoHabitacionesBudget, 0)
    
    # Restaurante: proporcional a ocupación + ruido
    $fnbBase = 18000 * $est.Factor
    $actual_fnb_rest = [Math]::Round($fnbBase * (1 + ($Random.NextDouble()-0.5)*0.12), 0)
    $budget_fnb_rest = [Math]::Round($fnbBase * (1 + ($Random.NextDouble()-0.5)*0.04), 0)
    
    # Bar & Terraza
    $barBase = 5500 * $est.Factor
    if ($mes -in 6..8) { $barBase *= 1.3 } # terraza en verano aunque haya menos ocupación, los que vienen consumen más
    $actual_fnb_bar = [Math]::Round($barBase * (1 + ($Random.NextDouble()-0.5)*0.15), 0)
    $budget_fnb_bar = [Math]::Round($barBase * (1 + ($Random.NextDouble()-0.5)*0.05), 0)
    
    # Spa: proporcional a ocupación
    $spaBase = 5000 * $est.Factor
    $actual_spa = [Math]::Round($spaBase * (1 + ($Random.NextDouble()-0.5)*0.15), 0)
    $budget_spa = [Math]::Round($spaBase * (1 + ($Random.NextDouble()-0.5)*0.05), 0)
    
    # Eventos: más discrecional, algunos meses tienen congresos
    $eventosBase = 3000 * $est.Factor
    if ($mes -in 4,5,6,9,10) { $eventosBase *= 2.5 } # temporada de bodas y congresos
    $actual_events = [Math]::Round($eventosBase * (1 + ($Random.NextDouble()-0.5)*0.30), 0)
    $budget_events = [Math]::Round($eventosBase * (1 + ($Random.NextDouble()-0.5)*0.10), 0)
    
    # Otros ingresos
    $otrosBase = 2000 * $est.Factor
    $actual_otros = [Math]::Round($otrosBase * (1 + ($Random.NextDouble()-0.5)*0.20), 0)
    $budget_otros = [Math]::Round($otrosBase * (1 + ($Random.NextDouble()-0.5)*0.05), 0)
    
    # Total Revenue
    $actual_revenue_total = $actual_rooms + $actual_fnb_rest + $actual_fnb_bar + $actual_spa + $actual_events + $actual_otros
    $budget_revenue_total = $budget_rooms + $budget_fnb_rest + $budget_fnb_bar + $budget_spa + $budget_events + $budget_otros
    
    # ── GASTOS (Actual y Budget) ──
    # Personal: 35-40% de ingresos, cierta rigidez (no se ajusta al 100% con ocupación)
    $personalBase = 0.37 * $actual_revenue_total
    $personalBudget = 0.36 * $budget_revenue_total
    # Ajuste por convenio: subida salarial anual del 3%
    $personalBase *= 1.03
    $personalBudget *= 1.03
    $actual_personal = [Math]::Round($personalBase * (1 + ($Random.NextDouble()-0.5)*0.05), 0)
    $budget_personal = [Math]::Round($personalBudget * (1 + ($Random.NextDouble()-0.5)*0.02), 0)
    
    # Limpieza y lavandería
    $actual_cleaning = [Math]::Round((3500 + $nochesOcupadas * 3.5) * (1 + ($Random.NextDouble()-0.5)*0.08), 0)
    $budget_cleaning = [Math]::Round((3500 + $nochesBudget * 3.5) * (1 + ($Random.NextDouble()-0.5)*0.03), 0)
    
    # Suministros y amenities
    $actual_supplies = [Math]::Round((1200 + $nochesOcupadas * 2.8) * (1 + ($Random.NextDouble()-0.5)*0.10), 0)
    $budget_supplies = [Math]::Round((1200 + $nochesBudget * 2.8) * (1 + ($Random.NextDouble()-0.5)*0.03), 0)
    
    # Marketing
    $actual_mkt = [Math]::Round(0.045 * $actual_revenue_total * (1 + ($Random.NextDouble()-0.5)*0.12), 0)
    $budget_mkt = [Math]::Round(0.045 * $budget_revenue_total * (1 + ($Random.NextDouble()-0.5)*0.04), 0)
    
    # Mantenimiento
    $actual_maint = [Math]::Round((2500 + $actual_revenue_total * 0.015) * (1 + ($Random.NextDouble()-0.5)*0.15), 0)
    $budget_maint = [Math]::Round((2500 + $budget_revenue_total * 0.015) * (1 + ($Random.NextDouble()-0.5)*0.05), 0)
    
    # Servicios públicos
    $actual_utilities = [Math]::Round((1800 + $nochesOcupadas * 1.2) * (1 + ($Random.NextDouble()-0.5)*0.08), 0)
    $budget_utilities = [Math]::Round((1800 + $nochesBudget * 1.2) * (1 + ($Random.NextDouble()-0.5)*0.03), 0)
    # Verano: más electricidad (aire acondicionado)
    if ($mes -in 6..9) { $actual_utilities = [Math]::Round($actual_utilities * 1.25); $budget_utilities = [Math]::Round($budget_utilities * 1.20) }
    # Invierno: más calefacción
    if ($mes -in 1..2 -or $mes -eq 12) { $actual_utilities = [Math]::Round($actual_utilities * 1.15); $budget_utilities = [Math]::Round($budget_utilities * 1.12) }
    
    # Gastos administrativos
    $actual_admin = [Math]::Round((2800 + $actual_revenue_total * 0.008) * (1 + ($Random.NextDouble()-0.5)*0.10), 0)
    $budget_admin = [Math]::Round((2800 + $budget_revenue_total * 0.008) * (1 + ($Random.NextDouble()-0.5)*0.03), 0)
    
    # Seguros y licencias (fijo mensual)
    $actual_insurance = 1450 + [Math]::Round(($Random.NextDouble()-0.5)*100, 0)
    $budget_insurance = 1450
    
    # Food Cost (35% del ingreso de restaurante + bar)
    $actual_foodcost = [Math]::Round(0.35 * ($actual_fnb_rest + $actual_fnb_bar) * (1 + ($Random.NextDouble()-0.5)*0.08), 0)
    $budget_foodcost = [Math]::Round(0.33 * ($budget_fnb_rest + $budget_fnb_bar) * (1 + ($Random.NextDouble()-0.5)*0.03), 0)
    
    # Productos Spa
    $actual_spacost = [Math]::Round(0.22 * $actual_spa * (1 + ($Random.NextDouble()-0.5)*0.10), 0)
    $budget_spacost = [Math]::Round(0.20 * $budget_spa * (1 + ($Random.NextDouble()-0.5)*0.04), 0)
    
    # Comisiones OTAs (15% de ingreso habitaciones)
    $actual_otas = [Math]::Round(0.15 * $actual_rooms * (1 + ($Random.NextDouble()-0.5)*0.06), 0)
    $budget_otas = [Math]::Round(0.14 * $budget_rooms * (1 + ($Random.NextDouble()-0.5)*0.03), 0)
    
    # Gastos varios
    $actual_misc = [Math]::Round((800 + $actual_revenue_total * 0.005) * (1 + ($Random.NextDouble()-0.5)*0.20), 0)
    $budget_misc = [Math]::Round((800 + $budget_revenue_total * 0.005) * (1 + ($Random.NextDouble()-0.5)*0.05), 0)
    
    # Depreciación (fija)
    $actual_depreciation = 4200
    $budget_depreciation = 4200
    
    # Gastos financieros
    $actual_financial = 1800 + [Math]::Round(($Random.NextDouble()-0.5)*200, 0)
    $budget_financial = 1800
    
    # ── GENERAR REGISTROS FACT TABLE ──
    $dateKey = 20250000 + $mes * 100 + 1
    $randomDelta = 0  # lo usamos inline ya
    
    # Mapeo: AccountKey -> [actual, budget]
    $accountsData = @(
        @{Key = 1;  Actual = $actual_rooms;      Budget = $budget_rooms}
        @{Key = 2;  Actual = $actual_fnb_rest;   Budget = $budget_fnb_rest}
        @{Key = 3;  Actual = $actual_fnb_bar;    Budget = $budget_fnb_bar}
        @{Key = 4;  Actual = $actual_spa;        Budget = $budget_spa}
        @{Key = 5;  Actual = $actual_events;     Budget = $budget_events}
        @{Key = 6;  Actual = $actual_otros;      Budget = $budget_otros}
        @{Key = 7;  Actual = $actual_personal;   Budget = $budget_personal}
        @{Key = 8;  Actual = $actual_cleaning;   Budget = $budget_cleaning}
        @{Key = 9;  Actual = $actual_supplies;   Budget = $budget_supplies}
        @{Key = 10; Actual = $actual_mkt;        Budget = $budget_mkt}
        @{Key = 11; Actual = $actual_maint;      Budget = $budget_maint}
        @{Key = 12; Actual = $actual_utilities;  Budget = $budget_utilities}
        @{Key = 13; Actual = $actual_admin;      Budget = $budget_admin}
        @{Key = 14; Actual = $actual_insurance;  Budget = $budget_insurance}
        @{Key = 15; Actual = $actual_foodcost;   Budget = $budget_foodcost}
        @{Key = 16; Actual = $actual_spacost;    Budget = $budget_spacost}
        @{Key = 17; Actual = $actual_otas;       Budget = $budget_otas}
        @{Key = 18; Actual = $actual_misc;       Budget = $budget_misc}
        @{Key = 19; Actual = $actual_depreciation; Budget = $budget_depreciation}
        @{Key = 20; Actual = $actual_financial;  Budget = $budget_financial}
    )
    
    # Asignar departamento apropiado según cuenta
    foreach ($acct in $accountsData) {
        $account = $DimAccount | Where-Object { $_.AccountKey -eq $acct.Key }
        
        # Determinar departamento según cuenta y tipo
        $deptKey = 5 # General por defecto
        switch ($acct.Key) {
            1  { $deptKey = 1 } # Rooms
            2  { $deptKey = 2 } # Restaurante
            3  { $deptKey = 2 } # Restaurante (bar)
            4  { $deptKey = 3 } # Spa
            5  { $deptKey = 4 } # Eventos
            6  { $deptKey = 1 } # Otros -> Rooms
            8  { $deptKey = 1 } # Limpieza -> Rooms
            9  { $deptKey = 1 } # Amenities -> Rooms
            15 { $deptKey = 2 } # Food cost -> Restaurante
            16 { $deptKey = 3 } # Spa cost -> Spa
            17 { $deptKey = 1 } # OTAs -> Rooms
            7  { $deptKey = 5 } # Personal -> General (se prorratea)
        }
        
        $FactActuals += [PSCustomObject]@{
            DateKey      = $dateKey
            AccountKey   = $acct.Key
            DepartmentKey = $deptKey
            Amount       = $acct.Actual
            Scenario     = "Actual"
            Version      = "Cierre Mensual"
            Currency     = "EUR"
            LastModified = Get-Date -Year 2025 -Month $mes -Day 28 -Format "yyyy-MM-dd"
        }
        
        $FactBudget += [PSCustomObject]@{
            DateKey      = $dateKey
            AccountKey   = $acct.Key
            DepartmentKey = $deptKey
            Amount       = $acct.Budget
            Scenario     = "Budget"
            Version      = "Presupuesto 2025"
            Currency     = "EUR"
            LastModified = "2024-12-15"
        }
    }
}

# ─────────────────────────────────────────────
# TABLA DE ALERTAS / UMBRALES
# ─────────────────────────────────────────────
Write-Host "Generando alertas sintéticas..."

$AlertTypes = @(
    [PSCustomObject]@{AlertCode = "REV_DROP";   AlertName = "Caída de Ingresos vs Presupuesto";         Severity = "CRITICAL"; Threshold = -0.10; MetricName = "RevenueVariance";  Description = "Ingresos totales caen >10% vs presupuesto"}
    [PSCustomObject]@{AlertCode = "REV_WARN";   AlertName = "Desviación negativa en Ingresos";          Severity = "WARNING";  Threshold = -0.05; MetricName = "RevenueVariance";  Description = "Ingresos totales caen >5% vs presupuesto"}
    [PSCustomObject]@{AlertCode = "OCC_DROP";   AlertName = "Caída de Ocupación";                      Severity = "WARNING";  Threshold = -0.08; MetricName = "OccupancyVariance"; Description = "Ocupación cae >8pp vs presupuesto"}
    [PSCustomObject]@{AlertCode = "ADR_DROP";   AlertName = "Caída de Tarifa Media";                   Severity = "WARNING";  Threshold = -0.08; MetricName = "ADRVariance";      Description = "ADR cae >8% vs presupuesto"}
    [PSCustomObject]@{AlertCode = "GOP_ALERT";  AlertName = "Margen GOP por debajo de objetivo";        Severity = "CRITICAL"; Threshold = -0.05; MetricName = "GOPMarginVar";    Description = "Margen GOP cae >5pp vs objetivo"}
    [PSCustomObject]@{AlertCode = "COST_SPIKE"; AlertName = "Disparo en Costes Operativos";            Severity = "CRITICAL"; Threshold = 0.10;  MetricName = "OpExVariance";    Description = "Gastos operativos >10% sobre presupuesto"}
    [PSCustomObject]@{AlertCode = "COST_WARN";  AlertName = "Sobrecoste en Personal";                  Severity = "WARNING";  Threshold = 0.06;  MetricName = "PayrollVariance"; Description = "Gastos de personal >6% sobre presupuesto"}
    [PSCustomObject]@{AlertCode = "FOOD_COST";  AlertName = "Food Cost por encima de objetivo";        Severity = "WARNING";  Threshold = 0.04;  MetricName = "FoodCostPct";    Description = "Food cost >35% vs objetivo 33%"}
    [PSCustomObject]@{AlertCode = "EBITDA_WARN";AlertName = "EBITDA por debajo de presupuesto";         Severity = "CRITICAL"; Threshold = -0.10; MetricName = "EBITDAVar";       Description = "EBITDA >10% por debajo de presupuesto"}
)

# ─────────────────────────────────────────────
# EXPORTAR CSV
# ─────────────────────────────────────────────
Write-Host "Exportando CSVs..." -ForegroundColor Green

$DimDate | Export-Csv -Path (Join-Path $OutputDir "DimDate.csv") -NoTypeInformation -Encoding UTF8
$DimAccount | Export-Csv -Path (Join-Path $OutputDir "DimAccount.csv") -NoTypeInformation -Encoding UTF8
$DimDepartment | Export-Csv -Path (Join-Path $OutputDir "DimDepartment.csv") -NoTypeInformation -Encoding UTF8
$FactActuals | Export-Csv -Path (Join-Path $OutputDir "FactActuals.csv") -NoTypeInformation -Encoding UTF8
$FactBudget | Export-Csv -Path (Join-Path $OutputDir "FactBudget.csv") -NoTypeInformation -Encoding UTF8
$RoomStats | Export-Csv -Path (Join-Path $OutputDir "DimRoomStats.csv") -NoTypeInformation -Encoding UTF8
$AlertTypes | Export-Csv -Path (Join-Path $OutputDir "DimAlerts.csv") -NoTypeInformation -Encoding UTF8

# ─────────────────────────────────────────────
# TABLA RESUMEN POR MES
# ─────────────────────────────────────────────
Write-Host "`n=== RESUMEN MENSUAL 2025 ===" -ForegroundColor Yellow
Write-Host ""

$resumen = @()
foreach ($mes in 1..12) {
    $actuals = $FactActuals | Where-Object { $_.DateKey -eq (20250000 + $mes*100 + 1) }
    $budgets = $FactBudget | Where-Object { $_.DateKey -eq (20250000 + $mes*100 + 1) }
    
    $ingActual = ($actuals | Where-Object { ($_.AccountKey -ge 1 -and $_.AccountKey -le 6) } | Measure-Object Amount -Sum).Sum
    $ingBudget = ($budgets | Where-Object { ($_.AccountKey -ge 1 -and $_.AccountKey -le 6) } | Measure-Object Amount -Sum).Sum
    
    $gastosActual = ($actuals | Where-Object { ($_.AccountKey -ge 7) } | Measure-Object Amount -Sum).Sum
    $gastosBudget = ($budgets | Where-Object { ($_.AccountKey -ge 7) } | Measure-Object Amount -Sum).Sum
    
    $gopActual = $ingActual - $gastosActual
    $gopBudget = $ingBudget - $gastosBudget
    
    $rs = $RoomStats | Where-Object { $_.Month -eq $mes }
    
    Write-Host ("{0,-10} Ing: {1,8:F0}€ vs {2,8:F0}€ | GOP: {3,8:F0}€ vs {4,8:F0}€ | Ocu: {5,5:F1}% ADR: {6,7:F2}€" -f `
        $DimDate[$mes-1].MonthShort, $ingActual, $ingBudget, $gopActual, $gopBudget, $rs.Ocupacion_Actual, $rs.ADR_Actual)
}

<#
.SYNOPSIS
    Genera proyecto PBIP para Power BI Desktop
    Hotel Boutique Posada de Sillería - Cierre Mensual Financiero
#>

$ProjectRoot = Join-Path $PSScriptRoot "..\PosadaDeSilleria.pbip"
$DataDir = Join-Path $PSScriptRoot "..\data"

foreach ($d in @("$ProjectRoot\.pbi","$ProjectRoot\PosadaDeSilleria.SemanticModel\.pbi","$ProjectRoot\PosadaDeSilleria.Report\.pbi","$ProjectRoot\PosadaDeSilleria.Report\pages","$ProjectRoot\data")) {
    New-Item -ItemType Directory -Path $d -Force | Out-Null
}

Copy-Item -Path "$DataDir\*.csv" -Destination "$ProjectRoot\data\" -Force
Write-Host "CSVs copiados a data/" -ForegroundColor Green

$utf8 = [System.Text.UTF8Encoding]::new($true)

# localSettings
[System.IO.File]::WriteAllText("$ProjectRoot\.pbi\localSettings.json", '{"localSettings":{"editorSettings":{"showQueryEditorInNewPane":false}}}', $utf8)
[System.IO.File]::WriteAllText("$ProjectRoot\PosadaDeSilleria.SemanticModel\.pbi\localSettings.json", '{"localSettings":{"isOpen":false,"isHidden":false,"showQueryEditor":false}}', $utf8)
[System.IO.File]::WriteAllText("$ProjectRoot\PosadaDeSilleria.Report\.pbi\localSettings.json", '{"localSettings":{"isOpen":false,"isHidden":false,"showQueryEditor":false}}', $utf8)

# ─── DEFINITION.PBIR (report - simple) ───
$pbir = '{"name":"PosadaDeSilleria","compatibilityLevel":1603,"report":{"reportName":"Posada de Silleria - Cierre Mensual","autoPageCreate":false,"page":[{"name":"ExecutiveDashboard","displayName":"Executive Dashboard","order":0,"filters":[],"visuals":[]},{"name":"RevenueDeepDive","displayName":"Revenue Deep Dive","order":1,"filters":[],"visuals":[]},{"name":"ExpenseCostControl","displayName":"Expense and Cost Control","order":2,"filters":[],"visuals":[]},{"name":"Profitability","displayName":"Profitability and GOP","order":3,"filters":[],"visuals":[]},{"name":"AlertsNarrative","displayName":"Alerts and Narrativa","order":4,"filters":[],"visuals":[]}]}}'
[System.IO.File]::WriteAllText("$ProjectRoot\PosadaDeSilleria.Report\definition.pbir", $pbir, $utf8)
Write-Host "definition.pbir generado" -ForegroundColor Green

# ─── DEFINITION.PBISM ───
# Build as a structured PowerShell object and serialize to JSON
# This avoids all quoting/escaping issues

function JsonSafe($s) {
    # Escape string for JSON embedding
    return ($s -replace '"', '\"' -replace "`r`n", "\n" -replace "`n", "\n" -replace "`t", "\t")
}

# Build tables
$tables = @()

# Helper: create column definition
function Col($n, $t, $s, $f, $sc) {
    $c = [ordered]@{name=$n; dataType=$t; sourceColumn=$n; lineageTag=[guid]::NewGuid().ToString("N").Substring(0,15); summarizeBy=$s}
    if ($f) { $c.formatString = $f }
    if ($sc) { $c.sortByColumn = $sc }
    return $c
}

# Helper: create partition with M expression
function Part($name, $csv) {
    $m = @"
let
    Source = Csv.Document(File.Contents("data\$csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.None]),
    #"Promoted Headers" = Table.PromoteHeaders(Source, [PromoteAllScalars=true])
in
    #"Promoted Headers"
"@
    return @{name=$name; mode="import"; source=@{type="m"; expression=$m}; lineageTag=[guid]::NewGuid().ToString("N").Substring(0,15)}
}

# Helper: create measure
function Meas($n, $e, $f, $df) {
    return @{name=$n; lineageTag=[guid]::NewGuid().ToString("N").Substring(0,15); expression=$e; formatString=$f; displayFolder=$df}
}

# DimDate
$tables += [ordered]@{
    name="DimDate"; lineageTag="t01"
    columns=@(
        (Col "DateKey" "int64" "none" $null $null),
        (Col "Year" "int64" "none" "0" $null),
        (Col "MonthNumber" "int64" "none" "0" $null),
        (Col "MonthName" "string" "none" $null "MonthNumber"),
        (Col "MonthShort" "string" "none" $null "MonthNumber"),
        (Col "Quarter" "string" "none" $null $null),
        (Col "YearQuarter" "string" "none" $null $null),
        (Col "DiasDelMes" "int64" "none" "0" $null),
        (Col "WeekendDays" "int64" "none" "0" $null),
        (Col "WeekdayDays" "int64" "none" "0" $null),
        (Col "Estacion" "string" "none" $null $null),
        (Col "IsTemporadaAlta" "bool" "none" $null $null),
        (Col "Periodo" "string" "none" $null $null)
    )
    partitions=@((Part "DimDate" "DimDate.csv"))
}
# DimAccount
$tables += [ordered]@{
    name="DimAccount"; lineageTag="t02"
    columns=@(
        (Col "AccountKey" "int64" "none" "0" $null),
        (Col "AccountCode" "string" "none" $null $null),
        (Col "AccountName" "string" "none" $null "OrderBy"),
        (Col "AccountType" "string" "none" $null $null),
        (Col "FinancialClass" "string" "none" $null $null),
        (Col "IsRevenue" "bool" "none" $null $null),
        (Col "IsExpense" "bool" "none" $null $null),
        (Col "DepartmentDefault" "string" "none" $null $null),
        (Col "OrderBy" "int64" "none" "0" $null)
    )
    partitions=@((Part "DimAccount" "DimAccount.csv"))
}
# DimDepartment
$tables += [ordered]@{
    name="DimDepartment"; lineageTag="t03"
    columns=@(
        (Col "DepartmentKey" "int64" "none" "0" $null),
        (Col "DepartmentCode" "string" "none" $null $null),
        (Col "DepartmentName" "string" "none" $null "OrderBy"),
        (Col "IsRevenueCenter" "bool" "none" $null $null),
        (Col "OrderBy" "int64" "none" "0" $null),
        (Col "Color" "string" "none" $null $null)
    )
    partitions=@((Part "DimDepartment" "DimDepartment.csv"))
}
# DimRoomStats
$tables += [ordered]@{
    name="DimRoomStats"; lineageTag="t04"
    columns=@(
        (Col "DateKey" "int64" "none" "0" $null),
        (Col "Year" "int64" "none" "0" $null),
        (Col "Month" "int64" "none" "0" $null),
        (Col "MonthName" "string" "none" $null "Month"),
        @{name="ADR_Actual"; dataType="double"; sourceColumn="ADR_Actual"; lineageTag="c0405"; summarizeBy="none"; formatString="#,##0.00"},
        @{name="ADR_Budget"; dataType="double"; sourceColumn="ADR_Budget"; lineageTag="c0406"; summarizeBy="none"; formatString="#,##0.00"},
        @{name="Ocupacion_Actual"; dataType="double"; sourceColumn="Ocupacion_Actual"; lineageTag="c0407"; summarizeBy="none"; formatString="0.0%"},
        @{name="Ocupacion_Budget"; dataType="double"; sourceColumn="Ocupacion_Budget"; lineageTag="c0408"; summarizeBy="none"; formatString="0.0%"},
        @{name="NochesOcupadas_Actual"; dataType="int64"; sourceColumn="NochesOcupadas_Actual"; lineageTag="c0409"; summarizeBy="sum"; formatString="0"},
        @{name="NochesOcupadas_Budget"; dataType="int64"; sourceColumn="NochesOcupadas_Budget"; lineageTag="c0410"; summarizeBy="sum"; formatString="0"},
        @{name="HabitacionesDisponibles"; dataType="int64"; sourceColumn="HabitacionesDisponibles"; lineageTag="c0411"; summarizeBy="none"; formatString="0"},
        @{name="RevPAR_Actual"; dataType="double"; sourceColumn="RevPAR_Actual"; lineageTag="c0412"; summarizeBy="none"; formatString="#,##0.00"},
        @{name="RevPAR_Budget"; dataType="double"; sourceColumn="RevPAR_Budget"; lineageTag="c0413"; summarizeBy="none"; formatString="#,##0.00"}
    )
    partitions=@((Part "DimRoomStats" "DimRoomStats.csv"))
}
# DimAlerts
$tables += [ordered]@{
    name="DimAlerts"; lineageTag="t05"
    columns=@(
        (Col "AlertCode" "string" "none" $null $null),
        (Col "AlertName" "string" "none" $null $null),
        (Col "Severity" "string" "none" $null $null),
        @{name="Threshold"; dataType="double"; sourceColumn="Threshold"; lineageTag="c0504"; summarizeBy="none"; formatString="0.00"},
        (Col "MetricName" "string" "none" $null $null),
        (Col "Description" "string" "none" $null $null)
    )
    partitions=@((Part "DimAlerts" "DimAlerts.csv"))
}
# FactActuals
$tables += [ordered]@{
    name="FactActuals"; lineageTag="t06"
    columns=@(
        (Col "DateKey" "int64" "none" "0" $null),
        (Col "AccountKey" "int64" "none" "0" $null),
        (Col "DepartmentKey" "int64" "none" "0" $null),
        @{name="Amount"; dataType="double"; sourceColumn="Amount"; lineageTag="c0604"; summarizeBy="sum"; formatString="#,##0"},
        (Col "Scenario" "string" "none" $null $null),
        (Col "Version" "string" "none" $null $null),
        (Col "Currency" "string" "none" $null $null),
        (Col "LastModified" "string" "none" $null $null)
    )
    partitions=@((Part "FactActuals" "FactActuals.csv"))
    measures=@(
        (Meas "Total Revenue" 'CALCULATE(SUM(FactActuals[Amount]), DimAccount[IsRevenue] = TRUE())' '#,##0 €' '01 - Ingresos')
        (Meas "Total Revenue Budget" 'CALCULATE(SUM(FactBudget[Amount]), DimAccount[IsRevenue] = TRUE())' '#,##0 €' '01 - Ingresos')
        (Meas "Revenue Variance" '[Total Revenue] - [Total Revenue Budget]' '#,##0 €' '01 - Ingresos')
        (Meas "Revenue Variance %" 'DIVIDE([Revenue Variance], [Total Revenue Budget], 0)' '+0.0%;-0.0%;0.0%' '01 - Ingresos')
        (Meas "Revenue Rooms" 'CALCULATE([Total Revenue], DimDepartment[DepartmentCode] = "ROOMS")' '#,##0 €' '01 - Ingresos')
        (Meas "Revenue F&B" 'CALCULATE([Total Revenue], DimDepartment[DepartmentCode] = "FNB")' '#,##0 €' '01 - Ingresos')
        (Meas "Revenue Spa" 'CALCULATE([Total Revenue], DimDepartment[DepartmentCode] = "SPA")' '#,##0 €' '01 - Ingresos')
        (Meas "Revenue Events" 'CALCULATE([Total Revenue], DimDepartment[DepartmentCode] = "EVENTS")' '#,##0 €' '01 - Ingresos')
        (Meas "Total OpEx" 'CALCULATE(SUM(FactActuals[Amount]), DimAccount[FinancialClass] = "OpEx" || DimAccount[FinancialClass] = "COGS")' '#,##0 €' '02 - Gastos')
        (Meas "Total OpEx Budget" 'CALCULATE(SUM(FactBudget[Amount]), DimAccount[FinancialClass] = "OpEx" || DimAccount[FinancialClass] = "COGS")' '#,##0 €' '02 - Gastos')
        (Meas "OpEx Variance" '[Total OpEx] - [Total OpEx Budget]' '#,##0 €' '02 - Gastos')
        (Meas "OpEx Variance %" 'DIVIDE([OpEx Variance], [Total OpEx Budget], 0)' '+0.0%;-0.0%;0.0%' '02 - Gastos')
        (Meas "Payroll" 'CALCULATE(SUM(FactActuals[Amount]), DimAccount[AccountCode] = "501000")' '#,##0 €' '02 - Gastos')
        (Meas "Payroll % Revenue" 'DIVIDE([Payroll], [Total Revenue], 0)' '0.0%' '02 - Gastos')
        (Meas "Food Cost %" 'VAR FC = CALCULATE(SUM(FactActuals[Amount]), DimAccount[AccountCode] = "509000")'#13#10'VAR FNB = [Revenue F&B]'#13#10'RETURN DIVIDE(FC, FNB, 0)' '0.0%' '02 - Gastos')
        (Meas "GOP" '[Total Revenue] - [Total OpEx]' '#,##0 €' '03 - GOP')
        (Meas "GOP Budget" '[Total Revenue Budget] - [Total OpEx Budget]' '#,##0 €' '03 - GOP')
        (Meas "GOP Variance" '[GOP] - [GOP Budget]' '#,##0 €' '03 - GOP')
        (Meas "GOP Margin" 'DIVIDE([GOP], [Total Revenue], 0)' '0.0%' '03 - GOP')
        (Meas "GOP Margin Budget" 'DIVIDE([GOP Budget], [Total Revenue Budget], 0)' '0.0%' '03 - GOP')
        (Meas "GOP Margin Variance" '[GOP Margin] - [GOP Margin Budget]' '+0.0%;-0.0%' '03 - GOP')
        (Meas "EBITDA" '[GOP] - CALCULATE(SUM(FactActuals[Amount]), DimAccount[FinancialClass] = "Fixed")' '#,##0 €' '04 - EBITDA')
        (Meas "EBITDA Margin" 'DIVIDE([EBITDA], [Total Revenue], 0)' '0.0%' '04 - EBITDA')
        (Meas "Alert Revenue Traffic" ('VAR v = [Revenue Variance %]' + [char]13 + [char]10 + 'RETURN SWITCH(TRUE(),' + [char]13 + [char]10 + '    v < -0.10, "CRITICAL",' + [char]13 + [char]10 + '    v < -0.05, "WARNING",' + [char]13 + [char]10 + '    v < 0, "MINOR",' + [char]13 + [char]10 + '    "OK")') '' '05 - Alertas')
        (Meas "Alert OpEx Traffic" ('VAR v = [OpEx Variance %]' + [char]13 + [char]10 + 'RETURN SWITCH(TRUE(),' + [char]13 + [char]10 + '    v > 0.10, "CRITICAL",' + [char]13 + [char]10 + '    v > 0.06, "WARNING",' + [char]13 + [char]10 + '    v > 0.03, "MINOR",' + [char]13 + [char]10 + '    "OK")') '' '05 - Alertas')
        (Meas "Alert GOP Traffic" ('VAR v = [GOP Margin Variance]' + [char]13 + [char]10 + 'RETURN SWITCH(TRUE(),' + [char]13 + [char]10 + '    v < -0.05, "CRITICAL",' + [char]13 + [char]10 + '    v < -0.03, "WARNING",' + [char]13 + [char]10 + '    v < 0, "MINOR",' + [char]13 + [char]10 + '    "OK")') '' '05 - Alertas')
        (Meas "Alert Status" ('VAR t = {("Revenue",[Alert Revenue Traffic]),("OpEx",[Alert OpEx Traffic]),("GOP",[Alert GOP Traffic])}' + [char]13 + [char]10 + 'VAR w = MINX(t, SWITCH([Value],"CRITICAL",1,"WARNING",2,"MINOR",3,"OK",4,99))' + [char]13 + [char]10 + 'RETURN SWITCH(w,1,"CRITICAL",2,"WARNING",3,"MINOR","OK")') '' '05 - Alertas')
        (Meas "Critical Alert Count" ('VAR t = {("Revenue",[Alert Revenue Traffic]),("OpEx",[Alert OpEx Traffic]),("GOP",[Alert GOP Traffic])}' + [char]13 + [char]10 + 'RETURN COUNTROWS(FILTER(t, [Value] = "CRITICAL"))') '0' '05 - Alertas')
    )
}
# FactBudget
$tables += [ordered]@{
    name="FactBudget"; lineageTag="t07"
    columns=@(
        (Col "DateKey" "int64" "none" "0" $null),
        (Col "AccountKey" "int64" "none" "0" $null),
        (Col "DepartmentKey" "int64" "none" "0" $null),
        @{name="Amount"; dataType="double"; sourceColumn="Amount"; lineageTag="c0704"; summarizeBy="sum"; formatString="#,##0"},
        (Col "Scenario" "string" "none" $null $null),
        (Col "Version" "string" "none" $null $null),
        (Col "Currency" "string" "none" $null $null),
        (Col "LastModified" "string" "none" $null $null)
    )
    partitions=@((Part "FactBudget" "FactBudget.csv"))
}

# Relationships
$relationships = @()
$relDefs = @(
    @("r01","DimDate","DateKey","FactActuals","DateKey"),
    @("r02","DimDate","DateKey","FactBudget","DateKey"),
    @("r03","DimDate","DateKey","DimRoomStats","DateKey"),
    @("r04","DimAccount","AccountKey","FactActuals","AccountKey"),
    @("r05","DimAccount","AccountKey","FactBudget","AccountKey"),
    @("r06","DimDepartment","DepartmentKey","FactActuals","DepartmentKey"),
    @("r07","DimDepartment","DepartmentKey","FactBudget","DepartmentKey")
)
foreach ($r in $relDefs) {
    $relationships += [ordered]@{name=$r[0]; lineageTag=$r[0]; fromTable=$r[1]; fromColumn=$r[2]; toTable=$r[3]; toColumn=$r[4]; crossFilteringBehavior="oneDirection"}
}

# Build complete model
$model = [ordered]@{
    name = "PosadaDeSilleria"
    compatibilityLevel = 1603
    model = [ordered]@{
        culture = "es-ES"
        collation = "Modern_Spanish_CI_AS"
        dataAccessOptions = [ordered]@{ returnErrorValuesAsNull = $true }
        defaultPowerBIDataSourceVersion = "powerBI_V3"
        tables = $tables
        relationships = $relationships
    }
}

$json = $model | ConvertTo-Json -Depth 12
[System.IO.File]::WriteAllText("$ProjectRoot\PosadaDeSilleria.SemanticModel\definition.pbism", $json, $utf8)
Write-Host "definition.pbism generado ($(($json | Measure-Object -Character).Characters) chars)" -ForegroundColor Green

# ─── SUMMARY ───
Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "PROYECTO PBIP GENERADO" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "Ubicacion: $ProjectRoot" -ForegroundColor Yellow
Write-Host ""
Get-ChildItem -Path $ProjectRoot -Recurse -File | ForEach-Object {
    Write-Host "  $($_.FullName.Replace($ProjectRoot,''))"
}
Write-Host ""
Write-Host "Tablas: $($tables.Count)" -ForegroundColor White
Write-Host "Relaciones: $($relationships.Count)" -ForegroundColor White
Write-Host "Medidas: $($tables | ForEach-Object { if ($_.measures) { $_.measures.Count } else { 0 } } | Measure-Object -Sum).Sum" -ForegroundColor White
Write-Host ""
Write-Host "Para abrir: File > Open > Project > seleccionar carpeta:" -ForegroundColor Yellow
Write-Host "  $ProjectRoot" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan

<#
.SYNOPSIS
    Genera proyecto PBIP para Power BI Desktop
    Hotel Boutique Posada de Sillería
#>

$ProjectRoot = Join-Path $PSScriptRoot "..\PosadaDeSilleria.pbip"
$DataDir = Join-Path $PSScriptRoot "..\data"

# ─── Estructura de carpetas ───
foreach ($d in @("$ProjectRoot\.pbi","$ProjectRoot\PosadaDeSilleria.SemanticModel\.pbi","$ProjectRoot\PosadaDeSilleria.Report\.pbi","$ProjectRoot\PosadaDeSilleria.Report\pages","$ProjectRoot\data")) {
    New-Item -ItemType Directory -Path $d -Force | Out-Null
}
Copy-Item -Path "$DataDir\*.csv" -Destination "$ProjectRoot\data\" -Force
Write-Host "CSVs copiados" -ForegroundColor Green

$utf8 = [System.Text.UTF8Encoding]::new($true)

# ─── localSettings ───
[System.IO.File]::WriteAllText("$ProjectRoot\.pbi\localSettings.json", '{"localSettings":{"editorSettings":{"showQueryEditorInNewPane":false}}}', $utf8)
[System.IO.File]::WriteAllText("$ProjectRoot\PosadaDeSilleria.SemanticModel\.pbi\localSettings.json", '{"localSettings":{"isOpen":false,"isHidden":false,"showQueryEditor":false}}', $utf8)
[System.IO.File]::WriteAllText("$ProjectRoot\PosadaDeSilleria.Report\.pbi\localSettings.json", '{"localSettings":{"isOpen":false,"isHidden":false,"showQueryEditor":false}}', $utf8)

# ─── Helpers ───
function M($csv) {
    # Generate M expression for CSV loading - properly escaped for JSON
    $m = "let`r`n"
    $m += "    Source = Csv.Document(File.Contents(""data\\$csv""), [Delimiter="","", Encoding=65001, QuoteStyle=QuoteStyle.None]),`r`n"
    $m += '    #"Promoted Headers" = Table.PromoteHeaders(Source, [PromoteAllScalars=true])' + "`r`n"
    $m += "in`r`n"
    $m += '    #"Promoted Headers"'
    # Escape for JSON embedding (String.Replace avoids regex issues)
    $m = $m.Replace('\', '\\').Replace('"', '\"').Replace("`r`n", "\r\n").Replace("`n", "\r\n").Replace("`t", "\\t")
    return $m
}

# ─── DEFINITION.PBIR ───
$pbir = '{' +
'"name":"PosadaDeSilleria","compatibilityLevel":1603,' +
'"report":{' +
  '"reportName":"Posada de Silleria - Cierre Mensual","autoPageCreate":false,' +
  '"page":[' +
    '{"name":"ExecutiveDashboard","displayName":"Executive Dashboard","order":0,"filters":[],"visuals":[]},' +
    '{"name":"RevenueDeepDive","displayName":"Revenue Deep Dive","order":1,"filters":[],"visuals":[]},' +
    '{"name":"ExpenseCostControl","displayName":"Expense and Cost Control","order":2,"filters":[],"visuals":[]},' +
    '{"name":"Profitability","displayName":"Profitability and GOP","order":3,"filters":[],"visuals":[]},' +
    '{"name":"AlertsNarrative","displayName":"Alerts and Narrativa","order":4,"filters":[],"visuals":[]}' +
  ']' +
'}}'
[System.IO.File]::WriteAllText("$ProjectRoot\PosadaDeSilleria.Report\definition.pbir", $pbir, $utf8)
Write-Host "definition.pbir OK" -ForegroundColor Green

# ─── Build model JSON using StringBuilder ───
$sb = New-Object System.Text.StringBuilder

# Euro sign
$euro = [char]0x20AC

# Helper to add JSON key-value (string)
# Helper: column JSON
function Col($n, $t, $s, $f, $sc) {
    $null = $sb.Append('{"name":"' + $n + '","dataType":"' + $t + '","sourceColumn":"' + $n + '","lineageTag":"' + [guid]::NewGuid().ToString("N").Substring(0,12) + '","summarizeBy":"' + $s + '"')
    if ($f) { $null = $sb.Append(',"formatString":"' + $f + '"') }
    if ($sc) { $null = $sb.Append(',"sortByColumn":"' + $sc + '"') }
    $null = $sb.Append('},')
}

# Helper: partition JSON
function Part($csv) {
    $null = $sb.Append('{"name":"' + $csv.Replace('.csv','') + '","mode":"import","source":{"type":"m","expression":"' + (M $csv) + '"},"lineageTag":"' + [guid]::NewGuid().ToString("N").Substring(0,12) + '"}')
}

# Helper: measure JSON
function Meas($n, $e, $f, $df) {
    # Escape DAX expression for JSON: newlines, quotes, backslashes, tabs
    $eJson = $e.Replace('\', '\\').Replace('"', '\"').Replace("`r`n", "\n").Replace("`n", "\n").Replace("`r", "\n").Replace("`t", "\\t")
    $null = $sb.Append('{"name":"' + $n + '","lineageTag":"' + [guid]::NewGuid().ToString("N").Substring(0,12) + '","expression":"' + $eJson + '","formatString":"' + $f + '","displayFolder":"' + $df + '"},')
}

# ─── BUILD MODEL ───
$null = $sb.Append('{"name":"PosadaDeSilleria","compatibilityLevel":1603,"model":{')
$null = $sb.Append('"culture":"es-ES","collation":"Modern_Spanish_CI_AS",')
$null = $sb.Append('"dataAccessOptions":{"returnErrorValuesAsNull":true},')
$null = $sb.Append('"defaultPowerBIDataSourceVersion":"powerBI_V3",')
$null = $sb.Append('"tables":[')

# ── TABLE: DimDate ──
$null = $sb.Append('{"name":"DimDate","lineageTag":"t01","columns":[')
Col "DateKey" "int64" "none" $null $null
Col "Year" "int64" "none" "0" $null
Col "MonthNumber" "int64" "none" "0" $null
Col "MonthName" "string" "none" $null "MonthNumber"
Col "MonthShort" "string" "none" $null "MonthNumber"
Col "Quarter" "string" "none" $null $null
Col "YearQuarter" "string" "none" $null $null
Col "DiasDelMes" "int64" "none" "0" $null
Col "WeekendDays" "int64" "none" "0" $null
Col "WeekdayDays" "int64" "none" "0" $null
Col "Estacion" "string" "none" $null $null
Col "IsTemporadaAlta" "bool" "none" $null $null
Col "Periodo" "string" "none" $null $null
$sb.Length -= 1  # remove trailing comma
$null = $sb.Append('],"partitions":['); Part "DimDate.csv"; $sb.Length -= 1; $null = $sb.Append(']},')

# ── TABLE: DimAccount ──
$null = $sb.Append('{"name":"DimAccount","lineageTag":"t02","columns":[')
Col "AccountKey" "int64" "none" "0" $null
Col "AccountCode" "string" "none" $null $null
Col "AccountName" "string" "none" $null "OrderBy"
Col "AccountType" "string" "none" $null $null
Col "FinancialClass" "string" "none" $null $null
Col "IsRevenue" "bool" "none" $null $null
Col "IsExpense" "bool" "none" $null $null
Col "DepartmentDefault" "string" "none" $null $null
Col "OrderBy" "int64" "none" "0" $null
$sb.Length -= 1
$null = $sb.Append('],"partitions":['); Part "DimAccount.csv"; $sb.Length -= 1; $null = $sb.Append(']},')

# ── TABLE: DimDepartment ──
$null = $sb.Append('{"name":"DimDepartment","lineageTag":"t03","columns":[')
Col "DepartmentKey" "int64" "none" "0" $null
Col "DepartmentCode" "string" "none" $null $null
Col "DepartmentName" "string" "none" $null "OrderBy"
Col "IsRevenueCenter" "bool" "none" $null $null
Col "OrderBy" "int64" "none" "0" $null
Col "Color" "string" "none" $null $null
$sb.Length -= 1
$null = $sb.Append('],"partitions":['); Part "DimDepartment.csv"; $sb.Length -= 1; $null = $sb.Append(']},')

# ── TABLE: DimRoomStats ──
$null = $sb.Append('{"name":"DimRoomStats","lineageTag":"t04","columns":[')
Col "DateKey" "int64" "none" "0" $null
Col "Year" "int64" "none" "0" $null
Col "Month" "int64" "none" "0" $null
Col "MonthName" "string" "none" $null "Month"
Col "ADR_Actual" "double" "none" "#,##0.00" $null
Col "ADR_Budget" "double" "none" "#,##0.00" $null
Col "Ocupacion_Actual" "double" "none" "0.0%" $null
Col "Ocupacion_Budget" "double" "none" "0.0%" $null
Col "NochesOcupadas_Actual" "int64" "sum" "0" $null
Col "NochesOcupadas_Budget" "int64" "sum" "0" $null
Col "HabitacionesDisponibles" "int64" "none" "0" $null
Col "RevPAR_Actual" "double" "none" "#,##0.00" $null
Col "RevPAR_Budget" "double" "none" "#,##0.00" $null
$sb.Length -= 1
$null = $sb.Append('],"partitions":['); Part "DimRoomStats.csv"; $sb.Length -= 1; $null = $sb.Append(']},')

# ── TABLE: DimAlerts ──
$null = $sb.Append('{"name":"DimAlerts","lineageTag":"t05","columns":[')
Col "AlertCode" "string" "none" $null $null
Col "AlertName" "string" "none" $null $null
Col "Severity" "string" "none" $null $null
Col "Threshold" "double" "none" "0.00" $null
Col "MetricName" "string" "none" $null $null
Col "Description" "string" "none" $null $null
$sb.Length -= 1
$null = $sb.Append('],"partitions":['); Part "DimAlerts.csv"; $sb.Length -= 1; $null = $sb.Append(']},')

# ── TABLE: FactActuals ──
$null = $sb.Append('{"name":"FactActuals","lineageTag":"t06","columns":[')
Col "DateKey" "int64" "none" "0" $null
Col "AccountKey" "int64" "none" "0" $null
Col "DepartmentKey" "int64" "none" "0" $null
$null = $sb.Append('{"name":"Amount","dataType":"double","sourceColumn":"Amount","lineageTag":"c06amt","summarizeBy":"sum","formatString":"#,##0"},')
Col "Scenario" "string" "none" $null $null
Col "Version" "string" "none" $null $null
Col "Currency" "string" "none" $null $null
Col "LastModified" "string" "none" $null $null
$sb.Length -= 1
$null = $sb.Append('],"partitions":['); Part "FactActuals.csv"; $sb.Length -= 1; $null = $sb.Append('],"measures":[')

# ── MEASURES for FactActuals ──
$fs = "#,##0 $euro"  # format string with euro

Meas "Total Revenue" 'CALCULATE(SUM(FactActuals[Amount]), DimAccount[IsRevenue] = TRUE())' $fs '01 - Ingresos'
Meas "Total Revenue Budget" 'CALCULATE(SUM(FactBudget[Amount]), DimAccount[IsRevenue] = TRUE())' $fs '01 - Ingresos'
Meas "Revenue Variance" '[Total Revenue] - [Total Revenue Budget]' $fs '01 - Ingresos'
Meas "Revenue Variance %" 'DIVIDE([Revenue Variance], [Total Revenue Budget], 0)' '+0.0%;-0.0%;0.0%' '01 - Ingresos'
Meas "Revenue Rooms" 'CALCULATE([Total Revenue], DimDepartment[DepartmentCode] = "ROOMS")' $fs '01 - Ingresos'
Meas "Revenue F&B" 'CALCULATE([Total Revenue], DimDepartment[DepartmentCode] = "FNB")' $fs '01 - Ingresos'
Meas "Revenue Spa" 'CALCULATE([Total Revenue], DimDepartment[DepartmentCode] = "SPA")' $fs '01 - Ingresos'
Meas "Revenue Events" 'CALCULATE([Total Revenue], DimDepartment[DepartmentCode] = "EVENTS")' $fs '01 - Ingresos'

Meas "Total OpEx" 'CALCULATE(SUM(FactActuals[Amount]), DimAccount[FinancialClass] = "OpEx" || DimAccount[FinancialClass] = "COGS")' $fs '02 - Gastos'
Meas "Total OpEx Budget" 'CALCULATE(SUM(FactBudget[Amount]), DimAccount[FinancialClass] = "OpEx" || DimAccount[FinancialClass] = "COGS")' $fs '02 - Gastos'
Meas "OpEx Variance" '[Total OpEx] - [Total OpEx Budget]' $fs '02 - Gastos'
Meas "OpEx Variance %" 'DIVIDE([OpEx Variance], [Total OpEx Budget], 0)' '+0.0%;-0.0%;0.0%' '02 - Gastos'
Meas "Payroll" 'CALCULATE(SUM(FactActuals[Amount]), DimAccount[AccountCode] = "501000")' $fs '02 - Gastos'
Meas "Payroll % Revenue" 'DIVIDE([Payroll], [Total Revenue], 0)' '0.0%' '02 - Gastos'

# Food Cost % with multi-line DAX
$fcDax = "VAR FC = CALCULATE(SUM(FactActuals[Amount]), DimAccount[AccountCode] = `"509000`")`r`nVAR FNB = [Revenue F&B]`r`nRETURN DIVIDE(FC, FNB, 0)"
Meas "Food Cost %" $fcDax '0.0%' '02 - Gastos'

Meas "GOP" '[Total Revenue] - [Total OpEx]' $fs '03 - GOP'
Meas "GOP Budget" '[Total Revenue Budget] - [Total OpEx Budget]' $fs '03 - GOP'
Meas "GOP Variance" '[GOP] - [GOP Budget]' $fs '03 - GOP'
Meas "GOP Margin" 'DIVIDE([GOP], [Total Revenue], 0)' '0.0%' '03 - GOP'
Meas "GOP Margin Budget" 'DIVIDE([GOP Budget], [Total Revenue Budget], 0)' '0.0%' '03 - GOP'
Meas "GOP Margin Variance" '[GOP Margin] - [GOP Margin Budget]' '+0.0%;-0.0%' '03 - GOP'
Meas "EBITDA" '[GOP] - CALCULATE(SUM(FactActuals[Amount]), DimAccount[FinancialClass] = "Fixed")' $fs '04 - EBITDA'
Meas "EBITDA Margin" 'DIVIDE([EBITDA], [Total Revenue], 0)' '0.0%' '04 - EBITDA'

# Alert measures
$nl = "`r`n"  # newline for DAX
$alertRevDax = "VAR v = [Revenue Variance %]$nl`tRETURN SWITCH(TRUE(),$nl`t`tv < -0.10, ""CRITICAL"",$nl`t`tv < -0.05, ""WARNING"",$nl`t`tv < 0, ""MINOR"",$nl`t`t""OK"")"
$alertOpDax = "VAR v = [OpEx Variance %]$nl`tRETURN SWITCH(TRUE(),$nl`t`tv > 0.10, ""CRITICAL"",$nl`t`tv > 0.06, ""WARNING"",$nl`t`tv > 0.03, ""MINOR"",$nl`t`t""OK"")"
$alertGoDax = "VAR v = [GOP Margin Variance]$nl`tRETURN SWITCH(TRUE(),$nl`t`tv < -0.05, ""CRITICAL"",$nl`t`tv < -0.03, ""WARNING"",$nl`t`tv < 0, ""MINOR"",$nl`t`t""OK"")"
$alertStDax = "VAR t = {(""Revenue"",[Alert Revenue Traffic]),(""OpEx"",[Alert OpEx Traffic]),(""GOP"",[Alert GOP Traffic])}$nl`tVAR w = MINX(t, SWITCH([Value],""CRITICAL"",1,""WARNING"",2,""MINOR"",3,""OK"",4,99))$nl`tRETURN SWITCH(w,1,""CRITICAL"",2,""WARNING"",3,""MINOR"",""OK"")"
$alertCtDax = "VAR t = {(""Revenue"",[Alert Revenue Traffic]),(""OpEx"",[Alert OpEx Traffic]),(""GOP"",[Alert GOP Traffic])}$nl`tRETURN COUNTROWS(FILTER(t, [Value] = ""CRITICAL""))"

Meas "Alert Revenue Traffic" $alertRevDax '' '05 - Alertas'
Meas "Alert OpEx Traffic" $alertOpDax '' '05 - Alertas'
Meas "Alert GOP Traffic" $alertGoDax '' '05 - Alertas'
Meas "Alert Status" $alertStDax '' '05 - Alertas'
Meas "Critical Alert Count" $alertCtDax '0' '05 - Alertas'

$sb.Length -= 1  # remove trailing comma from last measure
$null = $sb.Append(']},')

# ── TABLE: FactBudget ──
$null = $sb.Append('{"name":"FactBudget","lineageTag":"t07","columns":[')
Col "DateKey" "int64" "none" "0" $null
Col "AccountKey" "int64" "none" "0" $null
Col "DepartmentKey" "int64" "none" "0" $null
$null = $sb.Append('{"name":"Amount","dataType":"double","sourceColumn":"Amount","lineageTag":"c07amt","summarizeBy":"sum","formatString":"#,##0"},')
Col "Scenario" "string" "none" $null $null
Col "Version" "string" "none" $null $null
Col "Currency" "string" "none" $null $null
Col "LastModified" "string" "none" $null $null
$sb.Length -= 1
$null = $sb.Append('],"partitions":['); Part "FactBudget.csv"; $sb.Length -= 1; $null = $sb.Append(']}')

$sb.Length -= 1  # remove trailing comma from last table
$null = $sb.Append('],"relationships":[')

# Relationships
$rels = @(
    @("r01","DimDate","DateKey","FactActuals","DateKey"),
    @("r02","DimDate","DateKey","FactBudget","DateKey"),
    @("r03","DimDate","DateKey","DimRoomStats","DateKey"),
    @("r04","DimAccount","AccountKey","FactActuals","AccountKey"),
    @("r05","DimAccount","AccountKey","FactBudget","AccountKey"),
    @("r06","DimDepartment","DepartmentKey","FactActuals","DepartmentKey"),
    @("r07","DimDepartment","DepartmentKey","FactBudget","DepartmentKey")
)
foreach ($r in $rels) {
    $null = $sb.Append('{"name":"' + $r[0] + '","lineageTag":"' + $r[0] + '","fromTable":"' + $r[1] + '","fromColumn":"' + $r[2] + '","toTable":"' + $r[3] + '","toColumn":"' + $r[4] + '","crossFilteringBehavior":"oneDirection"},')
}
$sb.Length -= 1
$null = $sb.Append(']}}')

# ─── WRITE FILE ───
$json = $sb.ToString()
[System.IO.File]::WriteAllText("$ProjectRoot\PosadaDeSilleria.SemanticModel\definition.pbism", $json, $utf8)
Write-Host "definition.pbism generado ($($json.Length) chars)" -ForegroundColor Green

# ─── SUMMARY ───
Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "PROYECTO PBIP GENERADO" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "Ubicacion: $ProjectRoot" -ForegroundColor Yellow
Write-Host ""
Get-ChildItem -Path $ProjectRoot -Recurse -File | ForEach-Object {
    $size = [math]::Round($_.Length / 1KB, 1)
    Write-Host "  $($_.FullName.Replace($ProjectRoot,'')) (${size} KB)"
}
Write-Host ""
Write-Host "Total tablas: 7" -ForegroundColor White
Write-Host "Total relaciones: 7" -ForegroundColor White
Write-Host "Total medidas: 29" -ForegroundColor White
Write-Host ""
Write-Host "Para abrir: File > Open > Project > seleccionar carpeta:" -ForegroundColor Yellow
Write-Host "  $ProjectRoot" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan

# Proyecto: Hotel Boutique Posada de la Sillería

## 🎯 Objetivo
Sistema de revenue management con comparador de precios dinámico, panel
de administración y backend en Insforge.

## ✅ Estado actual completado
- Backend Insforge: 9 tablas + 3 buckets + auth email/pass
- Datos iniciales: habitaciones, temporadas, eventos, competencia
- Histórico sintético 12 meses (mayo 2025 – abril 2026):
  · 2.529 reservas, ADR 147,87€, RevPAR 96,59€
  · 365 días de ocupación (media 65,3%) y tiempo
  · 12 meses de costes (417.453€/año)
  · Ingresos brutos 669.844€, margen +252.390€
- MCP de Insforge y Stitch conectados a OpenCode
- Diseño en Stitch del panel de administración (8 secciones)
- RLS activado en las 9 tablas del proyecto
- **Frontend conectado a Insforge vía endpoints REST** (sin rawsql):
  · `select()` / `create()` para código nuevo (REST directo)
  · `query()` / `mutate()` puente legacy (parsea SQL → REST)
  · 7 páginas públicas alimentadas con datos reales
  · Reservas e incidencias protegidas por RLS (requieren login)

## ✅ Últimos cambios (26/05/2026)

### Predicción.jsx — Página completa de predicción de ocupación
- **Frontend conectado al motor SARIMA**: tabla `predicciones` en Insforge (30 filas SARIMA)
- **3 tarjetas de escenarios**: Pesimista, Realista, Optimista con media calculada y Material Icons
- **Gráfica con abanico de incertidumbre**: 3 líneas (pesimista rojiza, realista dorada, optimista verde) + zona sombreada entre pesimista y optimista vía Areas apiladas Recharts
- **Leyenda** identificando las 3 líneas
- **Tabla de 30 días**: columnas Fecha, Pesimista, Realista, Optimista, Recomendación con badges de color:
  - 🟢 >75% → "Subir tarifa"
  - 🟡 50-75% → "Mantener"
  - 🔴 <50% → "Oferta/promoción"
- **Ruta** `/prediccion` registrada en App.jsx + enlace en navegación DashboardLayout
- **Script Python** `volcar_predicciones.py` para regenerar y subir predicciones a Insforge
- Fix encoding: caracteres UTF-8 correctos en todo el JSX (tildes, eñes)
- Sin dependencias adicionales (usa Recharts ya instalado)

### Panel derecho colapsable
- **DashboardLayout.jsx**: panel lateral derecho con toggle
- Plegado por defecto en páginas internas, desplegado en Dashboard
- Estado persiste entre navegación (no al recargar)
- Animación suave con transición CSS

### Costes.jsx — Rediseño completo desde Stitch
- **Layout**: formulario (izquierda) + gráfico (derecha) + tarjetas insight (abajo)
- **Formulario**: selector mes/año con carga automática, 5 campos de costes (Operativos, Mantenimiento, Personal, Suministros, Otros), total auto-calculado
- **Modo create/edit**: si existe registro para el mes/año, carga los datos para editar; si no, crea uno nuevo
- **Gráfico**: barras apiladas con Recharts, evolución 12 meses, leyenda por categoría
- **Tarjetas insight**: Optimización (% real calculado de datos), Alertas de Personal, Histórico
- Dependencia añadida: `recharts`

### insforge.js — Nuevas funciones REST
- `update(table, id, data)` — PATCH para editar registros existentes
- `remove(table, id)` — DELETE para eliminar registros

### motor_prediccion/ — Entorno Python para predicción (Bloque 1)
- **Carpeta**: `motor_prediccion/` en la raíz del proyecto
- **Virtualenv**: `.venv/` con Python 3.14.3 aislado del sistema
- **8 librerías instaladas** con versiones fijadas en `requirements.txt`:
  `pandas==3.0.3`, `numpy==2.4.6`, `statsmodels==0.14.6`,
  `pmdarima==2.1.1`, `matplotlib==3.10.9`, `scikit-learn==1.8.0`,
  `requests==2.34.2`, `python-dotenv==1.2.2`
- **Verificado**: `test_entorno.py` importa las 11 sub-librerías sin errores
- **Nota**: Todas con ruedas precompiladas para Windows/amd64 — sin errores de compilación
- **Conexion Insforge confirmada**: `test_conexion_insforge.py` lee 365 filas de `ocupacion_real` vía REST API con Anon Key correctamente. Listo para Bloque 2 (preparar series temporales para ARIMA/SARIMA).
- **Bloque 2 parte 1 completado**: `preparar_serie.py` construye serie temporal pandas desde Insforge. 365 días contiguos sin huecos, frecuencia diaria, media 65.27%, desviación ±22% (estacionalidad marcada). Gráfica guardada en `graficas/ocupacion_anual.png`.
- **Bloque 3 completado**: `modelo_arima.py` — ARIMA(5,1,2) entrenado con auto_arima. MAE=12.96%, RMSE=14.97%. Predice razonablemente pero sin estacionalidad se queda corto.
- **Bloque 4 completado**: `modelo_sarima.py` — SARIMA(2,1,1)(1,0,2,7) con estacionalidad semanal m=7. MAE bajó de 12.96 a 8.05 (**mejora del 38%**). RMSE de 14.97 a 10.56 (**mejora del 30%**). Gráfica comparativa guardada en `graficas/sarima_vs_arima.png`. La estacionalidad semanal es clave para ocupación hotelera (finde vs entre semana).
- **Bloque 5 completado**: `escenarios.py` — 3 escenarios de predicción sobre SARIMA(2,1,1)(1,0,2,7) entrenado con los 365 días completos. Predicción 30 días con IC 95%. Pesimista 38.1%, realista 66.5%, optimista 91.2% (recortado a rango 0-100%). Tabla de 30 días + gráfica `graficas/tres_escenarios.png`. El modelo captura el patrón semanal (findes altos, entre semana bajos).
- **Bloque 6.1 completado**: `modelo_holtwinters.py` — Tercer modelo (Holt-Winters ExponentialSmoothing) con estacionalidad semanal m=7. Mejor configuración: Add-Add (tendencia aditiva + estacionalidad aditiva), MAE=11.05, RMSE=12.11. Tabla comparativa: ARIMA 12.96 🥉, Holt-Winters 11.05 🥈, SARIMA 8.13 🥇. Gráfica `graficas/tres_modelos.png`. Holt-Winters aporta velocidad (entrenamiento instantáneo vs 1-3 min de SARIMA) ideal para dashboard en tiempo real.
- **Bloque 6.2 completado**: `ensemble.py` — Ensemble de los 3 modelos. Promedio simple MAE=9.91, ponderado MAE=9.55 (pesos: SARIMA 42.3%, Holt-Winters 31.1%, ARIMA 26.6%). SARIMA individual sigue ganando (MAE=8.13) — hallazgo válido: la estacionalidad semanal es tan dominante que mezclar modelos más débiles reduce precisión. Gráfica `graficas/ensemble_final.png`. **PARTE DE LOS 3 MODELOS COMPLETA.**
- **Bloque 7 COMPLETO**: `rag_base.py` + `rag_buscador.py` + `rag_respuestas.py` + `asistente.py` — RAG sin IA externa basado en datos reales del hotel. Asistente interactivo que responde en lenguaje natural sobre ocupación, precios, eventos y costes con recomendaciones accionables estilo revenue manager. Clasifica intenciones, extrae fechas, cruza datos de Insforge + predicción SARIMA. **MOTOR DE PREDICCIÓN COMPLETO (ARIMA+SARIMA+HoltWinters+ensemble+3 escenarios+RAG).**

## ⏭️ Próximo paso
- Conectar asistente RAG al frontend (opcional)
- Preparar presentación del proyecto
- Migrar ocupacion_real y costes_mensuales a rol authenticated

## 🐛 Fallos pendientes de revisar (próxima tanda)
- _(pendiente de detallar)_

## 🧾 Notas técnicas

### ⚠️ Codificación UTF-8 — caracteres corruptos en DB (solucionado)
**Problema**: 6 registros en `eventos_locales` y `temporadas` tenían
caracteres `�` (U+FFFD) en lugar de tildes y ñ (procesión, Sillería,
Constitución, Año, otoño).

**Causa**: Los datos se insertaron originalmente con una codificación
que no era UTF-8, probablemente durante la carga inicial por MCP
(`run-raw-sql`). PowerShell por defecto usa ISO-8859-1/Windows-1252
en consola, no UTF-8. Al enviar caracteres como ó, í, ñ desde la
terminal, se convierten a bytes inválidos y PostgreSQL los almacena
como U+FFFD.

**Solución**: 6 UPDATEs directos vía `run-raw-sql` con los nombres
correctos en UTF-8.

**Prevención para futuras inserciones**:
- ✅ Las inserciones desde el frontend (`create()` / `mutate()` via
  REST API) usan `Content-Type: application/json` → UTF-8 garantizado.
  No hay riesgo desde la app.
- ⚠️ Si se usa `run-raw-sql` desde MCP con caracteres especiales:
  anteponer `[Console]::OutputEncoding = [System.Text.Encoding]::UTF8`
  en PowerShell, o mejor aún, insertar datos via REST API directamente.
- ✅ El MCP `run-raw-sql` de Insforge maneja UTF-8 correctamente
  cuando el string SQL que se le pasa ya está en UTF-8. El problema
  original fue que el string llegó en otra codificación.

## 🗄️ Estado verificado en Insforge (19/05/2026)
| Tabla | Filas |
|---|---|
| reservas | 2.529 |
| habitaciones | 5 |
| temporadas | 7 |
| eventos_locales | 7 |
| tiempo_toledo | 365 |
| precios_competencia | 18 |
| costes_mensuales | 12 |
| ocupacion_real | 365 |
| incidencias | 0 |
| test_conexion (extra) | 1 |

## 🔑 Configuración (URLs públicas, NUNCA claves)
- API_BASE_URL Insforge: https://v63axieg.us-east.insforge.app

## 📝 Decisiones clave tomadas
- Modelo de pricing en dos fases: reglas explicables + ML encima
- Corpus Christi recibe multiplicador extra (la procesión pasa por la
  calle del hotel)
- Tabla reservas regenerada para ser coherente con ocupación real
- Hotel modelado con 19 habitaciones en 5 tipos

## 🔒 Seguridad (RLS en Insforge)
- RLS activado en las **9 tablas del proyecto**
- **Públicas** (rol `anon`): `habitaciones`, `temporadas`, `eventos_locales`,
  `precios_competencia`, `tiempo_toledo`
- **⚠️ TEMPORAL — lectura pública** (rol `anon`, pendiente migrar a
  `authenticated`): `ocupacion_real` y `costes_mensuales` — restringir
  cuando se monte el sistema de auth
- **Privadas** (solo rol `authenticated`): `reservas` e `incidencias` —
  las páginas de Reservas e Incidencias REQUIEREN login para mostrar datos.
  Con Anon Key devuelven 0 filas (verificado).

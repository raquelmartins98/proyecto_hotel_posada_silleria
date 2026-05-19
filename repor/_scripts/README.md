# Automatizacion para subir informes a /repor

Este directorio contiene herramientas para automatizar la subida de
informes y reportes al repositorio.

## Flujo recomendado

1. Creas un informe en Word (.docx) en tu Escritorio
2. El nombre debe empezar por `Informe_` o `Reporte_`
   Ej: `Informe_Ocupacion_2026_Q1.docx`, `Reporte_Eventos_Corpus.docx`
3. Ejecutas el script y el resto es automatico:
   - Se convierte a PDF
   - Se copia a /repor del repositorio
   - Se hace commit + push automatico
   - El DOCX original se archiva en _scripts/_procesados/

## Uso

### Una sola vez
```powershell
cd modelo-predictivo-revenue
python repor/_scripts/subir_informe.py
```

### Modo vigilante (cada 60s)
```powershell
python repor/_scripts/subir_informe.py --watch
```

### Cada 5 minutos
```powershell
python repor/_scripts/subir_informe.py --watch --interval 300
```

## Programar con Task Scheduler (Windows)

Para que se ejecute automaticamente cada hora:

1. Abre **Task Scheduler** (buscalo en Inicio)
2. Clic en **Create Task...**
3. **General**:
   - Nombre: `Subir Informes Hotel`
   - Marca "Run whether user is logged on or not"
4. **Triggers** -> **New...**:
   - Begin the task: `On a schedule`
   - Daily, repeat every `1 hour`, for `1 day`
5. **Actions** -> **New...**:
   - Action: `Start a program`
   - Program/script: `python`
   - Arguments: `repor/_scripts/subir_informe.py`
   - Start in: `C:\Users\raque\proyecto_hotel_posada_silleria\modelo-predictivo-revenue`
6. **OK** y lista

Para probarlo manualmente desde el Task Scheduler:
- Selecciona la tarea y clic en **Run**

## Convencion de nombres

```
Informe_<Tema>_<Ano>.pdf     — Informe anual o trimestral
Reporte_<Tema>_<Fecha>.pdf   — Reporte especifico
```

Ejemplos validos:
| Nombre del .docx | PDF generado |
|---|---|
| `Informe_Anual_2026.docx` | `Informe_Anual_2026.pdf` |
| `Reporte_Ocupacion_2026-06.docx` | `Reporte_Ocupacion_2026-06.pdf` |
| `Informe_Eventos_Corpus.docx` | `Informe_Eventos_Corpus.pdf` |

## Resolucion de problemas

| Sintoma | Causa | Solucion |
|---|---|---|
| "Not a git repository" | Ejecutas desde otro directorio | Corre desde la raiz del repo |
| `git push` falla | Sin acceso al remote | Configura `git remote` o usa token |
| Conversión falla | Falta python-docx o fpdf2 | `pip install python-docx fpdf2` |
| No encuentra archivos | Escritorio no detectado | Revisa DESKTOP en subir_informe.py |

El log completo esta en: `repor/_scripts/_logs/subir_informe.log`

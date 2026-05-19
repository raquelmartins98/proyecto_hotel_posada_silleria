#!/usr/bin/env python3
"""
Script watcher para subir informes a /repor del repositorio.

Funcionamiento:
  1. Escanea el Escritorio en busca de archivos cuyo nombre empiece
     por "Informe_" o "Reporte_" y terminen en .docx
  2. Convierte cada uno a PDF usando convertir_docx_a_pdf.py
  3. Copia el PDF a la carpeta /repor del repositorio
  4. Hace commit y push con mensaje descriptivo
  5. Mueve el DOCX original a una subcarpeta _procesados/ (para no
     reprocesarlo)
  6. Registra todo en un archivo de log

Uso:
    python subir_informe.py                        # Procesa todos los pendientes
    python subir_informe.py --watch                # Modo vigilante (cada 60s)
    python subir_informe.py --watch --interval 300 # Cada 5 minutos

Requisitos:
    - Python 3.12+
    - pip install python-docx fpdf2
    - git configurado con acceso al remote
"""

import argparse
import glob
import logging
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# ── Configuracion ────────────────────────────────────────
REPO_DIR = Path(__file__).resolve().parent.parent.parent  # raiz del repo
REPOR_DIR = REPO_DIR / 'repor'
CONVERTER = REPOR_DIR / 'convertir_docx_a_pdf.py'
SCRIPTS_DIR = REPOR_DIR / '_scripts'
LOG_DIR = SCRIPTS_DIR / '_logs'
PROCESADOS_DIR = SCRIPTS_DIR / '_procesados'

# Escritorio: detecta la carpeta correcta (OneDrive o local)
CANDIDATOS_DESKTOP = [
    Path.home() / 'OneDrive' / 'Escritorio',
    Path.home() / 'OneDrive' / 'Desktop',
    Path.home() / 'Escritorio',
    Path.home() / 'Desktop',
]
DESKTOP = None
for p in CANDIDATOS_DESKTOP:
    if p.exists():
        DESKTOP = p
        break

LOG_FILE = LOG_DIR / 'subir_informe.log'

PATRONES = ['Informe_*.docx', 'Reporte_*.docx']


# ── Logging ──────────────────────────────────────────────
def setup_logging():
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[
            logging.FileHandler(LOG_FILE, encoding='utf-8'),
            logging.StreamHandler(sys.stdout),
        ],
    )
    return logging.getLogger(__name__)


# ── Funciones ────────────────────────────────────────────
def buscar_docx_en_desktop(logger):
    """Busca archivos .docx en el Escritorio que coincidan con los patrones."""
    if DESKTOP is None:
        logger.error('No se pudo determinar la carpeta Escritorio.')
        return []

    encontrados = []
    for pat in PATRONES:
        patron_completo = str(DESKTOP / pat)
        for f in glob.glob(patron_completo):
            encontrados.append(Path(f))
    return encontrados


def convertir_a_pdf(docx_path, logger):
    """Convierte un DOCX a PDF usando convertir_docx_a_pdf.py."""
    pdf_name = docx_path.stem + '.pdf'
    pdf_temp = REPOR_DIR / pdf_name

    logger.info(f'Convirtiendo: {docx_path.name} -> {pdf_temp.name}')

    # Si el PDF ya existe en /repor, comprobamos si el DOCX es mas reciente
    if pdf_temp.exists():
        docx_mtime = os.path.getmtime(docx_path)
        pdf_mtime = os.path.getmtime(pdf_temp)
        if pdf_mtime >= docx_mtime:
            logger.info(f'  -> Saltando: {pdf_temp.name} ya existe y esta actualizado')
            return pdf_temp

    cmd = [
        sys.executable,
        str(CONVERTER),
        str(docx_path),
        str(pdf_temp),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

    if result.returncode != 0:
        logger.error(f'  -> Error en conversion:\n{result.stderr}')
        return None

    if pdf_temp.exists():
        logger.info(f'  -> PDF generado: {pdf_temp} ({pdf_temp.stat().st_size / 1024:.1f} KB)')
        return pdf_temp
    else:
        logger.error(f'  -> No se genero el PDF: {pdf_temp}')
        return None


def commit_y_push(pdf_path, logger):
    """Hace git add, commit y push del PDF nuevo."""
    os.chdir(REPO_DIR)

    # git add
    r = subprocess.run(['git', 'add', str(pdf_path)], capture_output=True, text=True)
    if r.returncode != 0:
        logger.error(f'Error en git add: {r.stderr}')
        return False

    # Verificar si hay algo que commitear
    r = subprocess.run(['git', 'diff', '--cached', '--quiet'], capture_output=True)
    if r.returncode == 0:
        logger.info('  -> No hay cambios nuevos que commitear')
        return True

    # Commit
    tema = pdf_path.stem.replace('Informe_', '').replace('Reporte_', '').replace('_', ' ')
    mensaje = f'docs(repor): anade {pdf_path.stem}'

    r = subprocess.run(['git', 'commit', '-m', mensaje], capture_output=True, text=True)
    if r.returncode != 0:
        logger.error(f'Error en git commit: {r.stderr}')
        return False
    logger.info(f'  -> Commit: {mensaje}')

    # Push
    r = subprocess.run(['git', 'push', 'origin', 'main'], capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        logger.error(f'Error en git push: {r.stderr}')
        return False
    logger.info('  -> Push a origin/main OK')

    return True


def archivar_original(docx_path, logger):
    """Mueve el DOCX original a _procesados/ para no reprocesarlo."""
    PROCESADOS_DIR.mkdir(parents=True, exist_ok=True)
    destino = PROCESADOS_DIR / docx_path.name

    # Si ya existe, anade timestamp
    if destino.exists():
        stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        destino = PROCESADOS_DIR / f'{docx_path.stem}_{stamp}{docx_path.suffix}'

    shutil.move(str(docx_path), str(destino))
    logger.info(f'  -> Original archivado: {destino.name}')


def procesar(logger):
    """Ejecuta el ciclo completo: buscar, convertir, commit, archivar."""
    logger.info('=' * 60)
    logger.info('INICIO - Buscando informes en el Escritorio...')

    docxs = buscar_docx_en_desktop(logger)
    if not docxs:
        logger.info('No se encontraron informes nuevos.')
        logger.info('FIN (sin cambios)')
        logger.info('')
        return

    logger.info(f'Encontrados {len(docxs)} archivo(s):')
    for d in docxs:
        logger.info(f'  - {d.name}')

    for docx_path in docxs:
        logger.info(f'--- Procesando: {docx_path.name} ---')

        pdf = convertir_a_pdf(docx_path, logger)
        if pdf is None:
            logger.warning(f'  -> Se omite {docx_path.name} por error de conversion')
            continue

        ok = commit_y_push(pdf, logger)
        if ok:
            archivar_original(docx_path, logger)
        else:
            logger.warning(f'  -> No se pudo subir {docx_path.name}. El DOCX queda en el Escritorio.')

    logger.info('FIN - Ciclo completado')
    logger.info('')


def modo_watch(interval, logger):
    """Ejecuta el ciclo en bucle cada `interval` segundos."""
    logger.info(f'MODO VIGILANTE activado (intervalo={interval}s)')
    logger.info(f'Escritorio: {DESKTOP}')
    logger.info(f'Esperando archivos: {", ".join(PATRONES)}')
    logger.info('Presiona Ctrl+C para detener.')
    logger.info('')

    while True:
        try:
            procesar(logger)
            time.sleep(interval)
        except KeyboardInterrupt:
            logger.info('Detenido por el usuario.')
            break
        except Exception as e:
            logger.error(f'Error inesperado: {e}')
            time.sleep(interval)


# ── Main ─────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description='Sube informes del Escritorio a /repor del repositorio.'
    )
    parser.add_argument(
        '--watch', action='store_true',
        help='Modo vigilante: ejecuta el ciclo cada N segundos'
    )
    parser.add_argument(
        '--interval', type=int, default=60,
        help='Intervalo en segundos para modo vigilante (default: 60)'
    )
    args = parser.parse_args()

    logger = setup_logging()

    logger.info(f'Repositorio: {REPO_DIR}')
    logger.info(f'Carpeta /repor: {REPOR_DIR}')
    logger.info(f'Escritorio detectado: {DESKTOP}')
    logger.info(f'Log: {LOG_FILE}')

    if args.watch:
        modo_watch(args.interval, logger)
    else:
        procesar(logger)


if __name__ == '__main__':
    main()

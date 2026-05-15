#!/usr/bin/env python3
"""
Punto de entrada para el Dashboard Streamlit del Revenue Management Engine.

Uso:
    python run_dashboard.py
    
    Esto lanza el dashboard en http://localhost:8501
"""

import subprocess
import sys
from pathlib import Path


def main():
    """Lanza la aplicación Streamlit."""
    dashboard_path = Path(__file__).parent / "revenue_engine" / "dashboard" / "app.py"
    
    cmd = [
        sys.executable, "-m", "streamlit", "run",
        str(dashboard_path),
        "--server.port", "8501",
        "--server.address", "0.0.0.0",
    ]
    
    subprocess.run(cmd)


if __name__ == "__main__":
    main()

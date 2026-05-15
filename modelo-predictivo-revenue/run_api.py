#!/usr/bin/env python3
"""
Punto de entrada para la API REST del Revenue Management Engine.

Uso:
    python run_api.py
    
    Esto lanza el servidor FastAPI en http://localhost:8000
    Documentación: http://localhost:8000/docs
"""

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "revenue_engine.api.app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )

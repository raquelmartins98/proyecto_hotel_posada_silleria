"""
Configuración de la aplicación FastAPI.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from revenue_engine.api.routes import router

app = FastAPI(
    title="Revenue Management API — Hotel Posada de la Sillería",
    description="API del modelo predictivo de revenue management para hotel boutique en Toledo",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS — permitir acceso desde dashboard Streamlit
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api/v1")

@app.get("/")
async def root():
    return {
        "app": "Revenue Management Engine",
        "hotel": "Hotel Posada de la Sillería (Toledo)",
        "version": "1.0.0",
        "docs": "/docs",
    }

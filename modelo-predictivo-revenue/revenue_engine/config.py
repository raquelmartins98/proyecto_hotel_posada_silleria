"""
Configuración global del sistema de Revenue Management.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class PricingConfig:
    """Parámetros globales del motor de precios."""
    
    # ---- Márgenes y rentabilidad ----
    default_target_margin: float = 20.0          # % margen sobre coste
    default_target_roi: float = 15.0             # % ROI anual objetivo
    min_margin: float = 5.0                      # % margen mínimo
    max_margin: float = 80.0                     # % margen máximo
    
    # ---- Booking Pace ----
    bvi_threshold_up: float = 1.05               # BVI para subir precios
    bvi_threshold_down: float = 0.95             # BVI para bajar precios
    bvi_window_days: int = 7                     # Ventana de cálculo BVI
    max_price_increase: float = 0.25             # +25% máximo
    max_price_decrease: float = 0.20             # -20% máximo
    confidence_minimum: float = 0.40             # Confianza mínima para usar booking pace
    
    # ---- Price Smoothing ----
    max_daily_change: float = 0.10               # 10% máximo cambio diario
    ema_alpha: float = 0.60                      # Factor de suavizado EMA
    
    # ---- Elasticidad ----
    elasticity_decay_beta: float = 0.15          # Decaimiento de elasticidad
    weekend_surcharge: float = 1.10              # Recargo fin de semana
    
    # ---- Ocupación ----
    occupancy_tiers: dict = field(default_factory=lambda: {
        "emergency":   (0.00, 0.30),   # < 30%
        "normal":      (0.30, 0.55),   # 30-55%
        "good_pace":   (0.55, 0.80),   # 55-80%
        "high_demand": (0.80, 0.92),   # 80-92%
        "full":        (0.92, 1.00),   # > 92%
    })
    
    # ---- Overbooking ----
    overbooking_max_pct: float = 0.10            # Máx 10% overbooking
    overbooking_confidence_min: float = 0.70     # Confianza mínima para overbooking
    
    # ---- Seasonality ----
    interpolation_window_days: int = 7           # Ventana de interpolación entre temporadas
    season_boundary_buffer: int = 3              # Días antes/después del cambio
    
    # ---- OTA ----
    direct_booking_cost_pct: float = 2.0         # % coste canal directo
    canibalization_alpha: float = 0.20           # Coeficiente de canibalización OTA->directo
    
    # ---- Redondeo Psicológico ----
    use_psychological_rounding: bool = True


@dataclass
class HotelMetadata:
    """Metadatos del hotel."""
    name: str = "Hotel Posada de la Sillería"
    location: str = "Toledo, España"
    category: str = "Boutique"
    total_rooms: int = 22
    year_opened: int = 2024
    currency: str = "EUR"
    
    # Líneas de negocio
    biz_lines: dict = field(default_factory=lambda: {
        "ALOJ": {"name": "Alojamiento",       "expected_revenue_pct": 65.0, "direct_cost_pct": 15.0},
        "REST": {"name": "Restauración",       "expected_revenue_pct": 25.0, "direct_cost_pct": 45.0},
        "EVENT": {"name": "Eventos",           "expected_revenue_pct": 10.0, "direct_cost_pct": 35.0},
    })


# Instancia global
DEFAULT_CONFIG = PricingConfig()
DEFAULT_HOTEL = HotelMetadata()

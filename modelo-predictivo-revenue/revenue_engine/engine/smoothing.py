"""
Motor de Suavizado de Precios (Price Smoothing).

Evita cambios bruscos en los precios que puedan:
    - Confundir al mercado
    - Generar desconfianza en los huéspedes
    - Provocar guerras de precios con competidores
    - Violar políticas de precios internas

Implementa:
    - Media Móvil Exponencial (EMA)
    - Acotación de cambio máximo diario
    - Redondeo psicológico hotelero
"""

import math
from typing import Optional, List

from revenue_engine.config import PricingConfig, DEFAULT_CONFIG


class PriceSmoothingEngine:
    """
    Suaviza cambios de precio para evitar fluctuaciones bruscas.
    
    Usa una media móvil exponencial:
        newPrice = α * proposedPrice + (1 - α) * currentPrice
    
    Con acotación de cambio máximo diario.
    """
    
    def __init__(self, config: PricingConfig = DEFAULT_CONFIG):
        self.config = config
    
    def smooth(
        self,
        current_price: float,
        proposed_price: float,
        alpha: Optional[float] = None,
        max_change: Optional[float] = None,
    ) -> float:
        """
        Aplica suavizado EMA con acotación.
        
        Args:
            current_price: Precio actual en los canales
            proposed_price: Precio propuesto por el motor
            alpha: Factor EMA (más alto = más peso al nuevo precio)
            max_change: Cambio máximo permitido (como fracción)
        
        Returns:
            Precio suavizado
        """
        if alpha is None:
            alpha = self.config.ema_alpha
        if max_change is None:
            max_change = self.config.max_daily_change
        
        raw_change = (proposed_price - current_price) / current_price if current_price > 0 else 0
        
        # Acotar cambio máximo
        clamped_change = max(-max_change, min(raw_change, max_change))
        
        # EMA
        effective_change = alpha * clamped_change + (1 - alpha) * 0
        
        smoothed = current_price * (1 + effective_change)
        
        return round(smoothed, 2)
    
    def psychological_rounding(self, price: float) -> float:
        """
        Redondeo psicológico para hotelería.
        
        Reglas:
        - Precios < 100€: redondear al 5 más cercano
        - Precios 100-200€: redondear al 5, terminar en 9 si es posible
        - Precios > 200€: redondear al 10, restar 1
        - Si termina en 0, ajustar
        """
        if not self.config.use_psychological_rounding:
            return round(price, 2)
        
        if price < 100:
            # Redondear al 5 más cercano
            rounded = round(price / 5) * 5
            # Evitar terminaciones en 0
            if rounded % 10 == 0:
                rounded = rounded - 1
            return max(rounded, 1)
        
        elif price < 200:
            rounded = round(price / 5) * 5
            if rounded % 10 == 0:
                rounded = rounded - 1
            return rounded
        
        else:
            rounded = round(price / 10) * 10 - 1
            return max(rounded, 199)
    
    def apply_all(
        self,
        current_price: float,
        proposed_price: float,
    ) -> float:
        """Aplica suavizado + redondeo completo."""
        smoothed = self.smooth(current_price, proposed_price)
        return self.psychological_rounding(smoothed)
    
    def max_allowed_price(self, current_price: float) -> float:
        """Precio máximo permitido (current * (1 + max_change))."""
        return round(current_price * (1 + self.config.max_daily_change), 2)
    
    def min_allowed_price(self, current_price: float) -> float:
        """Precio mínimo permitido (current * (1 - max_change))."""
        return round(current_price * (1 - self.config.max_daily_change), 2)

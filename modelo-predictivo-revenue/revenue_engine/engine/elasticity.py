"""
Motor de Elasticidad Precio-Demanda.

Implementa:
    - Coeficiente de elasticidad compuesto (múltiples segmentos)
    - Precio óptimo según regla de Lerner
    - Techo de mercado dinámico
    - Decaimiento de elasticidad por booking window
    - Precio óptimo por segmento multi-segmento
"""

from typing import Optional, Dict, List, Callable
from datetime import datetime
import math

from revenue_engine.config import PricingConfig, DEFAULT_CONFIG
from revenue_engine.toledo_calendar import (
    ToledoCalendar, ELASTICITY_MATRIX,
    SEGMENT_ELASTICITIES, SEGMENT_WEIGHTS,
    DOW_SHORT,
)


class ElasticityEngine:
    """
    Motor de elasticidad precio-demanda segmentada.
    
    La elasticidad varía según:
    - Día de la semana (viernes/sábado muy inelástico)
    - Temporada (Semana Santa → inelástico, Verano → elástico)
    - Segmento de cliente (escapista Madrid vs. cultural nacional)
    - Ventana de reserva restante (booking window)
    """
    
    def __init__(
        self,
        calendar: ToledoCalendar,
        config: PricingConfig = DEFAULT_CONFIG,
        elasticity_matrix: Optional[Dict[str, Dict[str, float]]] = None,
    ):
        self.calendar = calendar
        self.config = config
        self.matrix = elasticity_matrix or ELASTICITY_MATRIX
    
    def get_elasticity(self, d: any, market_ceiling: Optional[float] = None) -> float:
        """
        Obtiene la elasticidad compuesta para una fecha.
        
        Si la elasticidad compuesta es > -1 (inelástica), la demanda no responde
        a cambios de precio y se debe fijar precio cercano al techo de mercado.
        """
        # Obtener temporada
        if hasattr(d, 'date'):  # datetime
            d = d.date()
        
        season = self._get_effective_season(d)
        dow = DOW_SHORT.get(d.weekday(), "Mon")
        
        # Elasticidad de la matriz día × temporada
        season_data = self.matrix.get(season, self.matrix["S_MEDIA_INV"])
        base_elasticity = season_data.get(dow, -1.0)
        
        # Elasticidad compuesta por segmentos
        segment_key = self._get_segment_key(d)
        weights = SEGMENT_WEIGHTS.get(segment_key, SEGMENT_WEIGHTS["weekday"])
        
        composite_elasticity = sum(
            weights[seg] * SEGMENT_ELASTICITIES.get(seg, -1.0)
            for seg in weights
        )
        
        # Usar la más conservadora (menos elástica → más seguro para precio alto)
        final_elasticity = max(base_elasticity, composite_elasticity)
        
        return round(final_elasticity, 4)
    
    def get_optimal_price(
        self,
        marginal_cost: float,
        elasticity: float,
        market_ceiling: float,
        min_price: Optional[float] = None,
    ) -> float:
        """
        Calcula el precio óptimo según la regla de Lerner.
        
        Regla de Lerner: (P - MC) / P = -1/ε
        
        Si ε < -1 (elástico):
            P* = MC / (1 + 1/ε)
        
        Si ε >= -1 (inelástico):
            P* = market_ceiling (la regla de Lerner no aplica)
        """
        if min_price is None:
            min_price = marginal_cost * 1.05  # margen mínimo 5%
        
        if elasticity < -1:
            # Demanda elástica: aplicar markup óptimo
            optimal = marginal_cost / (1 + 1.0 / elasticity)
        else:
            # Demanda inelástica: subir hasta techo de mercado
            optimal = market_ceiling
        
        # Restricciones
        optimal = max(optimal, min_price)
        optimal = min(optimal, market_ceiling)
        
        return round(optimal, 2)
    
    def get_market_ceiling(
        self,
        d: any,
        competitive_price: float = 140.0,
        historical_max: float = 200.0,
        rack_rate: float = 180.0,
    ) -> float:
        """
        Calcula el techo de mercado dinámico.
        
        Market Ceiling = min(
            competitive_price * 1.25,
            historical_max * 1.10,
            rack_rate * 0.95
        )
        """
        if hasattr(d, 'date'):  # datetime
            d = d.date()
        
        season = self._get_effective_season(d)
        
        # Ajustar techo según temporada
        season_mult = {
            "S_SEMANA_SANTA": 1.30,
            "S_CORPUS": 1.20,
            "S_NAVIDAD": 1.15,
            "S_PRIMAVERA": 1.10,
            "S_OTONO": 1.05,
            "S_MEDIA_INV": 0.95,
            "S_VERANO": 0.90,
            "S_BAJA_INV": 0.85,
        }.get(season, 1.0)
        
        ceiling = min(
            competitive_price * 1.25 * season_mult,
            historical_max * 1.10,
            rack_rate * 0.95,
        )
        
        return round(ceiling, 2)
    
    def decay_elasticity(
        self,
        elasticity: float,
        days_before_arrival: int,
        max_window: int = 90,
        beta: float = 0.15,
    ) -> float:
        """
        Aplica decaimiento de elasticidad a medida que se acerca la fecha.
        
        ε_effective(d, t) = ε * (1 - β * ln(t / t_max))
        
        A más cerca de la fecha, menor elasticidad (demanda más inelástica
        porque quedan los que NECESITAN esa fecha).
        """
        if days_before_arrival <= 0:
            return elasticity * 0.5  # Muy inelástico el mismo día
        
        t = min(days_before_arrival, max_window)
        decay = 1 - beta * math.log(t / max_window) if t > 0 else 0.5
        
        return round(elasticity * max(decay, 0.3), 4)
    
    def _get_effective_season(self, d: any) -> str:
        """Temporada efectiva considerando eventos."""
        if isinstance(d, datetime):
            d = d.date()
        elif not hasattr(d, 'weekday'):
            return "S_MEDIA_INV"
        
        return self.calendar.get_season_for_date(d)
    
    def _get_segment_key(self, d: any) -> str:
        """Clave de ponderación de segmentos según el día."""
        if isinstance(d, datetime):
            d = d.date()
        elif not hasattr(d, 'weekday'):
            return "weekday"
        
        season = self.calendar.get_season_for_date(d)
        
        if season in ("S_SEMANA_SANTA", "S_CORPUS"):
            return "event"
        
        if season == "S_PUENTE" or self.calendar.is_puente(d):
            return "puente"
        
        if d.weekday() >= 4:  # Viernes o sábado
            return "weekend"
        
        return "weekday"
    
    def price_elasticity_report(self, base_price: float, d: any) -> Dict:
        """
        Genera un reporte de elasticidad para una fecha concreta.
        """
        if hasattr(d, 'date'):
            d = d.date()
        
        elasticity = self.get_elasticity(d)
        ceiling = self.get_market_ceiling(d)
        optimal = self.get_optimal_price(base_price, elasticity, ceiling)
        
        return {
            "date": d.isoformat(),
            "season": self._get_effective_season(d),
            "segment_key": self._get_segment_key(d),
            "composite_elasticity": elasticity,
            "elasticity_label": self._label_elasticity(elasticity),
            "market_ceiling": ceiling,
            "base_price": base_price,
            "optimal_price": optimal,
            "recommended_action": "RAISE" if optimal > base_price * 1.05
                else "LOWER" if optimal < base_price * 0.95
                else "HOLD",
        }
    
    @staticmethod
    def _label_elasticity(eps: float) -> str:
        if eps <= -2.0:
            return "Muy elástico"
        elif eps <= -1.2:
            return "Elástico"
        elif eps <= -0.8:
            return "Moderadamente elástico"
        elif eps <= -0.4:
            return "Inelástico"
        else:
            return "Muy inelástico"

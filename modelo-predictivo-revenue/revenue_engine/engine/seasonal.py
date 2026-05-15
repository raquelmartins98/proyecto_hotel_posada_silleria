"""
Motor de Ajuste Estacional — Coeficientes correctores para Toledo.

Implementa:
    - Matriz estacional completa con interpolación
    - Cálculo de coeficiente para cualquier fecha
    - Precios dinámicos por temporada
    - Reporte de coeficientes por período
"""

from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple

from revenue_engine.toledo_calendar import ToledoCalendar, SEASONAL_COEFFICIENTS
from revenue_engine.config import PricingConfig, DEFAULT_CONFIG


class SeasonalEngine:
    """
    Motor de ajuste estacional.
    
    Aplica coeficientes correctores según el calendario turístico de Toledo,
    con interpolación suave entre temporadas y recargo de fin de semana.
    """
    
    def __init__(
        self,
        calendar: ToledoCalendar,
        config: PricingConfig = DEFAULT_CONFIG,
    ):
        self.calendar = calendar
        self.config = config
    
    def get_coefficient(self, d: date) -> float:
        """Coeficiente estacional completo para una fecha."""
        return self.calendar.get_coefficient(d)
    
    def get_season_name(self, d: date) -> str:
        """Nombre legible de la temporada para una fecha."""
        season_map = {
            "S_BAJA_INV": "Baja Invierno",
            "S_MEDIA_INV": "Media Invierno",
            "S_SEMANA_SANTA": "Semana Santa",
            "S_PRIMAVERA": "Primavera",
            "S_CORPUS": "Corpus Christi",
            "S_VERANO": "Verano",
            "S_OTONO": "Otoño",
            "S_NAVIDAD": "Navidades",
            "S_PUENTE": "Puente",
        }
        
        # Prioridad: eventos > puente > temporada base
        if self.calendar.is_puente(d):
            # Comprobar si cae en evento primero
            pass
        
        season_code = self.calendar.get_season_for_date(d)
        return season_map.get(season_code, "Temporada regular")
    
    def apply_seasonal_price(
        self,
        base_price: float,
        d: date,
        weekend_surcharge: Optional[bool] = None,
    ) -> float:
        """
        Aplica el ajuste estacional a un precio base.
        
        Price(d) = basePrice * SeasonalCoeff(d) * WeekendSurcharge(d)
        """
        coeff = self.get_coefficient(d)
        
        price = base_price * coeff
        
        # El recargo de fin de semana ya está incluido en el coeficiente
        # del calendario (get_coefficient aplica weekend_surcharge)
        
        return round(price, 2)
    
    def generate_yearly_prices(
        self,
        base_prices: Dict[str, float],
        year: int = 2026,
    ) -> Dict[str, Dict[str, float]]:
        """
        Genera precios dinámicos para todo un año.
        
        Args:
            base_prices: Dict con {room_cat_id: precio_base}
            year: Año a generar
        
        Returns:
            Dict con {fecha_iso: {cat_id: precio}}
        """
        start = date(year, 1, 1)
        end = date(year, 12, 31)
        delta = end - start
        
        prices = {}
        for i in range(delta.days + 1):
            d = start + timedelta(days=i)
            date_key = d.isoformat()
            prices[date_key] = {}
            
            for cat_id, base_price in base_prices.items():
                prices[date_key][cat_id] = self.apply_seasonal_price(base_price, d)
        
        return prices
    
    def seasonality_report(self, year: int = 2026) -> List[Dict]:
        """
        Genera un reporte de coeficientes por período.
        """
        periods = self.calendar.get_periods()
        report = []
        
        for p in periods:
            # Fecha de ejemplo representativa del período
            try:
                sample_date = date(year, p.start[0], p.start[1])
            except (ValueError, OverflowError):
                sample_date = date(year, 6, 15)  # fallback
            
            report.append({
                "code": p.code,
                "name": p.name,
                "start_date": f"{p.start[0]:02d}-{p.start[1]:02d}",
                "end_date": f"{p.end[0]:02d}-{p.end[1]:02d}",
                "base_coefficient": p.coefficient,
                "sample_coefficient": self.get_coefficient(sample_date),
                "is_event": p.is_event,
                "priority": p.priority,
            })
        
        return sorted(report, key=lambda x: x["priority"], reverse=True)
    
    def get_puentes_list(self, year: int = 2026) -> List[Dict]:
        """Lista de puentes nacionales para el año."""
        puentes = self.calendar.get_puentes()
        return [
            {
                "start": p[0].isoformat(),
                "end": p[1].isoformat(),
                "name": p[2],
                "days": (p[1] - p[0]).days + 1,
            }
            for p in puentes
        ]

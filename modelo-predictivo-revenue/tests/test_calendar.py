"""
Tests del Toledo Calendar.
"""

import pytest
from datetime import date, timedelta
from revenue_engine.toledo_calendar import (
    ToledoCalendar, SEASONAL_COEFFICIENTS, ELASTICITY_MATRIX,
)


class TestToledoCalendarComplete:
    """Tests exhaustivos del calendario de Toledo."""
    
    @pytest.fixture
    def cal(self):
        return ToledoCalendar(year=2026)
    
    def test_seasonal_highs_and_lows(self, cal):
        """Verifica los extremos de estacionalidad."""
        assert cal.get_coefficient(date(2026, 4, 3)) >= 1.70  # Viernes Santo (1.75 × 1.10)
        # Baja Invierno: 1 Febrero, bien entrada la temporada (no en zona de interpolación)
        assert cal.get_coefficient(date(2026, 2, 10)) <= 0.90  # Plena baja invierno
    
    def test_season_interpolation(self, cal):
        """Verifica que la interpolación suave funcione."""
        # Justo antes de Semana Santa (transición media invierno → primavera)
        d1 = date(2026, 4, 4)  # Sábado Santo → Semana Santa (1.75)
        assert cal.get_coefficient(d1) >= 1.50
    
    def test_elasticity_weekend_vs_weekday(self, cal):
        from revenue_engine.engine.elasticity import ElasticityEngine
        engine = ElasticityEngine(cal)
        
        # Viernes de primavera vs Martes de primavera
        viernes = date(2026, 5, 15)
        martes = date(2026, 5, 12)
        
        eps_fri = engine.get_elasticity(viernes)
        eps_tue = engine.get_elasticity(martes)
        
        assert eps_fri > eps_tue  # viernes menos elástico
    
    def test_biz_lines_config(self):
        from revenue_engine.engine.profit_distribution import ProfitDistributionEngine
        biz_lines = {
            "ALOJ": {"name": "Alojamiento", "expected_revenue_pct": 65, "direct_cost_pct": 15},
            "REST": {"name": "Restauración", "expected_revenue_pct": 25, "direct_cost_pct": 45},
        }
        engine = ProfitDistributionEngine(biz_lines, 100_000)
        result = engine.distribute(target_profit=10_000)
        assert abs(sum(result.values()) - 10_000) < 0.01

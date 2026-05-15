"""
Tests del Revenue Management Engine.
"""

import pytest
from datetime import date, datetime
from revenue_engine.models import (
    HotelConfig, RoomCategory, FixedCost, VariableCost,
    InvestmentParams, ScenarioName, AllocationMethod,
)
from revenue_engine.engine.cost_engine import CostEngine, sigmoid
from revenue_engine.engine.elasticity import ElasticityEngine
from revenue_engine.engine.seasonal import SeasonalEngine
from revenue_engine.engine.pricing_engine import RevenueManager
from revenue_engine.engine.roi_calculator import ROICalculator
from revenue_engine.engine.breakeven import BreakEvenEngine
from revenue_engine.toledo_calendar import ToledoCalendar


# ─── FIXTURES ───

@pytest.fixture
def sample_rooms():
    return [
        RoomCategory("dob", "DOB", "Doble", 12, 2, 22.0, 120.0, 1.00),
        RoomCategory("sup", "SUP", "Superior", 6, 2, 32.5, 155.0, 1.35),
    ]


@pytest.fixture
def sample_fixed_costs():
    return [
        FixedCost("FC1", "Personal", "staff", 10_000.0, AllocationMethod.WEIGHTED),
        FixedCost("FC2", "Suministros", "suministros", 3_000.0, AllocationMethod.SQM),
    ]


@pytest.fixture
def sample_variable_costs():
    return [
        VariableCost("VC1", "dob", "Limpieza", per_stay_amount=12.0),
        VariableCost("VC2", "dob", "Amenities", per_stay_amount=5.0),
        VariableCost("VC3", "sup", "Limpieza", per_stay_amount=15.0),
        VariableCost("VC4", "sup", "Amenities", per_stay_amount=8.0),
    ]


@pytest.fixture
def sample_config(sample_rooms, sample_fixed_costs, sample_variable_costs):
    return HotelConfig(
        hotel_name="Test Hotel",
        room_categories=sample_rooms,
        fixed_costs=sample_fixed_costs,
        variable_costs=sample_variable_costs,
    )


@pytest.fixture
def cost_engine(sample_rooms, sample_fixed_costs, sample_variable_costs):
    return CostEngine(sample_rooms, sample_fixed_costs, sample_variable_costs)


# ─── TEST SIGMOIDE ───

class TestSigmoid:
    def test_low_occupancy(self):
        """A baja ocupación (< 40%), sigmoide ≈ 0"""
        assert sigmoid(0.20) < 0.01

    def test_high_occupancy(self):
        """A alta ocupación (> 80%), sigmoide ≈ 1"""
        assert sigmoid(0.85) > 0.95

    def test_midpoint(self):
        """En el punto medio (60%), sigmoide = 0.5"""
        assert abs(sigmoid(0.60) - 0.5) < 0.01


# ─── TEST COST ENGINE ───

class TestCostEngine:
    def test_total_fixed_costs(self, cost_engine):
        assert cost_engine.total_fixed_costs == 156_000.0  # 13.000€/mes × 12
        assert cost_engine.total_fixed_costs_monthly == 13_000.0

    def test_total_rooms(self, cost_engine):
        assert cost_engine.total_rooms == 18

    def test_sum_weights(self, cost_engine):
        """12*1.0 + 6*1.35 = 12 + 8.1 = 20.1"""
        assert abs(cost_engine._sum_weights() - 20.1) < 0.01

    def test_calculate_returns_all_categories(self, cost_engine):
        result = cost_engine.calculate(occupancy=0.70)
        assert len(result) == 2
        assert all(r.cat_id in ("dob", "sup") for r in result)

    def test_base_price_above_marginal(self, cost_engine):
        result = cost_engine.calculate(occupancy=0.70)
        for r in result:
            assert r.base_price > r.marginal_cost

    def test_doble_cheaper_than_superior(self, cost_engine):
        result = cost_engine.calculate(occupancy=0.70)
        doble = next(r for r in result if r.cat_id == "dob")
        superior = next(r for r in result if r.cat_id == "sup")
        assert doble.base_price < superior.base_price


# ─── TEST CALENDARIO TOLEDO ───

class TestToledoCalendar:
    def test_easter_sunday_2026(self):
        """Domingo de Resurrección 2026: 5 de abril"""
        cal = ToledoCalendar(year=2026)
        assert cal.easter_sunday == date(2026, 4, 5)

    def test_palm_sunday_2026(self):
        """Domingo de Ramos 2026: 29 de marzo"""
        cal = ToledoCalendar(year=2026)
        assert cal.palm_sunday == date(2026, 3, 29)

    def test_corpus_2026(self):
        """Corpus Christi 2026: 60 días post Pascua ≈ 4 de junio"""
        from datetime import timedelta
        cal = ToledoCalendar(year=2026)
        corpus = cal.easter_sunday + timedelta(days=60)
        assert corpus == date(2026, 6, 4)

    def test_semana_santa_coefficient(self):
        cal = ToledoCalendar(year=2026)
        # Jueves Santo
        jueves_santo = date(2026, 4, 2)
        coeff = cal.get_coefficient(jueves_santo)
        assert coeff >= 1.75

    def test_weekend_surcharge(self):
        cal = ToledoCalendar(year=2026)
        # Un sábado de primavera
        sabado = date(2026, 4, 18)
        coeff = cal.get_coefficient(sabado)
        assert coeff > 1.10  # Primavera 1.10 * weekend 1.10

    def test_puente_detect(self):
        cal = ToledoCalendar(year=2026)
        # Hispanidad 2026: 12 octubre es lunes → puente
        hisp = date(2026, 10, 12)
        assert cal.is_puente(hisp)
    
    def test_verano_coefficient(self):
        cal = ToledoCalendar(year=2026)
        verano = date(2026, 7, 15)
        coeff = cal.get_coefficient(verano)
        assert coeff <= 1.05  # Verano 0.95 (sin fin de semana)


# ─── TEST REVENUE MANAGER ───

class TestRevenueManager:
    def test_initialization(self, sample_config):
        manager = RevenueManager(sample_config)
        assert manager is not None
        assert manager.cost_engine.total_rooms == 18

    def test_simulation_returns_result(self, sample_config):
        manager = RevenueManager(sample_config)
        result = manager.run_simulation(occupancy=0.70)
        assert result is not None
        assert result.total_revenue > 0
        assert result.total_costs > 0

    def test_higher_occupancy_more_revenue(self, sample_config):
        manager = RevenueManager(sample_config)
        r1 = manager.run_simulation(occupancy=0.50)
        r2 = manager.run_simulation(occupancy=0.80)
        assert r2.total_revenue > r1.total_revenue

    def test_higher_margin_higher_price(self, sample_config):
        manager = RevenueManager(sample_config)
        r1 = manager.run_simulation(occupancy=0.70, target_margin=10.0)
        r2 = manager.run_simulation(occupancy=0.70, target_margin=30.0)
        
        p1 = r1.category_pricing[0].base_price
        p2 = r2.category_pricing[0].base_price
        assert p2 > p1

    def test_breakeven_below_current_occupancy(self, sample_config):
        """Con los datos de test, el BE debe ser alcanzable (>0% pero <100%)."""
        manager = RevenueManager(sample_config)
        result = manager.run_simulation(occupancy=0.70)
        assert result.breakeven_occupancy_pct > 0.0
        assert result.breakeven_occupancy_pct <= 100.0

    def test_monthly_pnl_length(self, sample_config):
        manager = RevenueManager(sample_config)
        result = manager.run_simulation()
        assert result.monthly_pnl is not None
        assert len(result.monthly_pnl) == 12

    def test_allocated_profits_sum(self, sample_config):
        manager = RevenueManager(sample_config)
        result = manager.run_simulation(target_roi=15.0)
        total = sum(result.allocated_profits.values())
        inv = sample_config.investment
        expected_monthly = inv.total_investment * 0.15 / 12
        assert abs(total - expected_monthly) < 0.01 * expected_monthly


# ─── TEST ROI ───

class TestROI:
    def test_roi_calculation(self):
        calc = ROICalculator(InvestmentParams(total_investment=1_000_000))
        result = calc.calculate(annual_net_profit=150_000)
        assert abs(result["roi_pct"] - 15.0) < 0.01

    def test_payback_calculation(self):
        calc = ROICalculator(InvestmentParams(total_investment=1_000_000))
        result = calc.calculate(annual_net_profit=200_000)
        assert abs(result["payback_years"] - 5.0) < 0.01

    def test_sensitivity_analysis(self):
        calc = ROICalculator(InvestmentParams(total_investment=1_000_000))
        sens = calc.sensitivity_analysis(base_net_profit=150_000)
        assert len(sens["scenarios"]) == 7  # 7 variaciones


# ─── TEST RENDIMIENTO ───

class TestPerformance:
    def test_simulation_under_2_seconds(self, sample_config):
        """La simulación debe ejecutarse en menos de 2 segundos."""
        import time
        manager = RevenueManager(sample_config)
        start = time.time()
        manager.run_simulation()
        elapsed = time.time() - start
        assert elapsed < 2.0, f"Simulación tardó {elapsed:.2f}s (límite: 2s)"

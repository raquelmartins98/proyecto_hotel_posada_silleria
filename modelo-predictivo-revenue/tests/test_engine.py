"""
Tests del Revenue Management Engine.
"""

import pytest
from datetime import date, datetime, timedelta
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
from revenue_engine.toledo_calendar import ToledoCalendar, ELASTICITY_MATRIX


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


# ─── TESTS REGRESIVOS (bugs cazados) ───

VALID_DOW_KEYS = {"Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"}

class TestRegressionDOW:
    """Tests que habrían cazado el bug #1 (DOW mapping) y bug #2 (Fr typo)."""

    @pytest.mark.parametrize("d,season,expected", [
        (date(2026, 5, 15), "S_PRIMAVERA", -0.7),   # viernes primavera
        (date(2026, 1, 2),  "S_NAVIDAD",   -0.5),   # viernes navidad
        (date(2026, 10, 9), "S_OTONO",     -0.6),   # viernes otoño (caza "Fr" typo)
    ])
    def test_friday_uses_friday_elasticity(self, d, season, expected):
        """Viernes usa 'Fri' en la matriz (no 'Thu' del bug #1, ni 'Fr' del bug #2)."""
        cal = ToledoCalendar(year=d.year)
        eng = ElasticityEngine(cal)
        assert eng.get_elasticity(d) == pytest.approx(expected, abs=0.02)

    def test_monday_not_sunday_elasticity(self):
        """Lunes usa 'Mon' no 'Sun' (bug #1: DOW mapping)."""
        cal = ToledoCalendar(2026)
        eng = ElasticityEngine(cal)
        monday = date(2026, 5, 4)   # lunes de primavera
        sunday = date(2026, 5, 10)  # domingo de primavera
        mon_el = eng.get_elasticity(monday)
        sun_el = eng.get_elasticity(sunday)
        # Con el bug, lunes y domingo daban la misma elasticidad
        assert abs(mon_el - sun_el) > 0.1, \
            f"Lunes({mon_el}) y domingo({sun_el}) deberían diferir >0.1"

    def test_elasticity_matrix_no_typos(self):
        """Todas las claves DOW en la matriz son válidas (sin 'Fr' ni 'FRI')."""
        for season_name, dow_map in ELASTICITY_MATRIX.items():
            for key in dow_map:
                assert key in VALID_DOW_KEYS, \
                    f"{season_name} tiene clave inválida: '{key}'"

    def test_all_dow_keys_present(self):
        """Cada temporada tiene las 7 claves DOW."""
        for season_name, dow_map in ELASTICITY_MATRIX.items():
            missing = VALID_DOW_KEYS - set(dow_map.keys())
            assert not missing, \
                f"{season_name} falta: {missing}"

    def test_all_year_coverage(self):
        """Cada día del año tiene elasticidad y coeficiente en rango sano."""
        cal = ToledoCalendar(2026)
        eng = ElasticityEngine(cal)
        for offset in range(365):
            d = date(2026, 1, 1) + timedelta(days=offset)
            coeff = cal.get_coefficient(d)
            el = eng.get_elasticity(d)
            assert 0.5 < coeff < 3.0, f"Coeficiente {coeff} fuera de rango para {d}"
            assert -2.5 < el < -0.15, f"Elasticidad {el} fuera de rango para {d}"


class TestRegressionWeekend:
    """Tests que habrían cazado el bug #4 (is_weekend incluía domingo)."""

    def test_saturday_is_weekend(self):
        """Sábado es fin de semana hotelero."""
        cal = ToledoCalendar(2026)
        sabado = date(2026, 5, 9)
        assert cal.is_weekend(sabado) is True

    def test_sunday_is_not_weekend(self):
        """Domingo NO es fin de semana hotelero (día de salida)."""
        cal = ToledoCalendar(2026)
        domingo = date(2026, 5, 10)
        assert cal.is_weekend(domingo) is False, \
            "Domingo no debe tener recargo de fin de semana"

    def test_sunday_no_surcharge(self):
        """Domingo no tiene el ×1.10 de fin de semana en su coeficiente."""
        cal = ToledoCalendar(2026)
        domingo = date(2026, 5, 10)   # domingo primavera (base=1.10)
        sabado = date(2026, 5, 9)     # sábado primavera (base=1.10 × 1.10)
        # Con el bug: domingo=1.21, sábado=1.21 (iguales)
        # Con el fix: domingo=1.10, sábado=1.21 (diferentes)
        dom_coef = cal.get_coefficient(domingo)
        sab_coef = cal.get_coefficient(sabado)
        assert sab_coef > dom_coef, \
            f"Sábado({sab_coef}) debería ser > Domingo({dom_coef})"
        assert abs(dom_coef - 1.10) < 0.02, \
            f"Domingo debería ser ~1.10 (base), no {dom_coef}"


class TestRegressionLerner:
    """Tests que habrían cazado el bug #3 (Lerner con seasonal_price)."""

    def test_optimal_price_uses_marginal_cost(self):
        """get_optimal_price varía con el coste marginal (bug #3)."""
        cal = ToledoCalendar(2026)
        eng = ElasticityEngine(cal)
        d = date(2026, 1, 12)  # lunes baja temporada, eps≈-1.18
        eps = eng.get_elasticity(d)
        ceiling = eng.get_market_ceiling(d)  # ≈149

        # MCs bajos para que Lerner quede bajo el ceiling
        mc_low = 15.0   # P* ≈ 100.7 < 148.75
        mc_high = 20.0  # P* ≈ 134.2 < 148.75

        p_low = eng.get_optimal_price(mc_low, eps, ceiling)
        p_high = eng.get_optimal_price(mc_high, eps, ceiling)

        assert p_high > p_low, \
            f"A mayor MC debería dar mayor precio ({p_high} > {p_low})"
        assert p_low >= mc_low * 1.05, \
            f"Precio ({p_low}) respeta min_price ({mc_low*1.05})"
        assert p_high >= mc_high * 1.05, \
            f"Precio ({p_high}) respeta min_price ({mc_high*1.05})"

    def test_lerner_price_below_ceiling(self):
        """Con elasticidad normal, Lerner da precio por debajo del techo."""
        cal = ToledoCalendar(2026)
        eng = ElasticityEngine(cal)
        d = date(2026, 5, 4)
        eps = eng.get_elasticity(d)
        ceiling = eng.get_market_ceiling(d)
        mc = 42.50

        price = eng.get_optimal_price(mc, eps, ceiling)
        ceiling_before_clamp = mc / (1 + 1.0 / eps)

        if eps < -1:
            assert price <= ceiling, \
                f"Precio Lerner {price} no debería superar techo {ceiling}"
            assert price >= mc * 1.05, \
                f"Precio Lerner {price} debería ser >= MC×1.05 ({mc*1.05})"


class TestRegressionPackage:
    """Tests que habrían cazado el bug #5 (seed import fuera del paquete)."""

    def test_from_seed_works(self):
        """HotelConfig.from_seed funciona desde cualquier import."""
        config = HotelConfig.from_seed("posada_silleria")
        assert config is not None
        assert config.hotel_name == "Hotel Posada de la Sillería"
        assert config.total_rooms() == 22
        assert len(config.fixed_costs) == 10

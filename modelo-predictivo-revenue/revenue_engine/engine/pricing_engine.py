"""
Orquestador Principal del Revenue Management Engine.

Coordina todos los submotores para ejecutar simulaciones completas:
    1. Motor de Costes
    2. Elasticidad Precio-Demanda
    3. Ajuste Estacional
    4. Modelo OTA
    5. Break-Even
    6. ROI
    7. Reparto de Beneficio
    8. Booking Pace
    9. Suavizado de Precios

Uso:
    manager = RevenueManager(config)
    result = manager.run_simulation(occupancy=0.75, target_margin=20.0)
    print(result.executive_summary())
"""

from datetime import date, timedelta, datetime
from typing import Dict, List, Optional, Tuple
import json

from revenue_engine.models import (
    HotelConfig, SimulationInput, SimulationResult, CategoryPricing,
    PricingAction, ScenarioName, DailyPricePoint, ChannelStrategy,
)
from revenue_engine.config import DEFAULT_CONFIG, PricingConfig
from revenue_engine.engine.cost_engine import CostEngine
from revenue_engine.engine.elasticity import ElasticityEngine
from revenue_engine.engine.seasonal import SeasonalEngine
from revenue_engine.engine.ota import CommissionModel, ChannelManager, CannibalizationModel
from revenue_engine.engine.breakeven import BreakEvenEngine
from revenue_engine.engine.roi_calculator import ROICalculator
from revenue_engine.engine.profit_distribution import ProfitDistributionEngine
from revenue_engine.engine.booking_pace import BookingPaceEngine
from revenue_engine.engine.smoothing import PriceSmoothingEngine
from revenue_engine.toledo_calendar import ToledoCalendar


class RevenueManager:
    """
    Orquestador principal del sistema de Revenue Management.
    
    Coordina todos los submotores para ejecutar simulaciones
    completas de pricing, rentabilidad y proyección.
    """
    
    def __init__(
        self,
        config: HotelConfig,
        pricing_config: PricingConfig = DEFAULT_CONFIG,
    ):
        self.config = config
        self.pricing_config = pricing_config
        
        # Inicializar calendario de Toledo
        self.calendar = ToledoCalendar(year=date.today().year)
        
        # Inicializar submotores
        self.cost_engine = CostEngine(
            config.room_categories,
            config.fixed_costs,
            config.variable_costs,
        )
        self.elasticity = ElasticityEngine(self.calendar, pricing_config)
        self.seasonal = SeasonalEngine(self.calendar, pricing_config)
        self.breakeven = BreakEvenEngine(self.cost_engine)
        self.roi_calc = ROICalculator(config.investment)
        self.distribution = ProfitDistributionEngine(
            config.biz_lines,
            alojamiento_revenue=0.0,  # Se actualiza en simulación
        )
        self.booking_pace = BookingPaceEngine(pricing_config)
        self.smoothing = PriceSmoothingEngine(pricing_config)
        self.channel_mgr = ChannelManager(pricing_config)
    
    def run_simulation(
        self,
        occupancy: float = 0.70,
        target_margin: float = 20.0,
        target_roi: float = 15.0,
        total_investment: float = 1_200_000.0,
        avg_guests: float = 1.8,
        ota_pct: float = 40.0,
        days_in_period: int = 365,
        year: Optional[int] = None,
        scenario_name: ScenarioName = ScenarioName.REALISTA,
    ) -> SimulationResult:
        """
        Ejecuta una simulación completa de pricing y rentabilidad.
        
        Args:
            occupancy: Ocupación esperada (0.0-1.0)
            target_margin: Margen de beneficio objetivo (%)
            target_roi: ROI objetivo anual (%)
            total_investment: Inversión total (€)
            avg_guests: Media de huéspedes por habitación
            ota_pct: Porcentaje de reservas vía OTA
            days_in_period: Días del período
            year: Año de simulación
            scenario_name: Nombre del escenario
        
        Returns:
            SimulationResult con todas las métricas
        """
        if year is None:
            year = date.today().year
        
        self.calendar = ToledoCalendar(year=year)
        self.elasticity.calendar = self.calendar
        self.seasonal.calendar = self.calendar
        
        # --- INPUT ---
        sim_input = SimulationInput(
            occupancy_pct=occupancy,
            target_margin_pct=target_margin,
            target_roi_pct=target_roi,
            total_investment=total_investment,
            avg_guests_per_room=avg_guests,
            avg_ota_pct=ota_pct,
            days_in_period=days_in_period,
            scenario_name=scenario_name,
        )
        
        result = SimulationResult(input_used=sim_input)
        result.total_rooms = self.config.total_rooms()
        result.total_room_nights = int(self.config.total_rooms() * days_in_period * occupancy)
        
        # --- 1. MOTOR DE COSTES ---
        category_pricing = self.cost_engine.calculate(
            occupancy=occupancy,
            days_in_period=days_in_period,
            avg_guests=avg_guests,
            ota_pct=ota_pct,
            target_margin=target_margin,
        )
        result.category_pricing = category_pricing
        
        # --- 2. INGRESOS Y COSTES GLOBALES ---
        total_revenue = 0.0
        total_variable = 0.0
        
        for cp in category_pricing:
            nights = cp.room_count * days_in_period * occupancy
            total_revenue += cp.base_price * nights
            total_variable += cp.variable_per_night * nights
        
        result.total_revenue = round(total_revenue, 2)
        result.total_fixed_costs = round(self.cost_engine.total_fixed_costs, 2)
        result.total_variable_costs = round(total_variable, 2)
        result.total_costs = round(result.total_fixed_costs + result.total_variable_costs, 2)
        result.net_profit = round(result.total_revenue - result.total_costs, 2)
        result.net_margin_pct = round(
            (result.net_profit / result.total_revenue * 100)
            if result.total_revenue > 0 else 0,
            2,
        )
        
        # --- 3. BREAK-EVEN ---
        prices = [cp.base_price for cp in category_pricing]
        be = self.breakeven.breakeven_report(prices, occupancy, days_in_period)
        result.breakeven_occupancy_pct = be["breakeven_occupancy_pct"]
        result.breakeven_revenue = be["breakeven_revenue_eur"]
        
        # --- 4. ROI y PAYBACK ---
        annual_profit = result.net_profit  # Ya es anual
        roi_result = self.roi_calc.calculate(
            annual_net_profit=annual_profit,
            total_investment=total_investment,
        )
        result.roi_pct = roi_result["roi_pct"]
        result.payback_years = roi_result["payback_years"]
        result.economic_value_added = roi_result["eva"]
        
        # --- 5. REPARTO HOMOGÉNEO DE BENEFICIO ---
        target_monthly_profit = total_investment * (target_roi / 100) / 12
        self.distribution.alojamiento_revenue = total_revenue / 12  # mensual
        allocation = self.distribution.distribute(target_monthly_profit)
        result.allocated_profits = allocation
        
        # --- 6. PRECIOS DINÁMICOS ESTACIONALES ---
        base_price_map = {cp.cat_id: cp.base_price for cp in category_pricing}
        daily_prices = self.seasonal.generate_yearly_prices(base_price_map, year)
        result.daily_prices = daily_prices
        
        # --- 7. REPORTE MENSUAL (P&L) ---
        result.monthly_pnl = self._generate_monthly_pnl(
            category_pricing, occupancy, days_in_period, year
        )
        
        return result
    
    def _generate_monthly_pnl(
        self,
        category_pricing: List[CategoryPricing],
        occupancy: float,
        days_in_period: int,
        year: int,
    ) -> List[Dict]:
        """Genera P&L mensual estacional."""
        monthly_data = []
        running_profit = 0.0
        days_per_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
        
        for month in range(1, 13):
            days = days_per_month[month - 1]
            
            # Fecha representativa del mes
            mid_date = date(year, month, min(15, days))
            
            # Coeficiente estacional del mes
            season = self.calendar.get_season_for_date(mid_date)
            season_name = self.seasonal.get_season_name(mid_date)
            
            # Ingresos del mes
            month_revenue = 0.0
            month_costs = 0.0
            
            for cp in category_pricing:
                month_nights = cp.room_count * days * occupancy
                month_revenue += cp.base_price * month_nights
                
                # Coste fijo mensual asignado
                cat_nights_total = cp.room_count * days_in_period * occupancy
                fixed_share_month = (cp.fixed_cost_share * days / 30) if cat_nights_total > 0 else 0
                
                month_costs += fixed_share_month + cp.variable_per_night * month_nights
            
            month_profit = month_revenue - month_costs
            running_profit += month_profit
            
            monthly_data.append({
                "month": month,
                "month_name": self._month_name(month),
                "season": season,
                "season_name": season_name,
                "seasonal_coeff": self.calendar.get_coefficient(mid_date),
                "days": days,
                "revenue": round(month_revenue, 2),
                "costs": round(month_costs, 2),
                "profit": round(month_profit, 2),
                "running_profit": round(running_profit, 2),
                "margin_pct": round(
                    (month_profit / month_revenue * 100) if month_revenue > 0 else 0,
                    2,
                ),
            })
        
        return monthly_data
    
    def run_daily_pricing(
        self,
        start_date: date,
        end_date: date,
        base_prices: Dict[str, float],
    ) -> List[DailyPricePoint]:
        """
        Genera precios dinámicos día a día para un rango de fechas.
        
        Args:
            start_date: Fecha de inicio
            end_date: Fecha de fin
            base_prices: Dict con {cat_id: precio_base}
        
        Returns:
            Lista de DailyPricePoint
        """
        daily_prices = []
        current = start_date
        
        while current <= end_date:
            season = self.calendar.get_season_for_date(current)
            coeff = self.calendar.get_coefficient(current)
            
            for cat_id, base_price in base_prices.items():
                seasonal_price = base_price * coeff
                
                # Aplicar elasticidad
                elasticity = self.elasticity.get_elasticity(current)
                ceiling = self.elasticity.get_market_ceiling(current)
                optimal = self.elasticity.get_optimal_price(
                    seasonal_price, elasticity, ceiling
                )
                
                point = DailyPricePoint(
                    date=current,
                    room_cat_id=cat_id,
                    season=season,
                    season_coefficient=coeff,
                    base_price=seasonal_price,
                    final_price=optimal,
                    action=PricingAction.HOLD,
                )
                daily_prices.append(point)
            
            current += timedelta(days=1)
        
        return daily_prices
    
    def breakeven_analysis(
        self,
        target_margin: float = 20.0,
        total_investment: float = 1_200_000.0,
    ) -> Dict:
        """
        Análisis completo de break-even con escenarios múltiples.
        """
        scenarios = [
            ("Pesimista", 0.45),
            ("Realista", 0.70),
            ("Optimista", 0.85),
        ]
        
        results = []
        for name, occ in scenarios:
            sim = self.run_simulation(
                occupancy=occ,
                target_margin=target_margin,
                total_investment=total_investment,
                scenario_name=getattr(ScenarioName, name.upper()),
            )
            results.append({
                "scenario": name,
                "occupancy_pct": round(occ * 100, 1),
                "revenue": sim.total_revenue,
                "costs": sim.total_costs,
                "profit": sim.net_profit,
                "margin_pct": sim.net_margin_pct,
                "be_occupancy": sim.breakeven_occupancy_pct,
                "roi_pct": sim.roi_pct,
                "payback_years": sim.payback_years,
            })
        
        return {"target_margin_pct": target_margin, "scenarios": results}
    
    @staticmethod
    def _month_name(month: int) -> str:
        names = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
                 "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
        return names[month - 1] if 1 <= month <= 12 else ""


# ──────────────────────────────────────────────
# CLI: EJECUCIÓN DIRECTA
# ──────────────────────────────────────────────

if __name__ == "__main__":
    from revenue_engine.models import HotelConfig, ScenarioName
    
    print("═══ REVENUE MANAGEMENT ENGINE — HOTEL POSADA DE LA SILLERÍA ═══\n")
    print("Cargando datos semilla...")
    
    config = HotelConfig.from_seed("posada_silleria")
    manager = RevenueManager(config)
    
    print(f"Hotel: {config.hotel_name}")
    print(f"Habitaciones: {config.total_rooms()}")
    print(f"Costes Fijos Mensuales: {manager.cost_engine.total_fixed_costs:,.2f}€\n")
    
    # Escenario realista
    print("▶ EJECUTANDO SIMULACIÓN (Escenario Realista, 70% ocupación)...\n")
    result = manager.run_simulation(
        occupancy=0.70,
        target_margin=20.0,
        target_roi=15.0,
        total_investment=1_200_000.0,
        scenario_name=ScenarioName.REALISTA,
    )
    
    print(result.executive_summary())
    
    print("\n▶ DESGLOSE POR CATEGORÍA:")
    for cp in result.category_pricing:
        margin = cp.base_price - cp.marginal_cost
        margin_pct = (margin / cp.base_price * 100) if cp.base_price > 0 else 0
        print(f"  {cp.cat_name:<20} {cp.room_count:>2} uds  |  "
              f"Coste: {cp.marginal_cost:>6.2f}€  →  Precio: {cp.base_price:>6.2f}€  "
              f"(Margen: {margin_pct:.1f}%)")
    
    print("\n▶ REPARTO HOMOGÉNEO DE BENEFICIO:")
    for code, profit in result.allocated_profits.items():
        info = config.biz_lines.get(code, {})
        print(f"  {info.get('name', code):<20}: {profit:>10.2f}€/mes")
    
    print("\n▶ P&L ESTACIONAL:")
    print(f"  {'Mes':<12} {'Temp':<18} {'Ingresos':>12} {'Costes':>12} {'Beneficio':>12} {'Margen':>8}")
    print(f"  {'─'*74}")
    for m in result.monthly_pnl or []:
        print(f"  {m['month_name']:<12} {m['season_name']:<18} "
              f"{m['revenue']:>10,.2f}€ {m['costs']:>10,.2f}€ {m['profit']:>10,.2f}€ "
              f"{m['margin_pct']:>6.1f}%")
    
    print("\n✅ Simulación completada con éxito.")

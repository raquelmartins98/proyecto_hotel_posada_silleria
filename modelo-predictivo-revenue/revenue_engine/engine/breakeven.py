"""
Motor de Break-Even Analysis.

Calcula el punto de equilibrio en ocupación y en ingresos,
tanto a nivel global como por categoría de habitación.
"""

from typing import List, Optional

from revenue_engine.models import RoomCategory, VariableCost
from revenue_engine.engine.cost_engine import CostEngine, calculate_variable_cost_per_night


class BreakEvenEngine:
    """
    Calcula el punto de equilibrio del hotel.
    
    Break-Even Occupancy = TotalFixedCosts / (
        Σ(Price_i * RoomCount_i * Days) - Σ(VC_i * RoomCount_i * Days)
    )
    
    Break-Even Revenue = TotalFixedCosts / (1 - VariableCostRatio)
    """
    
    def __init__(self, cost_engine: CostEngine):
        self.cost_engine = cost_engine
    
    def breakeven_occupancy(
        self,
        prices: List[float],
        occupancy_step: float = 0.001,
        days_in_period: int = 365,
    ) -> float:
        """
        Calcula la ocupación de punto de equilibrio.
        
        Args:
            prices: Lista de precios por categoría (mismo orden que room_categories)
            occupancy_step: Precisión del cálculo (default 0.1%)
            days_in_period: Días del período
        
        Returns:
            Ocupación de break-even (0.0 - 1.0)
        """
        total_fixed = self.cost_engine.total_fixed_costs
        rooms = self.cost_engine.room_categories
        
        # Buscar ocupación donde Ingresos = Costes Totales
        occ = occupancy_step
        while occ <= 1.0:
            total_revenue = 0.0
            total_variable = 0.0
            
            for i, cat in enumerate(rooms):
                price = prices[i] if i < len(prices) else 100.0
                cat_nights = cat.room_count * days_in_period * occ
                total_revenue += price * cat_nights
                
                # Estimar coste variable (precio fijo para simplificar)
                vc_per_night = cat.base_rate_2025 * 0.20  # ~20% del rate como VC
                total_variable += vc_per_night * cat_nights
            
            total_costs = total_fixed + total_variable
            
            if total_revenue >= total_costs:
                return round(occ, 4)
            
            occ += occupancy_step
        
        return 1.0  # Nunca alcanza break-even
    
    def breakeven_revenue(
        self,
        total_fixed_costs: float,
        total_variable_costs: float,
        total_revenue: float,
    ) -> float:
        """
        Calcula el ingreso de punto de equilibrio.
        
        BE_Revenue = FixedCosts / (1 - VariableCostRatio)
        """
        if total_revenue == 0:
            return 0.0
        
        variable_cost_ratio = total_variable_costs / total_revenue
        
        if variable_cost_ratio >= 1.0:
            return float('inf')  # Nunca alcanza break-even
        
        return round(total_fixed_costs / (1 - variable_cost_ratio), 2)
    
    def margin_of_safety(
        self,
        current_revenue: float,
        breakeven_revenue: float,
    ) -> float:
        """
        Margen de seguridad = (IngresoActual - BE) / IngresoActual * 100
        
        Indica cuánto pueden caer los ingresos antes de entrar en pérdidas.
        """
        if current_revenue == 0:
            return 0.0
        return round((current_revenue - breakeven_revenue) / current_revenue * 100, 2)
    
    def contribution_margin_ratio(
        self,
        price: float,
        variable_cost_per_night: float,
    ) -> float:
        """
        Ratio de margen de contribución = (P - VC) / P
        
        Porcentaje de cada euro de ingreso que contribuye a cubrir costes fijos.
        """
        if price == 0:
            return 0.0
        return round((price - variable_cost_per_night) / price, 4)
    
    def breakeven_report(
        self,
        prices: List[float],
        occupancy: float = 0.70,
        days_in_period: int = 365,
    ) -> dict:
        """
        Reporte completo de break-even.
        """
        be_occ = self.breakeven_occupancy(prices, days_in_period=days_in_period)
        
        # Calcular Ingresos y Costes
        total_fixed = self.cost_engine.total_fixed_costs
        total_revenue = 0.0
        total_variable = 0.0
        
        for i, cat in enumerate(self.cost_engine.room_categories):
            price = prices[i] if i < len(prices) else 100.0
            cat_nights = cat.room_count * days_in_period * occupancy
            total_revenue += price * cat_nights
            vc_per_night = cat.base_rate_2025 * 0.20
            total_variable += vc_per_night * cat_nights
        
        be_rev = self.breakeven_revenue(total_fixed, total_variable, total_revenue)
        mos = self.margin_of_safety(total_revenue, be_rev) if be_rev != float('inf') else 0.0
        
        return {
            "breakeven_occupancy_pct": round(be_occ * 100, 2),
            "breakeven_revenue_eur": be_rev,
            "current_revenue_eur": round(total_revenue, 2),
            "total_fixed_costs_eur": round(total_fixed, 2),
            "total_variable_costs_eur": round(total_variable, 2),
            "margin_of_safety_pct": mos,
            "is_profitable": be_occ < occupancy,
            "status": "RENTABLE" if be_occ < occupancy else "NO_RENTABLE",
        }

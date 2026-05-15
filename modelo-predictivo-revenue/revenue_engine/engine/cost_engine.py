"""
Motor de Costes — Asignación de costes fijos y variables
a categorías de habitación.

Implementa:
    - Agregación de costes fijos mensuales
    - Distribución ponderada por categoría (weight_factor)
    - Cálculo de coste fijo por habitación-noche
    - Cálculo de coste variable por estancia
    - Coste marginal con función sigmoide (refleja escasez)
"""

from dataclasses import dataclass
from typing import List, Optional
import math

from revenue_engine.models import (
    RoomCategory, FixedCost, VariableCost, AllocationMethod,
    CategoryPricing,
)


def sigmoid(x: float, midpoint: float = 0.60, slope: float = 12) -> float:
    """
    Función sigmoide para modelar la transición del coste marginal.
    
    A baja ocupación (<40%): el coste marginal ≈ coste variable
    (la sigmoide está cerca de 0, apenas se añade coste fijo).
    
    A alta ocupación (>80%): el coste marginal ≈ coste total por noche
    (la sigmoide está cerca de 1, el coste fijo se incorpora,
    reflejando que cada venta desplaza a otro cliente potencial).
    """
    return 1.0 / (1.0 + math.exp(-slope * (x - midpoint)))


def calculate_variable_cost_per_night(
    cat: RoomCategory,
    variable_costs: List[VariableCost],
    guests: float = 1.8,
    ota_pct: float = 40.0,
    stay_length: float = 2.0,
    base_price: float = 0.0,
) -> float:
    """
    Calcula el coste variable total por noche para una categoría.
    
    Fórmula:
        VC = Σ(per_stay) / stay_length
           + Σ(per_guest) * (guests - 1)
           + (Price * ota_commission / 100)  -- comisión OTA prorrateada
           + Σ(per_night)
    """
    # Filtrar costes variables de esta categoría
    cat_costs = [vc for vc in variable_costs if vc.room_cat_id == cat.cat_id]
    
    total_per_stay = sum(vc.per_stay_amount for vc in cat_costs if vc.is_per_booking)
    total_per_guest = sum(vc.per_guest_amount for vc in cat_costs)
    total_per_night = sum(vc.per_night_amount for vc in cat_costs if not vc.is_per_booking)
    
    # Coste base
    vc = (total_per_stay / stay_length) + total_per_guest * max(0, guests - 1) + total_per_night
    
    # Comisión OTA (se aplica sobre el precio final, se estima iterativamente)
    avg_ota_commission = 0.0
    ota_costs = [vc for vc in cat_costs if vc.ota_commission_pct > 0]
    if ota_costs and base_price > 0:
        avg_ota_commission = sum(vc.ota_commission_pct for vc in ota_costs) / len(ota_costs)
        # Solo el % de reservas que vienen por OTA paga comisión
        vc += base_price * (avg_ota_commission / 100) * (ota_pct / 100)
    
    return round(vc, 4)


class CostEngine:
    """
    Motor de asignación y cálculo de costes.
    
    Uso:
        engine = CostEngine(room_categories, fixed_costs, variable_costs)
        result = engine.calculate(occupancy=0.70, days_in_period=365)
    """
    
    def __init__(
        self,
        room_categories: List[RoomCategory],
        fixed_costs: List[FixedCost],
        variable_costs: List[VariableCost],
    ):
        self.room_categories = room_categories
        self.fixed_costs = fixed_costs
        self.variable_costs = variable_costs
        self._validate()
    
    def _validate(self):
        """Valida que los datos de entrada sean coherentes."""
        if not self.room_categories:
            raise ValueError("Se necesita al menos una categoría de habitación")
        if not self.fixed_costs:
            raise ValueError("Se necesita al menos un coste fijo")
    
    @property
    def total_fixed_costs_monthly(self) -> float:
        """Costes fijos mensuales totales (activos)."""
        return sum(fc.monthly_amount for fc in self.fixed_costs if fc.is_active)
    
    @property
    def total_fixed_costs(self) -> float:
        """Costes fijos anuales totales (activos)."""
        return self.total_fixed_costs_monthly * 12
    
    @property
    def total_rooms(self) -> int:
        return sum(c.room_count for c in self.room_categories)
    
    def _sum_weights(self) -> float:
        """Suma ponderada de todas las habitaciones (para distribución)."""
        return sum(c.room_count * c.weight_factor for c in self.room_categories)
    
    def calculate(
        self,
        occupancy: float = 0.70,
        days_in_period: int = 365,
        avg_guests: float = 1.8,
        ota_pct: float = 40.0,
        target_margin: float = 20.0,
    ) -> List[CategoryPricing]:
        """
        Calcula la asignación de costes para cada categoría.
        
        Args:
            occupancy: Ocupación esperada (0.0 - 1.0)
            days_in_period: Días del período a simular
            avg_guests: Media de huéspedes por habitación
            ota_pct: Porcentaje de reservas vía OTA
            target_margin: Margen de beneficio objetivo (%)
        
        Returns:
            Lista de CategoryPricing con costes y precios por categoría
        """
        sum_weights = self._sum_weights()
        total_room_nights = self.total_rooms * days_in_period * occupancy
        
        results = []
        
        for cat in self.room_categories:
            pricing = CategoryPricing(
                cat_id=cat.cat_id,
                cat_name=cat.name,
                room_count=cat.room_count,
            )
            
            # 1. Coste fijo asignado a esta categoría
            pricing.fixed_cost_share = (
                self.total_fixed_costs
                * (cat.room_count * cat.weight_factor)
                / sum_weights
            )
            
            # 2. Coste fijo por habitación-noche ocupada
            cat_nights = cat.room_count * days_in_period * occupancy
            pricing.fixed_per_night = (
                pricing.fixed_cost_share / cat_nights if cat_nights > 0 else 0
            )
            
            # 3. Coste variable por noche
            # Primero calculamos un precio estimado para la comisión OTA
            # (usamos el proceso iterativo: pricing → variable → pricing)
            estim_price = cat.base_rate_2025  # punto de partida
            
            pricing.variable_per_night = calculate_variable_cost_per_night(
                cat, self.variable_costs,
                guests=avg_guests, ota_pct=ota_pct,
                stay_length=2.0, base_price=estim_price,
            )
            
            # 4. Coste marginal (con sigmoide de ocupación)
            fixed_component = pricing.fixed_per_night * sigmoid(occupancy)
            pricing.marginal_cost = pricing.variable_per_night + fixed_component
            
            # 5. Precio base (cost-plus)
            pricing.base_price = pricing.marginal_cost * (1 + target_margin / 100)
            
            # Recalcular coste variable con el precio real
            pricing.variable_per_night = calculate_variable_cost_per_night(
                cat, self.variable_costs,
                guests=avg_guests, ota_pct=ota_pct,
                stay_length=2.0, base_price=pricing.base_price,
            )
            
            # Recalcular marginal y precio final
            pricing.marginal_cost = pricing.variable_per_night + fixed_component
            pricing.base_price = max(
                pricing.marginal_cost * (1 + target_margin / 100),
                pricing.marginal_cost * 1.05,  # margen mínimo del 5%
            )
            
            results.append(pricing)
        
        return results
    
    def get_category_pricing_summary(self, pricing_list: List[CategoryPricing]) -> str:
        """Genera un resumen tabular de los precios por categoría."""
        lines = [
            f"{'Categoría':<20} {'Ud.':>4} {'CosteFijo/N':>12} {'CosteVar/N':>12} "
            f"{'CosteMarg':>12} {'Precio':>12} {'Margen€':>10} {'Margen%':>8}"
        ]
        lines.append("─" * 90)
        
        for p in pricing_list:
            margin_eur = p.base_price - p.marginal_cost
            margin_pct = (margin_eur / p.base_price * 100) if p.base_price > 0 else 0
            lines.append(
                f"{p.cat_name:<20} {p.room_count:>4} {p.fixed_per_night:>10.2f}€ "
                f"{p.variable_per_night:>10.2f}€ {p.marginal_cost:>10.2f}€ "
                f"{p.base_price:>10.2f}€ {margin_eur:>8.2f}€ {margin_pct:>6.1f}%"
            )
        
        lines.append("─" * 90)
        return "\n".join(lines)

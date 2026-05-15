"""
Modelos de datos del sistema de Revenue Management.

Define las estructuras de datos para:
    - Categorías de habitación
    - Costes fijos y variables
    - Parámetros de inversión
    - Escenarios de ocupación
    - Resultados de simulación
"""

from dataclasses import dataclass, field, asdict
from datetime import date, datetime
from typing import Optional, Dict, List, Any
from enum import Enum
import json


# ──────────────────────────────────────────────
# ENUMS
# ──────────────────────────────────────────────

class AllocationMethod(str, Enum):
    EQUAL = "equal"
    WEIGHTED = "weighted"
    SQM = "sqm"


class ScenarioName(str, Enum):
    PESIMISTA = "pesimista"
    REALISTA = "realista"
    OPTIMISTA = "optimista"


class PricingAction(str, Enum):
    RAISE = "raise"
    HOLD = "hold"
    LOWER = "lower"
    DISTRESS = "distress"


class ChannelStrategy(str, Enum):
    OPEN_ALL = "open_all"
    OTA_RESTRICTED = "ota_restricted"
    DIRECT_PRIORITY = "direct_priority"
    DIRECT_ONLY = "direct_only"


# ──────────────────────────────────────────────
# CATEGORÍAS DE HABITACIÓN
# ──────────────────────────────────────────────

@dataclass
class RoomCategory:
    """Categoría de habitación del hotel."""
    cat_id: str
    code: str
    name: str
    room_count: int
    max_guests: int
    sqm: float
    base_rate_2025: float
    weight_factor: float
    description: str = ""


# ──────────────────────────────────────────────
# COSTES FIJOS
# ──────────────────────────────────────────────

@dataclass
class FixedCost:
    """Partida de coste fijo mensual."""
    line_id: str
    line_name: str
    category: str                         # staff, mantenimiento, suministros, seguros, marketing, admin, tech, financiero
    monthly_amount: float
    alloc_method: AllocationMethod = AllocationMethod.WEIGHTED
    is_active: bool = True
    notes: str = ""


# ──────────────────────────────────────────────
# COSTES VARIABLES
# ──────────────────────────────────────────────

@dataclass
class VariableCost:
    """Coste variable por estancia para una categoría de habitación."""
    cost_id: str
    room_cat_id: str
    line_name: str
    per_stay_amount: float = 0.0
    per_guest_amount: float = 0.0
    per_night_amount: float = 0.0
    is_per_booking: bool = True
    ota_commission_pct: float = 0.0


# ──────────────────────────────────────────────
# INVERSIÓN
# ──────────────────────────────────────────────

@dataclass
class InvestmentParams:
    """Parámetros de inversión y financiación."""
    total_investment: float = 1_200_000.00
    target_roi_pct: float = 15.0
    target_margin_pct: float = 20.0
    loan_amount: float = 600_000.00
    loan_annual_rate: float = 4.5
    loan_term_years: int = 10
    amortization_years: int = 20
    wacc: float = 6.0


# ──────────────────────────────────────────────
# OCUPACIÓN
# ──────────────────────────────────────────────

@dataclass
class OccupancyScenario:
    """Escenario de ocupación para simulación."""
    scenario_id: str
    scenario_name: ScenarioName
    annual_occupancy_pct: float
    season_high_occ_pct: float
    season_low_occ_pct: float
    avg_stay_days: float = 2.0


# ──────────────────────────────────────────────
# CONFIGURACIÓN COMPLETA DEL HOTEL
# ──────────────────────────────────────────────

@dataclass
class HotelConfig:
    """Configuración completa del hotel para el motor de revenue."""
    hotel_name: str = "Hotel Posada de la Sillería"
    location: str = "Toledo, España"
    currency: str = "EUR"
    days_in_period: int = 365
    
    room_categories: List[RoomCategory] = field(default_factory=list)
    fixed_costs: List[FixedCost] = field(default_factory=list)
    variable_costs: List[VariableCost] = field(default_factory=list)
    investment: InvestmentParams = field(default_factory=InvestmentParams)
    scenarios: List[OccupancyScenario] = field(default_factory=list)
    
    # Líneas de negocio
    biz_lines: Dict[str, Dict] = field(default_factory=lambda: {
        "ALOJ": {"name": "Alojamiento",       "expected_revenue_pct": 65.0, "direct_cost_pct": 15.0},
        "REST": {"name": "Restauración",       "expected_revenue_pct": 25.0, "direct_cost_pct": 45.0},
        "EVENT": {"name": "Eventos",           "expected_revenue_pct": 10.0, "direct_cost_pct": 35.0},
    })
    
    @classmethod
    def from_seed(cls, seed_name: str = "posada_silleria") -> "HotelConfig":
        """Carga la configuración desde los datos semilla."""
        from revenue_engine.seeds.seed_data import load_seed
        return load_seed(seed_name)
    
    def total_rooms(self) -> int:
        return sum(c.room_count for c in self.room_categories)
    
    def to_dict(self) -> dict:
        return asdict(self)


# ──────────────────────────────────────────────
# INPUT DE SIMULACIÓN
# ──────────────────────────────────────────────

@dataclass
class SimulationInput:
    """Parámetros de entrada para una simulación."""
    occupancy_pct: float = 0.70
    target_margin_pct: float = 20.0
    target_roi_pct: float = 15.0
    total_investment: float = 1_200_000.0
    avg_guests_per_room: float = 1.8
    avg_ota_pct: float = 40.0                    # % reservas vía OTA
    days_in_period: int = 365
    start_date: Optional[date] = None
    
    # Escenario
    scenario_name: ScenarioName = ScenarioName.REALISTA


# ──────────────────────────────────────────────
# RESULTADOS
# ──────────────────────────────────────────────

@dataclass
class CategoryPricing:
    """Precios y costes para una categoría en una simulación."""
    cat_id: str
    cat_name: str
    room_count: int
    
    fixed_cost_share: float = 0.0
    fixed_per_night: float = 0.0
    variable_per_night: float = 0.0
    marginal_cost: float = 0.0
    base_price: float = 0.0
    
    # Desglose mensual
    prices_by_season: Dict[str, float] = field(default_factory=dict)


@dataclass
class SimulationResult:
    """Resultado completo de una simulación."""
    input_used: SimulationInput = field(default_factory=SimulationInput)
    
    # Métricas globales
    total_rooms: int = 0
    total_room_nights: int = 0
    total_revenue: float = 0.0
    total_fixed_costs: float = 0.0
    total_variable_costs: float = 0.0
    total_costs: float = 0.0
    net_profit: float = 0.0
    net_margin_pct: float = 0.0
    
    # Break-even
    breakeven_occupancy_pct: float = 0.0
    breakeven_revenue: float = 0.0
    
    # ROI
    roi_pct: float = 0.0
    payback_years: float = 0.0
    economic_value_added: float = 0.0
    
    # Reparto de beneficio
    allocated_profits: Dict[str, float] = field(default_factory=dict)
    
    # Desglose por categoría
    category_pricing: List[CategoryPricing] = field(default_factory=list)
    
    # Precios dinámicos por fecha
    daily_prices: Optional[Dict[str, Dict[str, float]]] = None
    
    # Reporte mensual
    monthly_pnl: Optional[List[Dict]] = None
    
    def executive_summary(self) -> str:
        lines = [
            "╔══════════════════════════════════════════════════╗",
            "║     RESULTADO DE SIMULACIÓN — HOTEL POSADA       ║",
            "║               DE LA SILLERÍA (TOLEDO)            ║",
            "╠══════════════════════════════════════════════════╣",
            f"  Ocupación:              {self.input_used.occupancy_pct:.1%}",
            f"  Habitaciones totales:   {self.total_rooms}",
            f"  Noches totales:         {self.total_room_nights:,}",
            f"  Ingreso bruto anual:    {self.total_revenue:>12,.2f} €",
            f"  Costes totales:         {self.total_costs:>12,.2f} €",
            f"  Beneficio neto:         {self.net_profit:>12,.2f} €",
            f"  Margen neto:            {self.net_margin_pct:.2f}%",
            "╠══════════════════════════════════════════════════╣",
            f"  Break-Even Ocupación:   {self.breakeven_occupancy_pct:.1f}%",
            f"  Break-Even Ingresos:    {self.breakeven_revenue:>12,.2f} €",
            "╠══════════════════════════════════════════════════╣",
            f"  ROI Anual:              {self.roi_pct:.2f}%",
            f"  Payback Period:         {self.payback_years:.2f} años",
            f"  EVA:                    {self.economic_value_added:>12,.2f} €",
            "╚══════════════════════════════════════════════════╝",
        ]
        return "\n".join(lines)
    
    def to_dict(self) -> dict:
        return asdict(self)


# ──────────────────────────────────────────────
# BOOKING PACE
# ──────────────────────────────────────────────

@dataclass
class BookingPaceSnapshot:
    """Snapshot del ritmo de reservas para una fecha."""
    snapshot_date: date
    arrival_date: date
    days_before_arrival: int
    room_cat_id: str
    
    bookings_confirmed: int = 0
    rooms_sold: int = 0
    revenue_booked: float = 0.0
    avg_rate_booked: float = 0.0
    
    bookings_pending: int = 0
    bookings_pending_value: float = 0.0
    
    projected_occupancy: float = 0.0
    projection_confidence: float = 0.0
    
    pricing_action: PricingAction = PricingAction.HOLD
    suggested_price: float = 0.0


@dataclass
class DailyPricePoint:
    """Precio dinámico para una fecha específica."""
    date: date
    room_cat_id: str
    season: str
    season_coefficient: float
    base_price: float
    booking_pace_correction: float = 0.0
    final_price: float = 0.0
    projected_occupancy: float = 0.0
    confidence: float = 0.0
    action: PricingAction = PricingAction.HOLD
    channel_strategy: ChannelStrategy = ChannelStrategy.OPEN_ALL

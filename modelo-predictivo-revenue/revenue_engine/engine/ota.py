"""
Modelo de Comisiones OTA y Estrategia de Canales.

Implementa:
    - Coste de adquisición por canal (CAC)
    - Análisis de marginalidad por canal
    - Estrategia de Value-Added Parity (VAP)
    - Asignación dinámica de inventario por canal
    - Modelo de canibalización entre canales
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple
from enum import Enum

from revenue_engine.config import PricingConfig, DEFAULT_CONFIG
from revenue_engine.models import ChannelStrategy


class CommissionModel:
    """
    Modelo de comisiones y costes por canal de venta.
    
    Cada canal tiene una estructura de costes diferente:
    - Directo (web):     ~2% (pasarela + mantenimiento)
    - Directo (teléfono): ~0.5% (TPV)
    - Booking:            15%
    - Expedia:            18%
    - OTA menor:          15-20%
    """
    
    # Costes por canal (% sobre BAR)
    CHANNEL_COSTS: Dict[str, float] = {
        "direct_web":        2.0,
        "direct_phone":      0.5,
        "direct_walkin":     0.0,
        "booking":          15.0,
        "expedia":          18.0,
        "ota_minor":        17.0,
        "google_hotel_ads": 12.0,
    }
    
    # Marketing attributable cost (additional)
    CHANNEL_MARKETING: Dict[str, float] = {
        "direct_web":        0.0,   # SEO traffic = free
        "direct_phone":      0.0,
        "direct_walkin":     0.0,
        "booking":           0.0,
        "expedia":           0.0,
        "ota_minor":         0.0,
        "google_hotel_ads":  3.5,  # CPC cost ≈ €3.50/click
    }
    
    def __init__(
        self,
        bar_price: float = 100.0,
        config: PricingConfig = DEFAULT_CONFIG,
    ):
        self.bar_price = bar_price
        self.config = config
    
    def net_revenue(self, channel: str) -> float:
        """Ingreso neto después de comisiones para un canal."""
        commission = self.CHANNEL_COSTS.get(channel, 0)
        marketing = self.CHANNEL_MARKETING.get(channel, 0)
        total_cost_pct = commission + marketing
        return round(self.bar_price * (1 - total_cost_pct / 100), 2)
    
    def cac_pct(self, channel: str) -> float:
        """Customer Acquisition Cost como porcentaje del BAR."""
        return self.CHANNEL_COSTS.get(channel, 0) + self.CHANNEL_MARKETING.get(channel, 0)
    
    def margin_loss_pct(self, channel: str) -> float:
        """Porcentaje de margen perdido por usar este canal vs. canal directo."""
        direct_net = self.net_revenue("direct_web")
        channel_net = self.net_revenue(channel)
        if direct_net == 0:
            return 0
        return round((direct_net - channel_net) / direct_net * 100, 2)
    
    def channel_report(self) -> List[Dict]:
        """Reporte comparativo de todos los canales."""
        report = []
        for channel in sorted(self.CHANNEL_COSTS.keys()):
            report.append({
                "channel": channel,
                "commission_pct": self.CHANNEL_COSTS[channel],
                "marketing_pct": self.CHANNEL_MARKETING[channel],
                "total_cac_pct": self.cac_pct(channel),
                "net_revenue": self.net_revenue(channel),
                "margin_loss_pct": self.margin_loss_pct(channel),
            })
        return report


class ValueAddedParity:
    """
    Estrategia de Value-Added Parity (VAP).
    
    Como la paridad de precios impide vender más barato en canal directo,
    competimos en VALOR AÑADIDO en lugar de precio.
    
    Cada incentivo tiene un coste para el hotel y un valor percibido
    por el huésped. Seleccionamos los de mejor ratio coste/valor.
    """
    
    # Catálogo de incentivos disponibles
    INCENTIVES: Dict[str, Dict] = {
        "desayuno_incluido": {
            "name": "Desayuno incluido (2 pax)",
            "cost": 12.0,
            "perceived_value": 20.0,
            "cost_value_ratio": 0.60,
        },
        "late_checkout": {
            "name": "Late checkout hasta 14:00",
            "cost": 0.0,
            "perceived_value": 25.0,
            "cost_value_ratio": 0.0,
        },
        "welcome_pack": {
            "name": "Welcome pack (vino D.O. + mazapán)",
            "cost": 8.0,
            "perceived_value": 18.0,
            "cost_value_ratio": 0.44,
        },
        "parking": {
            "name": "Parking gratuito",
            "cost": 15.0,
            "perceived_value": 22.0,
            "cost_value_ratio": 0.68,
        },
        "upgrade": {
            "name": "Upgrade de categoría (si disponible)",
            "cost": 0.0,
            "perceived_value": 40.0,
            "cost_value_ratio": 0.0,
        },
        "agua_fruta": {
            "name": "Botella de agua + fruta en habitación",
            "cost": 2.0,
            "perceived_value": 8.0,
            "cost_value_ratio": 0.25,
        },
    }
    
    def __init__(
        self,
        bar_price: float,
        ota_commission_pct: float = 15.0,
        direct_cost_pct: float = 2.0,
    ):
        self.bar_price = bar_price
        self.ota_commission_pct = ota_commission_pct
        self.direct_cost_pct = direct_cost_pct
    
    @property
    def max_incentive_budget(self) -> float:
        """Presupuesto máximo para incentivo = ahorro de comisión OTA."""
        ota_cost = self.bar_price * self.ota_commission_pct / 100
        direct_cost = self.bar_price * self.direct_cost_pct / 100
        return round(ota_cost - direct_cost, 2)
    
    def select_incentives(self, max_budget: Optional[float] = None) -> List[Dict]:
        """
        Selecciona los mejores incentivos hasta agotar el presupuesto.
        
        Prioriza los de mejor ratio coste/valor percibido.
        """
        if max_budget is None:
            max_budget = self.max_incentive_budget
        
        sorted_incentives = sorted(
            self.INCENTIVES.values(),
            key=lambda x: x["cost_value_ratio"],
        )
        
        selected = []
        remaining = max_budget
        
        for inc in sorted_incentives:
            if inc["cost"] <= remaining:
                selected.append(inc)
                remaining -= inc["cost"]
        
        return selected


class ChannelManager:
    """
    Gestor de asignación de inventario por canal.
    
    Decide qué canales abrir/cerrar según:
    - Ocupación proyectada
    - Ingreso neto por canal
    - Probabilidad de conversión
    - Estrategia de precio dinámico
    """
    
    def __init__(
        self,
        config: PricingConfig = DEFAULT_CONFIG,
    ):
        self.config = config
    
    def determine_strategy(
        self,
        projected_occupancy: float,
        booking_velocity_index: float = 1.0,
        days_before_arrival: int = 30,
    ) -> ChannelStrategy:
        """
        Determina la estrategia de canales según ocupación y demanda.
        
        Reglas:
            < 30%:  Abrir todos los canales, emergencia
            30-55%: Mantener todos, normal
            55-80%: Restringir OTAs gradualmente
            80-92%: Cerrar OTAs de alta comisión, priorizar directo
            > 92%:  Solo canal directo
        """
        if projected_occupancy >= 0.92:
            return ChannelStrategy.DIRECT_ONLY
        
        if projected_occupancy >= 0.80:
            return ChannelStrategy.DIRECT_PRIORITY
        
        if projected_occupancy >= 0.55:
            return ChannelStrategy.OTA_RESTRICTED
        
        return ChannelStrategy.OPEN_ALL
    
    def calculate_allocation(
        self,
        total_rooms: int,
        projected_occupancy: float,
        strategy: ChannelStrategy,
        direct_bookings: int = 0,
        ota_bookings: int = 0,
    ) -> Dict[str, int]:
        """
        Calcula la asignación de habitaciones por canal.
        
        Returns:
            Dict con {canal: habitaciones_asignadas}
        """
        available = int(total_rooms * projected_occupancy)
        
        if strategy == ChannelStrategy.DIRECT_ONLY:
            return {"direct": available, "ota": 0}
        
        elif strategy == ChannelStrategy.DIRECT_PRIORITY:
            direct_share = int(available * 0.70)
            return {"direct": direct_share, "ota": available - direct_share}
        
        elif strategy == ChannelStrategy.OTA_RESTRICTED:
            direct_share = int(available * 0.50)
            return {"direct": direct_share, "ota": available - direct_share}
        
        else:  # OPEN_ALL
            direct_share = int(available * 0.35)
            return {"direct": direct_share, "ota": available - direct_share}
    
    def net_channel_revenue(
        self,
        bar_price: float,
        strategy: ChannelStrategy,
        allocation: Dict[str, int],
        ota_commission: float = 15.0,
    ) -> Dict[str, float]:
        """Calcula el ingreso neto por canal."""
        direct_net = bar_price * (1 - 2.0 / 100)  # ~2% coste directo
        ota_net = bar_price * (1 - ota_commission / 100)
        
        return {
            "direct": round(direct_net * allocation.get("direct", 0), 2),
            "ota": round(ota_net * allocation.get("ota", 0), 2),
            "total": round(
                direct_net * allocation.get("direct", 0)
                + ota_net * allocation.get("ota", 0),
                2,
            ),
        }


class CannibalizationModel:
    """
    Modelo de canibalización entre canales OTA y directo.
    
    Las OTAs canibalizan al canal directo, pero también lo alimentan
    (efecto escaparate). Cada reserva OTA puede:
    - Robar una reserva que habría ido a directo (canibalización)
    - Ser incremental (nuevo cliente que no habría reservado)
    
    NetDirectBookings = GrossDirectBookings - α * OTABookings
    """
    
    def __init__(self, alpha: float = 0.20):
        """
        Args:
            alpha: Coeficiente de canibalización
                α = 0.10: Baja — OTAs atraen demanda incremental
                α = 0.40: Alta — OTAs roban demanda que iría a directo
        """
        self.alpha = alpha
    
    def net_direct_bookings(
        self,
        gross_direct: int,
        ota_bookings: int,
    ) -> int:
        """Reservas directas netas después de canibalización."""
        return max(0, int(gross_direct - self.alpha * ota_bookings))
    
    def analyze_channel_mix(
        self,
        bar_price: float,
        direct_demand: int,
        ota_demand: int,
        direct_cost_pct: float = 2.0,
        ota_cost_pct: float = 15.0,
    ) -> Dict:
        """
        Analiza si es más rentable tener OTA activo o no.
        
        Returns:
            Dict con ingresos netos comparativos
        """
        direct_rate = bar_price * (1 - direct_cost_pct / 100)
        ota_rate = bar_price * (1 - ota_cost_pct / 100)
        
        # Con OTA
        net_direct_with_ota = self.net_direct_bookings(direct_demand, ota_demand)
        revenue_with_ota = (
            net_direct_with_ota * direct_rate
            + ota_demand * ota_rate
        )
        
        # Sin OTA (la demanda directa podría aumentar)
        estimated_direct_without_ota = int(direct_demand * 1.15)  # +15% estimado
        revenue_without_ota = estimated_direct_without_ota * direct_rate
        
        ota_incremental = revenue_with_ota > revenue_without_ota
        
        return {
            "bar_price": bar_price,
            "cannibalization_alpha": self.alpha,
            "direct_demand": direct_demand,
            "ota_demand": ota_demand,
            "net_direct_with_ota": net_direct_with_ota,
            "revenue_with_ota": round(revenue_with_ota, 2),
            "revenue_without_ota": round(revenue_without_ota, 2),
            "ota_is_incremental": ota_incremental,
            "delta_with_ota": round(revenue_with_ota - revenue_without_ota, 2),
            "recommendation": "RETAIN_OTA" if ota_incremental else "CONSIDER_DROPPING_OTA",
        }

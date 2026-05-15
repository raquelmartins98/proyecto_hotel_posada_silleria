"""
Motor de Booking Pace Forecasting — Proyección de Ocupación
basada en el ritmo de reservas.

Implementa:
    - Curva de pickup normalizada por Pattern Matching
    - Booking Velocity Index (BVI)
    - Proyección de ocupación final
    - Nivel de confianza de la proyección
    - Corrección de precio basada en BVI
"""

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple, Callable
import math
import random

from revenue_engine.config import PricingConfig, DEFAULT_CONFIG
from revenue_engine.models import PricingAction


@dataclass
class BookingCurvePoint:
    """Punto de una curva de booking acumulada."""
    days_before_arrival: int
    cumulative_pct: float  # % de ocupación final alcanzada a esta antelación


@dataclass
class BookingCurve:
    """Curva histórica de booking para un perfil de fecha."""
    season: str
    day_of_week: int
    room_cat_id: str
    is_puente: bool = False
    is_event: bool = False
    
    mean_final_occ: float = 0.0
    stddev_final_occ: float = 0.0
    pickup_rate_peak_dba: int = 0
    pickup_rate_peak_val: float = 0.0
    sample_size: int = 0
    
    # Curva: lista de puntos [dba, cumulative_pct]
    # indexed by dba (0 = día de llegada, 365 = un año antes)
    profile: List[float] = field(default_factory=lambda: [0.0] * 366)
    
    def get_pct_at_dba(self, dba: int) -> float:
        """% acumulado a una antelación dada."""
        idx = max(0, min(dba, 365))
        return self.profile[idx]
    
    def get_pickup(self, from_dba: int, to_dba: int) -> float:
        """Pickup (incremento de ocupación) entre dos antelaciones."""
        return max(0, self.get_pct_at_dba(from_dba) - self.get_pct_at_dba(to_dba))


class BookingPaceEngine:
    """
    Motor de forecasting por ritmo de reservas.
    
    Proyecta la ocupación final comparando el booking actual
    con curvas históricas de reservas.
    """
    
    def __init__(
        self,
        config: PricingConfig = DEFAULT_CONFIG,
        curves: Optional[Dict[str, BookingCurve]] = None,
    ):
        self.config = config
        
        # Si no hay curvas históricas, usar curvas sintéticas genéricas
        self.curves = curves or self._generate_default_curves()
    
    def _generate_default_curves(self) -> Dict[str, BookingCurve]:
        """
        Genera curvas sintéticas para hoteles boutique.
        
        Útil para cold start (sin datos históricos del hotel).
        Basado en patrones típicos de hoteles urbanos culturales.
        """
        curves = {}
        
        profiles = {
            "weekday_high": {  # Primavera/Otoño entre semana
                "final_occ": 0.65, "peak_dba": 14, "peak_val": 0.08,
            },
            "weekend_high": {  # Primavera/Otoño fin de semana
                "final_occ": 0.80, "peak_dba": 7, "peak_val": 0.12,
            },
            "event": {  # Semana Santa / Corpus
                "final_occ": 0.92, "peak_dba": 60, "peak_val": 0.04,
            },
            "low": {  # Verano / Invierno
                "final_occ": 0.45, "peak_dba": 7, "peak_val": 0.06,
            },
            "puente": {  # Puentes
                "final_occ": 0.88, "peak_dba": 30, "peak_val": 0.06,
            },
        }
        
        for key, params in profiles.items():
            curve = BookingCurve(
                season=key,
                day_of_week=0,
                room_cat_id="generic",
                mean_final_occ=params["final_occ"],
                pickup_rate_peak_dba=params["peak_dba"],
                pickup_rate_peak_val=params["peak_val"],
                sample_size=24,
            )
            
            # Generar perfil: logístico inverso con pickup peak
            profile = [0.0] * 366
            for dba in range(366):
                # Curva logística: L / (1 + exp(-k * (x - x0)))
                # A más cerca de llegada (dba pequeño), mayor ocupación
                x = dba / 365.0  # normalizado
                L = params["final_occ"]
                k = 8.0  # pendiente
                x0 = 0.4  # punto medio
                profile[dba] = L / (1 + math.exp(-k * (x - x0) + 2))
            
            # Ajustar para que a dba=0 sea exactamente final_occ
            if profile[0] > 0:
                scale = params["final_occ"] / profile[0]
                profile = [min(p * scale, 1.0) for p in profile]
            
            curve.profile = profile
            curves[key] = curve
        
        return curves
    
    def _get_curve_for_date(
        self,
        d: date,
        room_cat_id: str,
        is_puente: bool = False,
        is_event: bool = False,
    ) -> BookingCurve:
        """Selecciona la curva más apropiada para una fecha."""
        
        if is_event:
            return self.curves.get("event", list(self.curves.values())[0])
        if is_puente:
            return self.curves.get("puente", list(self.curves.values())[0])
        
        dow = d.weekday()
        if dow >= 4:  # viernes/sábado
            return self.curves.get("weekend_high", list(self.curves.values())[0])
        
        return self.curves.get("weekday_high", list(self.curves.values())[0])
    
    def calculate_bvi(
        self,
        curve: BookingCurve,
        dba: int,
        actual_pickups: int = 0,
    ) -> float:
        """
        Booking Velocity Index (BVI).
        
        BVI = ActualPickups(últimos_7_días) / ExpectedPickups(últimos_7_días)
        
        > 1.30: Demanda muy superior → subir precios
        1.05-1.30: Demanda superior → subir ligeramente
        0.95-1.05: En línea → mantener
        0.75-0.95: Demanda inferior → bajar ligeramente
        < 0.75: Demanda muy inferior → bajar precios
        """
        expected_pickup = curve.get_pickup(dba, max(0, dba - self.config.bvi_window_days))
        
        if expected_pickup <= 0:
            return 1.0  # No hay datos históricos
        
        bvi = actual_pickups / expected_pickup
        return round(bvi, 4)
    
    def project_occupancy(
        self,
        d: date,
        current_bookings_pct: float,
        total_rooms: int,
        is_puente: bool = False,
        is_event: bool = False,
        room_cat_id: str = "generic",
        dba: Optional[int] = None,
    ) -> Tuple[float, float]:
        """
        Proyecta la ocupación final para una fecha.
        
        Args:
            d: Fecha de llegada
            current_bookings_pct: Ocupación actual (%)
            total_rooms: Total de habitaciones
            dba: Días antes de la llegada (calculado automáticamente si None)
        
        Returns:
            (projected_occupancy_pct, confidence)
        """
        if dba is None:
            dba = max(0, (d - date.today()).days)
        
        curve = self._get_curve_for_date(d, room_cat_id, is_puente, is_event)
        
        # Encontrar punto equivalente en la curva histórica
        hist_pct_at_dba = curve.get_pct_at_dba(dba)
        
        if hist_pct_at_dba <= 0:
            # Sin referencia histórica, usar proyección conservadora
            projected = current_bookings_pct + 0.15  # +15% estimado
        else:
            # Ratio de cómo vamos respecto a la curva histórica
            ratio = current_bookings_pct / hist_pct_at_dba
            
            # Proyectar: final_occ = ratio * historical_final_occ
            projected = ratio * curve.mean_final_occ * 100
        
        projected = min(projected, 100.0)
        projected = max(projected, current_bookings_pct)
        
        # Calcular confianza
        confidence = self._calculate_confidence(dba, curve.sample_size)
        
        return round(projected, 2), round(confidence, 4)
    
    def _calculate_confidence(self, dba: int, sample_size: int) -> float:
        """
        Nivel de confianza de la proyección.
        
        Disminuye a medida que nos acercamos a la fecha porque
        hay menos margen de corrección.
        """
        base_confidence = 0.85
        time_factor = 1 - 0.5 * math.exp(-0.01 * dba)
        sample_factor = min(sample_size / 10.0, 1.0)
        
        return base_confidence * time_factor * sample_factor
    
    def price_correction_by_bvi(
        self,
        base_price: float,
        bvi: float,
    ) -> float:
        """
        Corrige el precio base según el Booking Velocity Index.
        
        Corrección = CLAMP(BVI - 1, max_decrease, max_increase)
        """
        correction = bvi - 1.0
        correction = max(correction, -self.config.max_price_decrease)
        correction = min(correction, self.config.max_price_increase)
        
        return round(base_price * (1 + correction), 2)
    
    def snapshot_report(
        self,
        d: date,
        current_bookings: int,
        total_rooms: int,
        current_price: float,
        room_cat_id: str = "generic",
    ) -> Dict:
        """
        Reporte completo de booking pace para una fecha.
        """
        dba = max(0, (d - date.today()).days)
        current_pct = (current_bookings / total_rooms * 100) if total_rooms > 0 else 0
        
        curve = self._get_curve_for_date(d, room_cat_id)
        projected_occ, confidence = self.project_occupancy(
            d, current_pct, total_rooms, room_cat_id=room_cat_id, dba=dba
        )
        
        # Simular pickup para BVI (en producción viene del PMS)
        expected_pickup = curve.get_pickup(dba, max(0, dba - 7))
        actual_pickup = expected_pickup * random.uniform(0.7, 1.3)  # simulado
        bvi = self.calculate_bvi(curve, dba, actual_pickup)
        corrected_price = self.price_correction_by_bvi(current_price, bvi)
        
        # Determinar acción
        if bvi > self.config.bvi_threshold_up:
            action = PricingAction.RAISE
        elif bvi < self.config.bvi_threshold_down:
            action = PricingAction.LOWER if current_price > corrected_price else PricingAction.DISTRESS
        else:
            action = PricingAction.HOLD
        
        return {
            "arrival_date": d.isoformat(),
            "days_before_arrival": dba,
            "current_bookings": current_bookings,
            "total_rooms": total_rooms,
            "current_occupancy_pct": round(current_pct, 2),
            "historical_expected_pct": round(curve.get_pct_at_dba(dba) * 100, 2),
            "projected_occupancy_pct": projected_occ,
            "confidence": confidence,
            "booking_velocity_index": bvi,
            "bvi_label": self._bvi_label(bvi),
            "current_price": current_price,
            "corrected_price": corrected_price,
            "recommended_action": action.value,
        }
    
    @staticmethod
    def _bvi_label(bvi: float) -> str:
        if bvi >= 1.30:
            return "Demanda muy superior"
        elif bvi >= 1.05:
            return "Demanda superior"
        elif bvi >= 0.95:
            return "En línea con histórico"
        elif bvi >= 0.75:
            return "Demanda inferior"
        else:
            return "Demanda muy inferior"

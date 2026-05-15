"""
Calendario turístico y matriz estacional de Toledo.

Define los períodos turísticos, coeficientes estacionales, eventos locales
y funciones de interpolación para el Hotel Posada de la Sillería.
"""

from datetime import date, timedelta
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
import math


# ──────────────────────────────────────────────
# MATRIZ ESTACIONAL — COEFICIENTES BASE
# ──────────────────────────────────────────────

SEASONAL_COEFFICIENTS: Dict[str, float] = {
    "S_BAJA_INV":      0.80,   # Baja Invierno:   8 Ene — 15 Feb
    "S_MEDIA_INV":     0.90,   # Media Invierno:  16 Feb — 14 Mar / 1 Nov — 22 Dic
    "S_SEMANA_SANTA":  1.75,   # Semana Santa:    Domingo de Ramos a Domingo de Resurrección
    "S_PRIMAVERA":     1.10,   # Primavera:        6 Abr — 30 May (excl. puentes y SS)
    "S_CORPUS":        1.50,   # Corpus Christi:   60 días post Domingo de Resurrección
    "S_VERANO":        0.95,   # Verano:           15 Jun — 31 Ago
    "S_OTONO":         1.05,   # Otoño:            1 Sep — 31 Oct
    "S_NAVIDAD":       1.25,   # Navidades:        23 Dic — 7 Ene
    "S_PUENTE":        1.35,   # Puentes nacionales
}

# Temporadas ordenadas por prioridad (de mayor a menor)
SEASON_PRIORITY = [
    "S_SEMANA_SANTA",  # 1.75 — prioridad máxima
    "S_CORPUS",        # 1.50
    "S_NAVIDAD",       # 1.25
    "S_PUENTE",        # 1.35 (se aplica sobre la estacional base)
    "S_PRIMAVERA",     # 1.10
    "S_OTONO",         # 1.05
    "S_VERANO",        # 0.95
    "S_MEDIA_INV",     # 0.90
    "S_BAJA_INV",      # 0.80
]


@dataclass
class SeasonPeriod:
    """Define un período de temporada con sus fechas."""
    code: str
    name: str
    start: Tuple[int, int]  # (mes, día)
    end: Tuple[int, int]    # (mes, día)
    coefficient: float
    is_event: bool = False
    priority: int = 0


@dataclass
class ToledoCalendar:
    """
    Calendario turístico de Toledo con cálculo de coeficientes estacionales.
    
    Incluye:
    - Temporadas base
    - Eventos locales (Semana Santa, Corpus)
    - Puentes nacionales
    - Recargo de fin de semana
    - Interpolación suave entre temporadas
    """
    
    year: int
    interpolation_window: int = 7  # días de transición suave
    
    # Semana Santa (calculada dinámicamente)
    easter_sunday: Optional[date] = None
    
    def __post_init__(self):
        self.easter_sunday = self._compute_easter_sunday(self.year)
    
    # ── Cálculo de la fecha de Pascua (Algoritmo de Butcher-Meeus) ──
    @staticmethod
    def _compute_easter_sunday(year: int) -> date:
        a = year % 19
        b = year // 100
        c = year % 100
        d = b // 4
        e = b % 4
        f = (b + 8) // 25
        g = (b - f + 1) // 3
        h = (19 * a + b - d - g + 15) % 30
        i = c // 4
        k = c % 4
        l = (32 + 2 * e + 2 * i - h - k) % 7
        m = (a + 11 * h + 22 * l) // 451
        month = (h + l - 7 * m + 114) // 31
        day = ((h + l - 7 * m + 114) % 31) + 1
        return date(year, month, day)
    
    @property
    def palm_sunday(self) -> date:
        """Domingo de Ramos (7 días antes de Pascua)."""
        return self.easter_sunday - timedelta(days=7)
    
    @property
    def easter_monday(self) -> date:
        return self.easter_sunday + timedelta(days=1)
    
    # ── Generar todos los períodos del año ──
    def get_periods(self) -> List[SeasonPeriod]:
        """Genera todos los períodos estacionales para el año configurado."""
        y = self.year
        
        # Períodos base
        base_periods = [
            SeasonPeriod("S_BAJA_INV",  "Baja Invierno",  (1, 8),   (2, 15),  0.80, priority=1),
            SeasonPeriod("S_MEDIA_INV", "Media Invierno", (2, 16),  (3, 14),  0.90, priority=2),
            SeasonPeriod("S_PRIMAVERA", "Primavera",      (4, 6),   (5, 31),  1.10, priority=4),
            SeasonPeriod("S_VERANO",    "Verano",         (6, 15),  (8, 31),  0.95, priority=6),
            SeasonPeriod("S_OTONO",     "Otoño",          (9, 1),   (10, 31), 1.05, priority=7),
            SeasonPeriod("S_MEDIA_INV", "Media Invierno2",(11, 1),  (12, 22), 0.90, priority=2),
            SeasonPeriod("S_NAVIDAD",   "Navidades",      (12, 23), (1, 7),   1.25, priority=3),
        ]
        
        # Eventos dinámicos
        events = [
            SeasonPeriod(
                "S_SEMANA_SANTA", "Semana Santa",
                (self.palm_sunday.month, self.palm_sunday.day),
                (self.easter_sunday.month, self.easter_sunday.day),
                1.75, is_event=True, priority=9,
            ),
            SeasonPeriod(
                "S_CORPUS", "Corpus Christi",
                ((self.easter_sunday + timedelta(days=60)).month,
                 (self.easter_sunday + timedelta(days=60)).day),
                ((self.easter_sunday + timedelta(days=67)).month,
                 (self.easter_sunday + timedelta(days=67)).day),
                1.50, is_event=True, priority=8,
            ),
        ]
        
        return base_periods + events
    
    # ── Puentes nacionales ──
    def get_puentes(self) -> List[Tuple[date, date, str]]:
        """Retorna lista de (fecha_inicio, fecha_fin, nombre) para puentes."""
        y = self.year
        puentes = []
        
        # San José (si es entre semana, se observa)
        sj = date(y, 3, 19)
        if sj.weekday() < 5:
            if sj.weekday() == 4:  # viernes → puente 3 días
                puentes.append((sj - timedelta(days=1), sj + timedelta(days=1), "San José"))
            else:
                puentes.append((sj, sj, "San José"))
        
        # Fiesta del Trabajo
        fd = date(y, 5, 1)
        if fd.weekday() < 5:
            # Si es viernes, se considera puente
            end = fd + timedelta(days=2) if fd.weekday() == 4 else fd
            puentes.append((fd, end, "Fiesta del Trabajo"))
        
        # Asunción (15 Ago)
        asuncion = date(y, 8, 15)
        if asuncion.weekday() < 5:
            puentes.append((asuncion, asuncion, "Asunción"))
        
        # Hispanidad (12 Oct)
        hisp = date(y, 10, 12)
        if hisp.weekday() < 5:
            if hisp.weekday() == 1:  # lunes → puente 3 días
                puentes.append((hisp, hisp + timedelta(days=1), "Hispanidad"))
            else:
                puentes.append((hisp, hisp, "Hispanidad"))
        
        # Constitución (6 Dic) + Inmaculada (8 Dic)
        const = date(y, 12, 6)
        inma = date(y, 12, 8)
        if const.weekday() < 5 or inma.weekday() < 5:
            # Posible puente de 4 días
            start = const - timedelta(days=1) if const.weekday() == 0 else const
            end = inma + timedelta(days=1) if inma.weekday() == 4 else inma
            puentes.append((start, end, "Constitución + Inmaculada"))
        
        return puentes
    
    def is_puente(self, d: date) -> bool:
        """Determina si una fecha cae dentro de un puente nacional."""
        for start, end, _ in self.get_puentes():
            if start <= d <= end:
                return True
        return False
    
    def is_weekend(self, d: date) -> bool:
        """Viernes (4), Sábado (5) como fin de semana hotelero."""
        return d.weekday() in (4, 5)
    
    def get_season_for_date(self, d: date) -> str:
        """Obtiene la temporada para una fecha, incluyendo eventos y puentes."""
        periods = self.get_periods()
        
        # Eventos tienen máxima prioridad
        for p in sorted(periods, key=lambda x: x.priority, reverse=True):
            if p.is_event and self._date_in_period(d, p):
                return p.code
        
        # Puentes
        if self.is_puente(d):
            return "S_PUENTE"
        
        # Temporada base
        for p in sorted(periods, key=lambda x: x.priority, reverse=True):
            if not p.is_event and self._date_in_period(d, p):
                return p.code
        
        return "S_MEDIA_INV"  # fallback
    
    def _date_in_period(self, d: date, p: SeasonPeriod) -> bool:
        """Comprueba si una fecha cae dentro de un período (maneja cruce de año)."""
        start_month, start_day = p.start
        end_month, end_day = p.end
        
        start_date = date(self.year, start_month, start_day)
        end_date = date(self.year, end_month, end_day)
        
        # Si el período cruza de año (ej: Navidad)
        if end_date < start_date:
            return d >= start_date or d <= end_date
        return start_date <= d <= end_date
    
    def get_coefficient(self, d: date) -> float:
        """
        Calcula el coeficiente estacional completo para una fecha.
        
        Orden de precedencia:
        1. Semana Santa (máxima prioridad)
        2. Corpus Christi
        3. Puente nacional
        4. Temporada base + recargo fin de semana
        5. Interpolación suave en bordes
        """
        coeff = self._base_seasonal_coefficient(d)
        
        # Eventos de máxima prioridad
        for p in self.get_periods():
            if p.is_event and self._date_in_period(d, p):
                coeff = max(coeff, p.coefficient)
        
        # Puentes
        if self.is_puente(d):
            coeff = max(coeff, 1.35)
        
        # Recargo fin de semana
        if self.is_weekend(d):
            coeff *= 1.10
        
        return round(coeff, 4)
    
    def _base_seasonal_coefficient(self, d: date) -> float:
        """Coeficiente base con interpolación suave en bordes de temporada."""
        periods = [p for p in self.get_periods() if not p.is_event]
        periods.sort(key=lambda p: p.priority, reverse=True)
        
        # Buscar período activo
        active_period = None
        for p in periods:
            if self._date_in_period(d, p):
                active_period = p
                break
        
        if not active_period:
            return 1.0
        
        # Comprobar si está en zona de interpolación (bordes del período)
        start_days = self._days_from_boundary(d, active_period)
        
        if start_days is not None and start_days < self.interpolation_window:
            # Interpolar con el período anterior
            prev = self._get_previous_period(active_period, periods)
            if prev:
                t = start_days / self.interpolation_window
                return round(prev.coefficient + (active_period.coefficient - prev.coefficient) * t, 4)
        
        return active_period.coefficient
    
    def _days_from_boundary(self, d: date, period: SeasonPeriod) -> Optional[int]:
        """Días desde el inicio del período (None si no aplica)."""
        y = self.year
        start = date(y, period.start[0], period.start[1])
        end = date(y, period.end[0], period.end[1])
        
        if end < start:  # cruce de año
            if d >= start:
                return (d - start).days
            elif d <= end:
                return (d - (date(y-1, period.start[0], period.start[1]))).days  # approx
            return None
        
        if start <= d <= end:
            return (d - start).days
        return None
    
    def _get_previous_period(self, current: SeasonPeriod, all_periods: List[SeasonPeriod]) -> Optional[SeasonPeriod]:
        """Obtiene el período inmediatamente anterior."""
        idx = -1
        for i, p in enumerate(all_periods):
            if p.code == current.code and p.start == current.start:
                idx = i
                break
        if idx > 0:
            return all_periods[idx - 1]
        return all_periods[-1] if all_periods else None


# ──────────────────────────────────────────────
# ELASTICIDAD SEGMENTADA (Toledo)
# ──────────────────────────────────────────────

# Matriz día × temporada (7 días × 9 temporadas)
ELASTICITY_MATRIX: Dict[str, Dict[str, float]] = {
    "S_BAJA_INV":  {"Mon": -1.8, "Tue": -1.8, "Wed": -1.7, "Thu": -1.6,
                    "Fri": -1.2, "Sat": -1.0, "Sun": -1.4},
    "S_MEDIA_INV": {"Mon": -1.6, "Tue": -1.6, "Wed": -1.5, "Thu": -1.4,
                    "Fri": -1.0, "Sat": -0.8, "Sun": -1.2},
    "S_PRIMAVERA": {"Mon": -1.5, "Tue": -1.5, "Wed": -1.4, "Thu": -1.3,
                    "Fri": -0.7, "Sat": -0.5, "Sun": -1.1},
    "S_SEMANA_SANTA": {"Mon": -0.4, "Tue": -0.3, "Wed": -0.3, "Thu": -0.25,
                       "Fri": -0.2, "Sat": -0.2, "Sun": -0.3},
    "S_CORPUS":   {"Mon": -0.5, "Tue": -0.4, "Wed": -0.4, "Thu": -0.3,
                   "Fri": -0.25, "Sat": -0.25, "Sun": -0.4},
    "S_VERANO":   {"Mon": -1.7, "Tue": -1.8, "Wed": -1.8, "Thu": -1.7,
                   "Fri": -1.3, "Sat": -1.1, "Sun": -1.5},
    "S_OTONO":    {"Mon": -1.4, "Tue": -1.4, "Wed": -1.3, "Thu": -1.2,
                    "Fri": -0.6, "Sat": -0.4, "Sun": -1.0},
    "S_NAVIDAD":  {"Mon": -1.0, "Tue": -1.0, "Wed": -0.9, "Thu": -0.8,
                   "Fri": -0.5, "Sat": -0.4, "Sun": -0.7},
    "S_PUENTE":   {"Mon": -0.3, "Tue": -0.3, "Wed": -0.3, "Thu": -0.3,
                   "Fri": -0.3, "Sat": -0.3, "Sun": -0.3},
}

SEGMENT_ELASTICITIES = {
    "escapista_madrid":      -0.3,
    "cultural_nacional":     -1.2,
    "cultural_internacional": -1.5,
    "religioso_evento":      -0.2,
    "corporate":             -2.0,
}

# Pesos de segmentos por tipo de día (Toledo)
SEGMENT_WEIGHTS: Dict[str, Dict[str, float]] = {
    "weekday": {
        "escapista_madrid":       0.05,
        "cultural_nacional":      0.40,
        "cultural_internacional": 0.30,
        "religioso_evento":       0.15,
        "corporate":              0.10,
    },
    "weekend": {
        "escapista_madrid":       0.55,
        "cultural_nacional":      0.25,
        "cultural_internacional": 0.10,
        "religioso_evento":       0.05,
        "corporate":              0.05,
    },
    "puente": {
        "escapista_madrid":       0.35,
        "cultural_nacional":      0.35,
        "cultural_internacional": 0.10,
        "religioso_evento":       0.15,
        "corporate":              0.05,
    },
    "event": {
        "escapista_madrid":       0.10,
        "cultural_nacional":      0.20,
        "cultural_internacional": 0.15,
        "religioso_evento":       0.50,
        "corporate":              0.05,
    },
}

# Días de la semana en español
DOW_NAMES = {0: "Lun", 1: "Mar", 2: "Mié", 3: "Jue", 4: "Vie", 5: "Sáb", 6: "Dom"}
DOW_SHORT = {0: "Mon", 1: "Tue", 2: "Wed", 3: "Thu", 4: "Fri", 5: "Sat", 6: "Sun"}

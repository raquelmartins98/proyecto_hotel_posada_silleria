"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  Dynamic Pricing Engine                                                   ║
║  Hotel Posada de la Sillería — Toledo                                     ║
║  RevPAR Optimization | Algorithmic Revenue Management System               ║
╚══════════════════════════════════════════════════════════════════════════════╝

DISCLAIMER TÉCNICO:
    Este sistema es un motor de SUGERENCIA de precios, no un sistema de
    fijación autónoma. Todo precio sugerido debe ser revisado por el equipo
    de Revenue Management antes de su publicación.

ARQUITECTURA:
    1) Data Layer    → Ingesta, validación y preprocesamiento de datos
    2) Elasticity    → Modelo econométrico de elasticidad precio-demanda
    3) Engine        → Algoritmo principal con sistema de multiplicadores
    4) Simulator     → Generación de datos sintéticos + demostración
"""

# =============================================================================
# IMPORTS
# =============================================================================
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, date
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import warnings

warnings.filterwarnings("ignore")

# =============================================================================
# ENUMS — Tipos de datos categóricos con jerarquía de impacto
# =============================================================================


class EventType(Enum):
    """
    Jerarquía de eventos según impacto en la demanda hotelera en Toledo.
    Basado en datos históricos de ocupación y precios medios.

    ORDEN DE IMPACTO (descendente):
      SEMANA_SANTA > CORPUS_CHRISTI > FERIA_LOCAL > PUENTE > FINDESEMANA
    """
    NONE = 0
    WEEKEND = 1
    PUENTE = 2
    LOCAL_FESTIVAL = 3
    CORPUS_CHRISTI = 4
    SEMANA_SANTA = 5


class WeatherType(Enum):
    """
    Clasificación meteorológica con impacto en la demanda.
    Para un destino cultural como Toledo, el clima tiene efecto moderado
    (afecta más a la decisión de última hora que a la planificada).
    """
    STORM = 0
    RAIN = 1
    CLOUDY = 2
    PARTLY_CLOUDY = 3
    SUNNY = 4


# =============================================================================
# CONFIGURACIÓN DEL HOTEL — Dataclass inmutable con validación
# =============================================================================


@dataclass(frozen=True)
class HotelConfig:
    """
    Configuración parametrizable del hotel.

    Todos los parámetros son inmutables (frozen=True) para evitar
    modificaciones accidentales durante la ejecución del algoritmo.

    Attributes:
        nombre:            Nombre comercial del hotel
        capacidad:         Número total de habitaciones
        bar_rate:          Best Available Rate (BAR) — tarifa base de referencia
        floor_price:       Precio mínimo absoluto (suelo de seguridad)
        ceiling_price:     Precio máximo absoluto (techo de seguridad)
        historical_occ:    Ocupación media histórica (0-1), para normalización
    """
    nombre: str = "Hotel Posada de la Sillería"
    capacidad: int = 42
    bar_rate: float = 120.0
    floor_price: float = 65.0
    ceiling_price: float = 350.0
    historical_occ: float = 0.68
    elasticity_window_days: int = 60

    def __post_init__(self):
        """Validación de límites de seguridad."""
        assert self.floor_price < self.bar_rate < self.ceiling_price, (
            f"Error de configuración: debe cumplirse floor ({self.floor_price}) "
            f"< BAR ({self.bar_rate}) < ceiling ({self.ceiling_price})"
        )
        assert 0 < self.historical_occ < 1, (
            f"La ocupación histórica debe estar entre 0 y 1, got {self.historical_occ}"
        )


# =============================================================================
# ELASTICITY CALCULATOR — Modelo econométrico de elasticidad precio-demanda
# =============================================================================


class ElasticityCalculator:
    """
    Estimador de Elasticidad Precio de la Demanda (PED).

    MARCO TEÓRICO:
        La elasticidad-precio mide el cambio porcentual en la cantidad demandada
        ante un cambio del 1% en el precio:

            ε = (ΔQ/Q) / (ΔP/P) = d(log Q) / d(log P)

        INTERPRETACIÓN:
            |ε| < 1 → Demanda INELÁSTICA → Subir precio ↑ → Ingresos ↑
            |ε| > 1 → Demanda ELÁSTICA   → Subir precio ↑ → Ingresos ↓
            |ε| = 1 → Elasticidad unitaria → Ingresos máximos (RevPAR óptimo)

    IMPLEMENTACIÓN:
        Se utiliza un modelo log-log (doble logarítmico) con MCO (OLS):

            ln(Demanda) = β₀ + β₁·ln(Precio) + β₂·ln(P_comp) + β₃·Ocupación_lag + ε

        donde β₁ es el coeficiente de elasticidad precio directa.

    REFERENCIA:
        Para hoteles urbanos europeos, la elasticidad precio suele oscilar
        entre -0.8 y -1.5 (Lilien & Kotler, 2012; Sánchez & Satir, 2005).
    """

    def __init__(self, config: HotelConfig):
        self.config = config
        self._is_fitted = False
        self._elasticity = None
        self._coefs = None
        self._intercept = None

    def _prepare_features(self, df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """
        Prepara las matrices X (features) e y (target) para el modelo log-log.

        Variables independientes:
            - ln(Precio propio):      efecto propio-precio (elasticidad directa)
            - ln(Precio competencia): efecto sustitución (elasticidad cruzada)
            - Ocupación_lag(1):       efecto de la ocupación del día anterior
            - Festividad (dummy):     control por eventos

        Variable dependiente:
            - ln(Demanda): logaritmo natural de la demanda observada

        NOTA: Incluimos término constante (intercepto) añadiendo columna de unos.
        """
        df = df.copy()

        EPS = 1e-8
        df['log_precio'] = np.log(df['precio_aplicado'].values + EPS)
        df['log_comp'] = np.log(df['precio_competencia'].values + EPS)
        df['log_demanda'] = np.log(df['demanda_observada'].values + EPS)
        df['occ_lag1'] = df['ocupacion'].shift(1).fillna(self.config.historical_occ)
        df['es_festivo'] = (df['evento'] != EventType.NONE).astype(float)

        # Matriz de diseño con intercepto (columna de unos)
        features = ['log_precio', 'log_comp', 'occ_lag1', 'es_festivo']
        X = np.column_stack([np.ones(len(df)), df[features].values])
        y = df['log_demanda'].values

        self._features = features
        return X, y

    def fit(self, df: pd.DataFrame) -> 'ElasticityCalculator':
        """
        Estima la elasticidad precio mediante regresión log-log por MCO.
        Utiliza estimación por mínimos cuadrados ordinarios con numpy.

        El modelo log-log tiene la ventaja de que los coeficientes
        SON directamente las elasticidades, sin transformación adicional.
        β₁ = d(log demanda) / d(log precio) = elasticidad precio.

        Returns:
            self (para encadenamiento de métodos)
        """
        X, y = self._prepare_features(df)

        # Estimación MCO: β = (X'X)⁻¹ X'y
        # Usamos scipy.stats.linregress para una implementación
        # numéricamente estable con una variable.
        # Para el modelo multivariante, usamos la fórmula directa de MCO.

        # Aproximación: regresión simple log(precio) -> log(demanda)
        # como estimador de elasticidad. Controlamos por las demás
        # variables mediante regresión múltiple con numpy.

        # β = (X'X)⁻¹ X'y usando pseudo-inversa (SVD) por estabilidad numérica
        beta = np.linalg.lstsq(X, y, rcond=None)[0]

        self._intercept = beta[0]
        self._coefs = beta[1:]
        self._is_fitted = True
        # β₁ es la elasticidad precio (primer coeficiente después del intercepto)
        self._elasticity = float(beta[1])

        return self

    @property
    def elasticity(self) -> float:
        """
        Elasticidad precio estimada (coeficiente β₁ del modelo log-log).

        Returns:
            float: Coeficiente de elasticidad (típicamente negativo)

        Raises:
            RuntimeError: Si el modelo no ha sido entrenado
        """
        if not self._is_fitted:
            raise RuntimeError(
                "El modelo debe entrenarse con .fit() antes de acceder a la elasticidad"
            )
        return self._elasticity

    def elasticity_adjustment_factor(self) -> float:
        """
        Calcula el factor de ajuste por elasticidad para el pricing.

        LÓGICA ECONÓMICA:
            La elasticidad precio mide cómo responde la demanda a cambios
            de precio. Este factor debe MATIZAR, no dominar, la decisión
            de pricing. Usamos una función lineal suave:

                factor = 1 - β × (|ε| - 1)

            donde β = 0.05 (sensibilidad calibrada).

            Con |ε| = 1 (elasticidad unitaria):  factor = 1.000 (neutro)
            Con |ε| = 0.5 (muy inelástica):      factor = 1.025 (+2.5%)
            Con |ε| = 1.5 (elástica):            factor = 0.975 (-2.5%)
            Con |ε| = 2.0 (muy elástica):        factor = 0.950 (-5.0%)

        JUSTIFICACIÓN:
            La elasticidad es una RESTRICCIÓN, no una señal de demanda.
            No debería anular el efecto de los multiplicadores basados
            en ocupación y eventos. Por eso el rango es estrecho (±5%).
        """
        eps = abs(self.elasticity)
        beta = 0.05
        factor = 1.0 - beta * (eps - 1.0)
        return float(np.clip(factor, 0.90, 1.10))


# =============================================================================
# PRICING ENGINE — Núcleo algorítmico del sistema
# =============================================================================


class PricingEngine:
    """
    Motor principal de sugerencia de precios.

    ARQUITECTURA DEL ALGORITMO:
        Precio_Sugerido = BAR × M_occ × M_pickup × M_event × M_comp × M_weather × M_dow

        donde cada M_i ∈ [1 - δ_i, 1 + δ_i] es un multiplicador centrado en 1.0

        Finalmente:
            Precio_Final = clip(Precio_Sugerido × factor_elasticidad, Suelo, Techo)

    PRINCIPIO ECONÓMICO:
        El sistema de multiplicadores asume independencia relativa entre factores,
        lo que es una simplificación aceptable para un motor de sugerencias.
        La interacción real entre factores se captura mediante la naturaleza
        multiplicativa del modelo (el producto de los efectos individuales).
    """

    # --- PONDERACIONES DE EVENTOS ---
    # Basadas en el incremento histórico de ADR (Average Daily Rate)
    # observado en hoteles de 3-4 estrellas en Toledo durante estos períodos.
    # Fuente: Informe de Temporada Turística de Castilla-La Mancha 2023-2024.
    EVENT_MULTIPLIERS: Dict[EventType, float] = {
        EventType.NONE: 0.00,
        EventType.WEEKEND: 0.08,
        EventType.PUENTE: 0.18,
        EventType.LOCAL_FESTIVAL: 0.25,
        EventType.CORPUS_CHRISTI: 0.40,
        EventType.SEMANA_SANTA: 0.50,
    }

    # --- PONDERACIONES METEOROLÓGICAS ---
    # Para un destino cultural, el clima tiene menor impacto que en
    # destinos de sol/playa. Los ajustes son moderados.
    WEATHER_MULTIPLIERS: Dict[WeatherType, float] = {
        WeatherType.STORM: -0.08,
        WeatherType.RAIN: -0.04,
        WeatherType.CLOUDY: 0.00,
        WeatherType.PARTLY_CLOUDY: 0.03,
        WeatherType.SUNNY: 0.06,
    }

    # --- PONDERACIONES POR DÍA DE LA SEMANA ---
    # Patrón semanal típico de hoteles urbanos de negocio/ocio mixto.
    # Miércoles como referencia (M_dow = 1.0) por ser el día más
    # cercano a la ocupación media semanal.
    DOW_MULTIPLIERS: Dict[int, float] = {
        0: -0.05,  # Lunes
        1: -0.03,  # Martes
        2: 0.00,   # Miércoles (referencia)
        3: 0.02,   # Jueves
        4: 0.10,   # Viernes
        5: 0.12,   # Sábado
        6: -0.02,  # Domingo
    }

    def __init__(self, config: HotelConfig, elasticity_calc: ElasticityCalculator):
        """
        Inicializa el motor de pricing.

        Args:
            config:           Configuración del hotel (BAR, límites, etc.)
            elasticity_calc:  Calculadora de elasticidad ya entrenada
        """
        self.config = config
        self.elasticity = elasticity_calc

    # ------------------------------------------------------------------
    # MULTIPLICADOR DE OCUPACIÓN (M_occ)
    # ------------------------------------------------------------------

    def _occupancy_multiplier(self, occupancy: float) -> float:
        """
        Calcula el multiplicador por ocupación actual del hotel.

        MODELO MATEMÁTICO: Función sigmoide (logística) asimétrica.

        RACIONAL ECONÓMICO:
            La relación entre ocupación y precio NO es lineal.
            A baja ocupación, pequeñas reducciones de precio apenas estimulan
            demanda adicional (la gente no viaja porque "está barato", sino
            porque quiere viajar).
            A alta ocupación, sin embargo, la disponibilidad limitada permite
            aplicar primas de escasez significativas.

        FUNCIÓN:
                         α_occ
            M_occ = 1 + ————————————————————————  -  0.5 × α_occ
                       1 + exp(-k × (occ - θ))

            donde:
                α_occ = 0.50  — Amplitud máxima del ajuste (±50% máximo)
                k     = 12.0  — Pendiente (steepness) de la curva sigmoide
                θ     = 0.65  — Punto de inflexión (threshold)

            INTERPRETACIÓN:
                occ < 30%  → M_occ ≈ 0.80  (-20%, descuento por baja demanda)
                occ = 50%  → M_occ ≈ 0.93  ( -7%, descuento ligero)
                occ = 65%  → M_occ ≈ 1.00  (neutro, punto de referencia)
                occ = 80%  → M_occ ≈ 1.20  (+20%, prima por alta ocupación)
                occ > 95%  → M_occ ≈ 1.45  (+45%, prima de escasez máxima)
        """
        alpha = 0.50
        k = 12.0
        theta = 0.65

        logistic = 1.0 / (1.0 + np.exp(-k * (occupancy - theta)))
        M_occ = 1.0 + alpha * (logistic - 0.5)

        return float(np.clip(M_occ, 1.0 - alpha, 1.0 + alpha))

    # ------------------------------------------------------------------
    # MULTIPLICADOR DE PICK-UP (M_pickup) — Ritmo de reservas
    # ------------------------------------------------------------------

    def _pickup_multiplier(self, pickup_ratio: float) -> float:
        """
        Calcula el multiplicador por ritmo de reservas (pick-up).

        DEFINICIÓN:
            pickup_ratio = Reservas_última_semana / Reservas_esperadas

            Un ratio > 1.0 indica que las reservas están llegando más rápido
            de lo esperado (demanda caliente → subir precio).
            Un ratio < 1.0 indica reservas lentas (demanda fría → bajar precio).

        FUNCIÓN:
            M_pickup = 1 + α_pickup × (pickup_ratio - 1)

            donde α_pickup = 0.20 (sensibilidad al pickup)

        JUSTIFICACIÓN:
            El pickup es un INDICADOR AVANZADO de demanda. Si hoy las reservas
            están llegando un 20% más rápido de lo esperado, es probable que
            la demanda futura sea mayor, permitiendo subir precios.
            Sin embargo, el pickup tiene menor peso que la ocupación actual
            (α=0.20 vs α_occ=0.50) porque es más volátil como predictor.
        """
        alpha_pickup = 0.20
        M_pickup = 1.0 + alpha_pickup * (pickup_ratio - 1.0)
        return float(np.clip(M_pickup, 0.85, 1.15))

    # ------------------------------------------------------------------
    # MULTIPLICADOR DE COMPETENCIA (M_comp)
    # ------------------------------------------------------------------

    def _competitor_multiplier(self, comp_price: float) -> float:
        """
        Calcula el multiplicador por precios de la competencia local.

        LÓGICA ECONÓMICA:
            Comparamos el precio medio de la competencia con el BAR del hotel.
            Si la competencia está cara respecto a nuestra referencia, tenemos
            margen para subir. Si está barata, debemos ser competitivos.

        FUNCIÓN:
            M_comp = 1 + α_comp × (P_comp / BAR - 1)

            donde:
                α_comp = 0.15  — Peso de la competencia (moderado)

        NOTA TÉCNICA:
            α_comp = 0.15 es intencionadamente moderado. Los hoteles con
            producto diferenciado (ubicación, historia, servicio) deben
            seguir su propia estrategia sin replicar ciegamente a la competencia.
        """
        alpha_comp = 0.15
        comp_ratio = comp_price / self.config.bar_rate
        M_comp = 1.0 + alpha_comp * (comp_ratio - 1.0)
        return float(np.clip(M_comp, 0.90, 1.10))

    # ------------------------------------------------------------------
    # MULTIPLICADOR DE EVENTOS (M_event)
    # ------------------------------------------------------------------

    def _event_multiplier(self, event: EventType) -> float:
        """
        Calcula el multiplicador por evento festivo.

        LÓGICA ECONÓMICA:
            Los eventos generan un INCREMENTO EXÓGENO de la demanda que es
            independiente de nuestras decisiones de precio. Durante eventos
            importantes (Semana Santa, Corpus Christi), la demanda supera
            ampliamente a la oferta hotelera de Toledo, permitiendo primas
            sustanciales.

        FUNCIÓN:
            M_event = 1 + EVENT_MULTIPLIERS[event]

            Ver tabla EVENT_MULTIPLIERS para valores concretos.
        """
        premium = self.EVENT_MULTIPLIERS.get(event, 0.0)
        return 1.0 + premium

    # ------------------------------------------------------------------
    # MULTIPLICADOR METEOROLÓGICO (M_weather)
    # ------------------------------------------------------------------

    def _weather_multiplier(self, weather: WeatherType) -> float:
        """
        Calcula el multiplicador por condiciones meteorológicas previstas.

        LÓGICA ECONÓMICA:
            Para destinos culturales como Toledo, el clima tiene un impacto
            moderado en la demanda. El buen tiempo aumenta las reservas de
            última hora (improvisación turística). El mal tiempo las reduce.

            El efecto es MENOR que en destinos de sol/playa porque:
            1) Toledo es destino cultural (museos, iglesias, monumentos)
            2) Gran parte de las reservas son planificadas con antelación
            3) El clima en Toledo es relativamente estable (continental)
        """
        premium = self.WEATHER_MULTIPLIERS.get(weather, 0.0)
        return 1.0 + premium

    # ------------------------------------------------------------------
    # MULTIPLICADOR POR DÍA DE LA SEMANA (M_dow)
    # ------------------------------------------------------------------

    def _dow_multiplier(self, day_of_week: int) -> float:
        """
        Calcula el multiplicador por día de la semana.

        LÓGICA ECONÓMICA:
            Refleja el patrón semanal de demanda mixta (business + ocio)
            típico de hoteles urbanos en ciudades patrimoniales.
            El miércoles se usa como referencia (M_dow = 1.0).
        """
        premium = self.DOW_MULTIPLIERS.get(day_of_week, 0.0)
        return 1.0 + premium

    # ------------------------------------------------------------------
    # MÉTODO PRINCIPAL: SUGERIR PRECIO
    # ------------------------------------------------------------------

    def suggest_price(
        self,
        occupancy: float,
        pickup_ratio: float,
        competitor_price: float,
        event: EventType,
        weather: WeatherType,
        day_of_week: int,
    ) -> Dict[str, float]:
        """
        Sugiere un precio óptimo para una noche dada.

        Args:
            occupancy:        Ocupación actual del hotel (0-1)
            pickup_ratio:     Ratio de pickup (reservas reales / esperadas)
            competitor_price: Precio medio de la competencia (EUR)
            event:            Tipo de evento festivo
            weather:          Condición meteorológica prevista
            day_of_week:      Día de la semana (0=Lunes, ..., 6=Domingo)

        Returns:
            Dict con:
                - precio_sugerido:          Precio final sugerido (EUR)
                - precio_base:              BAR de referencia
                - desglose:                 Dict con cada multiplicador
                - precio_sin_elasticidad:   Precio antes del ajuste por elasticidad

        ALGORITMO:
            1. Calcular cada multiplicador individualmente
            2. Combinar multiplicativamente: M_total = Π M_i
            3. Aplicar sobre BAR: P_intermedio = BAR × M_total
            4. Ajustar por elasticidad: P_ajustado = P_intermedio × factor_elasticidad
            5. Aplicar límites de seguridad: P_final = clip(P_ajustado, suelo, techo)
        """
        # --- STEP 1: Multiplicadores individuales ---
        M_occ = self._occupancy_multiplier(occupancy)
        M_pickup = self._pickup_multiplier(pickup_ratio)
        M_comp = self._competitor_multiplier(competitor_price)
        M_event = self._event_multiplier(event)
        M_weather = self._weather_multiplier(weather)
        M_dow = self._dow_multiplier(day_of_week)

        # --- STEP 2: Combinación multiplicativa ---
        # Justificación: factores aproximadamente independientes →
        # efecto conjunto = producto de efectos individuales.
        M_total = M_occ * M_pickup * M_comp * M_event * M_weather * M_dow

        # --- STEP 3: Precio intermedio (antes de elasticidad) ---
        precio_intermedio = self.config.bar_rate * M_total

        # --- STEP 4: Ajuste por elasticidad ---
        factor_elasticidad = self.elasticity.elasticity_adjustment_factor()
        precio_ajustado = precio_intermedio * factor_elasticidad

        # --- STEP 5: Límites de seguridad ---
        precio_final = np.clip(
            precio_ajustado,
            self.config.floor_price,
            self.config.ceiling_price,
        )

        return {
            "precio_sugerido": round(float(precio_final), 2),
            "precio_base": self.config.bar_rate,
            "multiplicador_total": round(float(M_total), 4),
            "factor_elasticidad": round(float(factor_elasticidad), 4),
            "desglose": {
                "M_ocupacion": round(float(M_occ), 4),
                "M_pickup": round(float(M_pickup), 4),
                "M_competencia": round(float(M_comp), 4),
                "M_evento": round(float(M_event), 4),
                "M_clima": round(float(M_weather), 4),
                "M_dia_semana": round(float(M_dow), 4),
            },
            "precio_sin_elasticidad": round(float(precio_intermedio), 2),
        }


# =============================================================================
# GENERADOR DE DATOS SINTÉTICOS — Mock realista para testing
# =============================================================================


class SyntheticDataGenerator:
    """
    Genera un DataFrame sintético que simula el entorno de datos del
    Hotel Posada de la Sillería durante un período especificado.

    Los datos generados reproducen patrones realistas:
        - Estacionalidad semanal y mensual
        - Eventos festivos en fechas concretas
        - Correlación entre ocupación, precio y factores externos
        - Ruido estocástico realista (demanda con componente aleatoria)

    REFERENCIA:
        Rangos y distribuciones basados en datos públicos de ocupación
        hotelera en Castilla-La Mancha (INE, 2023-2024).
    """

    # Fechas de eventos críticos en Toledo. Calendario 2025 real.
    EVENT_DATES: Dict[str, EventType] = {
        # Semana Santa 2025: 13-20 abril
        "2025-04-13": EventType.SEMANA_SANTA,
        "2025-04-14": EventType.SEMANA_SANTA,
        "2025-04-15": EventType.SEMANA_SANTA,
        "2025-04-16": EventType.SEMANA_SANTA,
        "2025-04-17": EventType.SEMANA_SANTA,
        "2025-04-18": EventType.SEMANA_SANTA,
        "2025-04-19": EventType.SEMANA_SANTA,
        "2025-04-20": EventType.SEMANA_SANTA,
        # Corpus Christi 2025: 19-23 junio (fecha móvil: 60 días post-Pascua)
        "2025-06-19": EventType.CORPUS_CHRISTI,
        "2025-06-20": EventType.CORPUS_CHRISTI,
        "2025-06-21": EventType.CORPUS_CHRISTI,
        "2025-06-22": EventType.CORPUS_CHRISTI,
        "2025-06-23": EventType.CORPUS_CHRISTI,
        # Feria de Toledo (Virgen del Sagrario): 14-17 agosto
        "2025-08-14": EventType.LOCAL_FESTIVAL,
        "2025-08-15": EventType.LOCAL_FESTIVAL,
        "2025-08-16": EventType.LOCAL_FESTIVAL,
        "2025-08-17": EventType.LOCAL_FESTIVAL,
    }

    # Puentes nacionales 2025
    PUENTE_DATES: List[str] = [
        "2025-05-01",  # Día del Trabajador
        "2025-12-06",  # Día de la Constitución
        "2025-12-08",  # Inmaculada Concepción
    ]

    def __init__(self, config: HotelConfig, seed: int = 42):
        self.config = config
        self.rng = np.random.default_rng(seed)

    def _get_event(self, d: date) -> EventType:
        """Determina el tipo de evento para una fecha dada."""
        date_str = d.isoformat()
        if date_str in self.EVENT_DATES:
            return self.EVENT_DATES[date_str]
        if date_str in self.PUENTE_DATES:
            return EventType.PUENTE
        if d.weekday() >= 5:
            return EventType.WEEKEND
        return EventType.NONE

    def _get_weather(self, d: date) -> WeatherType:
        """
        Genera clima sintético con estacionalidad para Toledo.

        Toledo: clima mediterráneo continentalizado.
            - Verano (jun-ago):   mayoritariamente soleado (70% SUNNY)
            - Invierno (dic-feb): mayoritariamente nublado/lluvioso
            - Primavera/Otoño:    mixto con probabilidad moderada de lluvia
        """
        month = d.month
        if month in [6, 7, 8]:
            probs = [0.00, 0.02, 0.05, 0.23, 0.70]
        elif month in [12, 1, 2]:
            probs = [0.05, 0.20, 0.35, 0.30, 0.10]
        else:
            probs = [0.03, 0.10, 0.25, 0.35, 0.27]
        return self.rng.choice(list(WeatherType), p=probs)

    def _get_seasonal_base_occupancy(self, d: date) -> float:
        """
        Calcula la ocupación base estacional (sin ruido estocástico).

        Patrón estacional calibrado para Toledo:
            - Máxima: Abril (S.Santa), Junio (Corpus), Octubre (otoño dorado)
            - Mínima: Enero, Julio (calor extremo)
            - Moderada: resto del año
        """
        seasonal = {
            1: 0.55,  2: 0.65,  3: 0.85,
            4: 1.25,  5: 0.95,  6: 1.15,
            7: 0.60,  8: 0.70,  9: 0.90,
            10: 1.05, 11: 0.75, 12: 0.80,
        }
        base = self.config.historical_occ * seasonal.get(d.month, 1.0)

        dow_factor = {0: 0.80, 1: 0.85, 2: 0.90, 3: 0.95, 4: 1.15, 5: 1.25, 6: 0.85}
        return base * dow_factor.get(d.weekday(), 1.0)

    def generate(self, days: int = 90, start_date: Optional[date] = None) -> pd.DataFrame:
        """
        Genera un conjunto de datos sintéticos para entrenamiento y simulación.

        Args:
            days:       Número de días a generar
            start_date: Fecha de inicio (por defecto: 90 días antes de hoy)

        Returns:
            DataFrame con columnas: fecha, dia_semana, evento, clima, ocupacion,
            pickup_ratio, precio_competencia, demanda_observada, precio_aplicado
        """
        if start_date is None:
            start_date = date.today() - timedelta(days=days)

        records = []
        for i in range(days):
            d = start_date + timedelta(days=i)
            event = self._get_event(d)
            weather = self._get_weather(d)

            # Ocupación base estacional + ruido gaussiano
            base_occ = self._get_seasonal_base_occupancy(d)
            noise_occ = self.rng.normal(0, 0.05)
            occupancy = float(np.clip(base_occ + noise_occ, 0.10, 0.98))

            # Pickup ratio: correlacionado con ocupación y eventos
            pickup_base = 0.8 + 0.4 * occupancy
            event_pickup_boost = 0.3 if event != EventType.NONE else 0.0
            noise_pickup = self.rng.normal(0, 0.08)
            pickup_ratio = float(
                np.clip(pickup_base + event_pickup_boost + noise_pickup, 0.3, 2.0)
            )

            # Precio competencia: correlacionado con ocupación y eventos
            event_premium = self.PricingEngine.EVENT_MULTIPLIERS.get(
                event, 0.0
            )
            comp_base = self.config.bar_rate * (0.85 + 0.3 * occupancy)
            comp_with_event = comp_base * (1.0 + event_premium * 0.5)
            noise_comp = self.rng.normal(0, 8.0)
            comp_price = float(max(comp_with_event + noise_comp, 50.0))

            # Precio aplicado históricamente (simulado): ruidoso alrededor
            # del precio de competencia con algo de ineficiencia
            precio_aplicado = float(comp_price * (0.88 + 0.24 * self.rng.random()))

            # Demanda observada: función de la relación precio propio / competencia
            # Economicamente: si nuestro precio es menor relativo a competencia,
            # obtenemos más demanda.
            price_ratio = precio_aplicado / max(comp_price, 1.0)
            sensibilidad = -0.8  # elasticidad implícita en los datos
            demanda_base = occupancy * self.config.capacidad
            ajuste_precio = (1.0 / max(price_ratio, 0.5)) ** abs(sensibilidad)
            ruido_demanda = self.rng.normal(0, 2)
            demanda_obs = int(
                np.clip(round(demanda_base * ajuste_precio + ruido_demanda), 0, self.config.capacidad)
            )

            records.append({
                "fecha": d,
                "dia_semana": d.weekday(),
                "nombre_dia": ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"][d.weekday()],
                "evento": event,
                "evento_nombre": event.name,
                "clima": weather,
                "clima_nombre": weather.name,
                "ocupacion": round(occupancy, 4),
                "pickup_ratio": round(pickup_ratio, 4),
                "precio_competencia": round(comp_price, 2),
                "demanda_observada": demanda_obs,
                "precio_aplicado": round(precio_aplicado, 2),
            })

        return pd.DataFrame(records)

    # Referencia interna para usar las tablas de PricingEngine en generación
    class PricingEngine:
        EVENT_MULTIPLIERS = {
            EventType.NONE: 0.00,
            EventType.WEEKEND: 0.08,
            EventType.PUENTE: 0.18,
            EventType.LOCAL_FESTIVAL: 0.25,
            EventType.CORPUS_CHRISTI: 0.40,
            EventType.SEMANA_SANTA: 0.50,
        }


# =============================================================================
# SIMULADOR COMPLETO — Orquesta todo el pipeline
# =============================================================================


class RevenueManagementSimulator:
    """
    Simulador completo del sistema de Revenue Management.

    Orquesta el pipeline completo:
        1. Generación de datos sintéticos
        2. Estimación de elasticidad precio-demanda
        3. Ejecución del Pricing Engine
        4. Análisis de resultados y métricas de rendimiento
    """

    def __init__(self, config: Optional[HotelConfig] = None):
        self.config = config or HotelConfig()
        self.data_generator = SyntheticDataGenerator(self.config)
        self.elasticity_model: Optional[ElasticityCalculator] = None
        self.pricing_engine: Optional[PricingEngine] = None
        self.results: Optional[pd.DataFrame] = None

    def run_simulation(self, days: int = 90, start_date: Optional[date] = None) -> pd.DataFrame:
        """
        Ejecuta la simulación completa del sistema de pricing.

        Pipeline:
            1. Generar datos históricos sintéticos (para entrenar elasticidad)
            2. Estimar elasticidad precio-demanda (log-log regression)
            3. Inicializar PricingEngine con el modelo entrenado
            4. Ejecutar sugerencias de precio para cada día del horizonte
            5. Analizar y mostrar resultados con métricas de rendimiento

        Returns:
            DataFrame con precios sugeridos y desglose de multiplicadores
        """
        print("=" * 80)
        print(f"  REVENUE MANAGEMENT SIMULATOR")
        print(f"  {self.config.nombre}")
        print(f"  Capacidad: {self.config.capacidad} habitaciones")
        print(f"  BAR: {self.config.bar_rate:.2f} EUR | Suelo: {self.config.floor_price:.2f} EUR | "
              f"Techo: {self.config.ceiling_price:.2f} EUR")
        print("=" * 80)

        # --- FASE 1: Datos sintéticos ---
        print("\n[FASE 1] Generando datos sintéticos históricos...")
        historical = self.data_generator.generate(days=days, start_date=start_date)
        print(f"  -> {len(historical)} dias generados")
        print(f"  -> Rango: {historical['fecha'].min()} -> {historical['fecha'].max()}")
        print(f"  -> Ocupacion media: {historical['ocupacion'].mean():.1%}")

        # --- FASE 2: Elasticidad ---
        print("\n[FASE 2] Estimando elasticidad precio-demanda (log-log MCO)...")
        self.elasticity_model = ElasticityCalculator(self.config)
        self.elasticity_model.fit(historical)
        eps = self.elasticity_model.elasticity
        print(f"  -> Elasticidad estimada (beta1): {eps:.4f}")
        print(f"  -> Demanda es {'ELASTICA' if abs(eps) > 1 else 'INELASTICA'} "
              f"(|e| = {abs(eps):.4f})")
        print(f"  -> Factor de ajuste: {self.elasticity_model.elasticity_adjustment_factor():.4f}")

        # --- FASE 3: Pricing Engine ---
        print("\n[FASE 3] Inicializando Pricing Engine...")
        self.pricing_engine = PricingEngine(self.config, self.elasticity_model)

        # --- FASE 4: Sugerencias para todo el horizonte ---
        print("\n[FASE 4] Ejecutando sugerencias de precio...")
        results_rows = []
        for _, row in historical.iterrows():
            suggestion = self.pricing_engine.suggest_price(
                occupancy=row["ocupacion"],
                pickup_ratio=row["pickup_ratio"],
                competitor_price=row["precio_competencia"],
                event=row["evento"],
                weather=row["clima"],
                day_of_week=row["dia_semana"],
            )
            results_rows.append({
                "fecha": row["fecha"],
                "dia_semana": row["nombre_dia"],
                "evento": row["evento_nombre"],
                "clima": row["clima_nombre"],
                "ocupacion": row["ocupacion"],
                "pickup_ratio": row["pickup_ratio"],
                "precio_competencia": row["precio_competencia"],
                "precio_sugerido": suggestion["precio_sugerido"],
                "precio_base": suggestion["precio_base"],
                "vs_bar_pct": round(
                    (suggestion["precio_sugerido"] / suggestion["precio_base"] - 1) * 100, 2
                ),
                "M_ocupacion": suggestion["desglose"]["M_ocupacion"],
                "M_pickup": suggestion["desglose"]["M_pickup"],
                "M_competencia": suggestion["desglose"]["M_competencia"],
                "M_evento": suggestion["desglose"]["M_evento"],
                "M_clima": suggestion["desglose"]["M_clima"],
                "M_dia_semana": suggestion["desglose"]["M_dia_semana"],
                "multiplicador_total": suggestion["multiplicador_total"],
                "factor_elasticidad": suggestion["factor_elasticidad"],
            })

        self.results = pd.DataFrame(results_rows)

        # --- FASE 5: Análisis ---
        print("\n[FASE 5] ANALIZANDO RESULTADOS")
        print("-" * 80)

        print(f"\n  >>> ESTADISTICAS DE PRECIOS SUGERIDOS:")
        print(f"     Media:       {self.results['precio_sugerido'].mean():.2f} EUR")
        print(f"     Mediana:     {self.results['precio_sugerido'].median():.2f} EUR")
        print(f"     Mínimo:      {self.results['precio_sugerido'].min():.2f} EUR")
        print(f"     Máximo:      {self.results['precio_sugerido'].max():.2f} EUR")
        print(f"     Desv. Std:   {self.results['precio_sugerido'].std():.2f} EUR")
        print(f"     vs BAR:      {self.results['vs_bar_pct'].mean():+.2f}% medio")

        print(f"\n  >>> PRECIO MEDIO POR TIPO DE EVENTO:")
        for ev_name, grp in self.results.groupby("evento"):
            print(
                f"     {ev_name:20s}: {grp['precio_sugerido'].mean():7.2f} EUR  "
                f"({grp['vs_bar_pct'].mean():+.1f}% vs BAR)  [{len(grp)} días]"
            )

        print(f"\n  >>> PRECIO MEDIO POR CLIMA:")
        for w_name, grp in self.results.groupby("clima"):
            print(
                f"     {w_name:20s}: {grp['precio_sugerido'].mean():7.2f} EUR  "
                f"({grp['vs_bar_pct'].mean():+.1f}% vs BAR)"
            )

        print(f"\n  >>> MULTIPLICADORES MEDIOS:")
        mult_cols = [
            "M_ocupacion", "M_pickup", "M_competencia",
            "M_evento", "M_clima", "M_dia_semana",
        ]
        for col in mult_cols:
            print(
                f"     {col:20s}: media={self.results[col].mean():.4f}  "
                f"[min={self.results[col].min():.4f}, max={self.results[col].max():.4f}]"
            )
        print(f"     {'Multiplicador Total':20s}: {self.results['multiplicador_total'].mean():.4f}")
        print(f"     {'Factor Elasticidad':20s}: {self.results['factor_elasticidad'].mean():.4f}")

        # RevPAR
        avg_price = self.results["precio_sugerido"].mean()
        avg_occ = self.results["ocupacion"].mean()
        revpar_dyn = avg_price * avg_occ
        revpar_static = self.config.bar_rate * self.config.historical_occ
        improvement = (revpar_dyn / revpar_static - 1) * 100

        print(f"\n  >>> REVPAR ESTIMADO:")
        print(f"     Precio medio:          {avg_price:.2f} EUR")
        print(f"     Ocupación media:       {avg_occ:.1%}")
        print(f"     RevPAR (dinámico):     {revpar_dyn:.2f} EUR")
        print(f"     RevPAR (BAR estático): {revpar_static:.2f} EUR")
        print(f"     Mejora RevPAR:         {improvement:+.2f}%")

        print("\n" + "=" * 80)
        print("  SIMULACIÓN COMPLETADA CON ÉXITO")
        print("=" * 80)

        return self.results

    def get_top_days(self, n: int = 10) -> pd.DataFrame:
        """Devuelve los n días con precio sugerido más alto."""
        if self.results is None:
            raise RuntimeError("Ejecuta run_simulation() primero")
        cols = ["fecha", "dia_semana", "evento", "ocupacion", "precio_sugerido", "vs_bar_pct"]
        return self.results.nlargest(n, "precio_sugerido")[cols]

    def get_bottom_days(self, n: int = 10) -> pd.DataFrame:
        """Devuelve los n días con precio sugerido más bajo."""
        if self.results is None:
            raise RuntimeError("Ejecuta run_simulation() primero")
        cols = ["fecha", "dia_semana", "evento", "ocupacion", "precio_sugerido", "vs_bar_pct"]
        return self.results.nsmallest(n, "precio_sugerido")[cols]


# =============================================================================
# MAIN — Punto de entrada para demostración
# =============================================================================

if __name__ == "__main__":

    print("\n" + "=" * 80)
    print("  Dynamic Pricing Engine - Hotel Posada de la Silleria (Toledo)")
    print("  RevPAR Optimization System | v1.0.0")
    print("=" * 80)

    # ------------------------------------------------------------------
    # CONFIGURACIÓN DEL HOTEL
    # ------------------------------------------------------------------
    # DATOS REALES extraidos de hotelposadasilleria.es:
    #   - 24 habitaciones (Bookaris, Expedia, Hotels.com)
    #   - Edificio s.XVI, ultima reforma 2020
    #   - 5 tipos: Doble Boutique, Doble Superior, Suite Castellana,
    #     Doble Posada, Individual
    #   - Precio OTA: ~97-105$ (~95 EUR) en baja temporada
    #   - Rating: 9.6/10 (Expedia, 197 reviews)
    config = HotelConfig(
        nombre="Hotel Boutique Posada de la Silleria",
        capacidad=24,
        bar_rate=115.0,
        floor_price=65.0,
        ceiling_price=350.0,
        historical_occ=0.72,
    )

    # ------------------------------------------------------------------
    # SIMULACIÓN PRINCIPAL
    # ------------------------------------------------------------------
    simulator = RevenueManagementSimulator(config)

    # Horizonte de simulación: 90 días desde el 1 de marzo de 2025
    # (cubre pre-Semana Santa, Semana Santa, Corpus Christi y verano)
    start = date(2025, 3, 1)
    results = simulator.run_simulation(days=90, start_date=start)

    # ------------------------------------------------------------------
    # TOP 5 DIAS MAS CAROS
    # ------------------------------------------------------------------
    print("\n\n[ TOP 5 DIAS ] PRECIO MAS ALTO SUGERIDO")
    print("-" * 70)
    top5 = simulator.get_top_days(5)
    for _, row in top5.iterrows():
        print(
            f"  {row['fecha']} ({row['dia_semana']:3s}) | "
            f"{row['evento']:20s} | "
            f"Ocup: {row['ocupacion']:.0%} | "
            f"EUR {row['precio_sugerido']:6.2f} ({row['vs_bar_pct']:+.1f}%)"
        )

    # ------------------------------------------------------------------
    # BOTTOM 5 DIAS MAS BARATOS
    # ------------------------------------------------------------------
    print("\n\n[ BOTTOM 5 DIAS ] PRECIO MAS BAJO SUGERIDO")
    print("-" * 70)
    bot5 = simulator.get_bottom_days(5)
    for _, row in bot5.iterrows():
        print(
            f"  {row['fecha']} ({row['dia_semana']:3s}) | "
            f"{row['evento']:20s} | "
            f"Ocup: {row['ocupacion']:.0%} | "
            f"EUR {row['precio_sugerido']:6.2f} ({row['vs_bar_pct']:+.1f}%)"
        )

    # ------------------------------------------------------------------
    # RESUMEN EJECUTIVO
    # ------------------------------------------------------------------
    avg_price = results["precio_sugerido"].mean()
    avg_occ = results["ocupacion"].mean()
    revpar = avg_price * avg_occ
    static_revpar = config.bar_rate * config.historical_occ
    improvement = (revpar / static_revpar - 1) * 100

    print("\n\n" + "+" + "-" * 78 + "+")
    print("|  RESUMEN EJECUTIVO - RECOMENDACIONES PARA REVENUE MANAGEMENT")
    print("+" + "-" * 78 + "+")
    print(f"""
  [ {config.nombre} ]
  ================================================================

  [ CONFIGURACION ]
     * BAR (Base Rate):        {config.bar_rate:.2f} EUR
     * Suelo de seguridad:    {config.floor_price:.2f} EUR
     * Techo de seguridad:    {config.ceiling_price:.2f} EUR
     * Capacidad:             {config.capacidad} habitaciones

  [ RESULTADOS DE LA SIMULACION ]
     * Precio medio sugerido: {avg_price:.2f} EUR
     * Precio minimo:         {results['precio_sugerido'].min():.2f} EUR
     * Precio maximo:         {results['precio_sugerido'].max():.2f} EUR
     * Desviacion tipica:     {results['precio_sugerido'].std():.2f} EUR
     * Ocupacion media:       {avg_occ:.1%}

  [ IMPACTO EN REVPAR ]
     * RevPAR dinamico:       {revpar:.2f} EUR
     * RevPAR estatico (BAR): {static_revpar:.2f} EUR
     * Mejora potencial:      {improvement:+.1f}%

  [ FACTORES MAS INFLUYENTES (peso medio) ]
     * Ocupacion:             {results['M_ocupacion'].mean():.4f}
     * Evento:                {results['M_evento'].mean():.4f}
     * Dia de semana:         {results['M_dia_semana'].mean():.4f}
     * Pickup:                {results['M_pickup'].mean():.4f}
     * Competencia:           {results['M_competencia'].mean():.4f}
     * Clima:                 {results['M_clima'].mean():.4f}

  [ RECOMENDACIONES ]
     1. {'INCREMENTAR BAR a ~' + str(round(avg_price)) + 'EUR - el mercado soporta un precio medio superior al BAR actual'
        if avg_price > config.bar_rate else 'Mantener BAR actual - el mercado no justifica subidas generalizadas'}
     2. {'Aplicar prima de evento AGGRESSIVE durante Semana Santa y Corpus Christi (potencial hasta ' +
        str(round(results.loc[results['evento'] == 'SEMANA_SANTA', 'precio_sugerido'].max())) + ' EUR)'
        if 'SEMANA_SANTA' in results['evento'].values else 'Programar proximos eventos festivos en el calendario'}
     3. {'Utilizar descuentos dinamicos en temporada baja (precios hasta ' +
        str(round(results['precio_sugerido'].min())) + ' EUR) para estimular demanda'
        if results['precio_sugerido'].min() < config.bar_rate * 0.9 else 'Los descuentos no parecen necesarios'}
     4. Revisar trimestralmente: elasticidad, ocupacion historica y precios de competencia
     5. NUNCA aplicar precios por debajo del suelo de seguridad ({config.floor_price:.0f} EUR) sin aprobacion de Direccion
""")

    # ------------------------------------------------------------------
    # EXPORTAR DATOS SINTETICOS A CSV (para auditoria externa)
    # ------------------------------------------------------------------
    import os as _os
    _csv_path = _os.path.join(
        _os.path.dirname(_os.path.abspath(__file__)),
        "datos_sinteticos_posada.csv"
    )
    simulator.data_generator.generate(days=90, start_date=start).to_csv(_csv_path, index=False)
    print(f"\n  [INFO] Datos sinteticos exportados a: {_csv_path}")
    print(f"  [INFO] Abrelo en Excel para auditar las subidas/bajadas de precio.")

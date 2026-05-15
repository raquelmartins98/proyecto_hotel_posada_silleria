"""
Datos semilla del Hotel Posada de la Sillería (Toledo).

Contiene la configuración base del hotel:
    - Categorías de habitación
    - Costes fijos mensuales
    - Costes variables por estancia
    - Parámetros de inversión
    - Escenarios de ocupación
"""

from revenue_engine.models import (
    HotelConfig, RoomCategory, FixedCost, VariableCost,
    InvestmentParams, OccupancyScenario, AllocationMethod, ScenarioName,
)


def load_seed(name: str = "posada_silleria") -> HotelConfig:
    """
    Carga los datos semilla del hotel.
    
    Args:
        name: Nombre del seed a cargar
    
    Returns:
        HotelConfig con todos los datos configurados
    """
    if name == "posada_silleria":
        return _posada_silleria_config()
    
    raise ValueError(f"Seed desconocido: {name}")


def _posada_silleria_config() -> HotelConfig:
    """Configuración completa del Hotel Posada de la Sillería."""
    
    # ──── CATEGORÍAS DE HABITACIÓN ────
    rooms = [
        RoomCategory(
            cat_id="dob-001",
            code="DOB",
            name="Doble",
            room_count=12,
            max_guests=2,
            sqm=22.0,
            base_rate_2025=120.0,
            weight_factor=1.00,
            description="Habitación doble estándar con baño completo, TV y WiFi",
        ),
        RoomCategory(
            cat_id="sup-001",
            code="SUP",
            name="Superior",
            room_count=6,
            max_guests=2,
            sqm=32.5,
            base_rate_2025=155.0,
            weight_factor=1.35,
            description="Habitación superior con vistas al casco histórico, baño con ducha hidromasaje",
        ),
        RoomCategory(
            cat_id="sui-001",
            code="SUI",
            name="Suite Junior",
            room_count=4,
            max_guests=3,
            sqm=45.0,
            base_rate_2025=210.0,
            weight_factor=1.80,
            description="Suite con salón independiente, terraza y minibar",
        ),
    ]
    
    # ──── COSTES FIJOS MENSUALES ────
    fixed_costs = [
        FixedCost(
            line_id="FC-001", line_name="Personal Recepción",
            category="staff", monthly_amount=8_500.00,
            alloc_method=AllocationMethod.WEIGHTED,
            notes="2 recepcionistas turno partido + 1 jefe de recepción",
        ),
        FixedCost(
            line_id="FC-002", line_name="Personal Limpieza (fijo)",
            category="staff", monthly_amount=5_200.00,
            alloc_method=AllocationMethod.WEIGHTED,
            notes="2 limpiadoras fijas, 1 gobernanta",
        ),
        FixedCost(
            line_id="FC-003", line_name="Mantenimiento",
            category="mantenimiento", monthly_amount=1_800.00,
            alloc_method=AllocationMethod.SQM,
            notes="Conserjería, reparaciones, piscina (verano)",
        ),
        FixedCost(
            line_id="FC-004", line_name="Suministros (Luz, Agua, Gas)",
            category="suministros", monthly_amount=3_200.00,
            alloc_method=AllocationMethod.SQM,
            notes="Factura media anual, mayor en verano por aire acondicionado",
        ),
        FixedCost(
            line_id="FC-005", line_name="Seguros",
            category="seguros", monthly_amount=750.00,
            alloc_method=AllocationMethod.EQUAL,
            notes="Seguro multirriesgo hotelero + responsabilidad civil",
        ),
        FixedCost(
            line_id="FC-006", line_name="Marketing Digital",
            category="marketing", monthly_amount=1_200.00,
            alloc_method=AllocationMethod.WEIGHTED,
            notes="Google Ads, SEO, redes sociales",
        ),
        FixedCost(
            line_id="FC-007", line_name="Gestión / Admin",
            category="admin", monthly_amount=3_500.00,
            alloc_method=AllocationMethod.WEIGHTED,
            notes="Gestoría, asesoría fiscal, software de gestión",
        ),
        FixedCost(
            line_id="FC-008", line_name="Tecnología",
            category="tech", monthly_amount=950.00,
            alloc_method=AllocationMethod.WEIGHTED,
            notes="PMS, Channel Manager, WiFi, dominio web",
        ),
        FixedCost(
            line_id="FC-009", line_name="Financiero (Intereses)",
            category="financiero", monthly_amount=2_250.00,
            alloc_method=AllocationMethod.WEIGHTED,
            notes="Interés préstamo inversión inicial",
        ),
        FixedCost(
            line_id="FC-010", line_name="Suministros Extras",
            category="suministros", monthly_amount=800.00,
            alloc_method=AllocationMethod.SQM,
            notes="Lavandería externa (sábanas/toallas entre cambios de huésped)",
        ),
    ]
    
    # ──── COSTES VARIABLES POR ESTANCIA ────
    variable_costs = [
        # Habitación Doble
        VariableCost(cost_id="VC-DOB-01", room_cat_id="dob-001",
                     line_name="Limpieza de cambio", per_stay_amount=12.50),
        VariableCost(cost_id="VC-DOB-02", room_cat_id="dob-001",
                     line_name="Amenities baño", per_stay_amount=4.50),
        VariableCost(cost_id="VC-DOB-03", room_cat_id="dob-001",
                     line_name="Lavandería sábanas/toallas", per_stay_amount=6.00),
        VariableCost(cost_id="VC-DOB-04", room_cat_id="dob-001",
                     line_name="Desayuno (coste alimentos)", per_guest_amount=5.50),
        VariableCost(cost_id="VC-DOB-05", room_cat_id="dob-001",
                     line_name="Comisión OTA (media)", per_stay_amount=0.0,
                     ota_commission_pct=15.0),
        
        # Habitación Superior
        VariableCost(cost_id="VC-SUP-01", room_cat_id="sup-001",
                     line_name="Limpieza de cambio", per_stay_amount=14.00),
        VariableCost(cost_id="VC-SUP-02", room_cat_id="sup-001",
                     line_name="Amenities baño premium", per_stay_amount=7.00),
        VariableCost(cost_id="VC-SUP-03", room_cat_id="sup-001",
                     line_name="Lavandería sábanas/toallas", per_stay_amount=7.50),
        VariableCost(cost_id="VC-SUP-04", room_cat_id="sup-001",
                     line_name="Desayuno (coste alimentos)", per_guest_amount=5.50),
        VariableCost(cost_id="VC-SUP-05", room_cat_id="sup-001",
                     line_name="Comisión OTA (media)", per_stay_amount=0.0,
                     ota_commission_pct=15.0),
        
        # Suite Junior
        VariableCost(cost_id="VC-SUI-01", room_cat_id="sui-001",
                     line_name="Limpieza de cambio", per_stay_amount=18.00),
        VariableCost(cost_id="VC-SUI-02", room_cat_id="sui-001",
                     line_name="Amenities baño de lujo", per_stay_amount=12.00),
        VariableCost(cost_id="VC-SUI-03", room_cat_id="sui-001",
                     line_name="Lavandería sábanas/toallas", per_stay_amount=10.00),
        VariableCost(cost_id="VC-SUI-04", room_cat_id="sui-001",
                     line_name="Minibar reposición", per_stay_amount=8.00),
        VariableCost(cost_id="VC-SUI-05", room_cat_id="sui-001",
                     line_name="Desayuno (coste alimentos)", per_guest_amount=5.50),
        VariableCost(cost_id="VC-SUI-06", room_cat_id="sui-001",
                     line_name="Comisión OTA (media)", per_stay_amount=0.0,
                     ota_commission_pct=15.0),
    ]
    
    # ──── PARÁMETROS DE INVERSIÓN ────
    investment = InvestmentParams(
        total_investment=1_200_000.00,
        target_roi_pct=15.0,
        target_margin_pct=20.0,
        loan_amount=600_000.00,
        loan_annual_rate=4.5,
        loan_term_years=10,
        amortization_years=20,
        wacc=6.0,
    )
    
    # ──── ESCENARIOS DE OCUPACIÓN ────
    scenarios = [
        OccupancyScenario(
            scenario_id="ESC-01", scenario_name=ScenarioName.PESIMISTA,
            annual_occupancy_pct=45.0, season_high_occ_pct=60.0,
            season_low_occ_pct=30.0, avg_stay_days=1.5,
        ),
        OccupancyScenario(
            scenario_id="ESC-02", scenario_name=ScenarioName.REALISTA,
            annual_occupancy_pct=70.0, season_high_occ_pct=85.0,
            season_low_occ_pct=45.0, avg_stay_days=2.0,
        ),
        OccupancyScenario(
            scenario_id="ESC-03", scenario_name=ScenarioName.OPTIMISTA,
            annual_occupancy_pct=85.0, season_high_occ_pct=95.0,
            season_low_occ_pct=60.0, avg_stay_days=2.5,
        ),
    ]
    
    return HotelConfig(
        hotel_name="Hotel Posada de la Sillería",
        location="Toledo, España",
        currency="EUR",
        days_in_period=365,
        room_categories=rooms,
        fixed_costs=fixed_costs,
        variable_costs=variable_costs,
        investment=investment,
        scenarios=scenarios,
        biz_lines={
            "ALOJ": {"name": "Alojamiento",       "expected_revenue_pct": 65.0, "direct_cost_pct": 15.0},
            "REST": {"name": "Restauración",       "expected_revenue_pct": 25.0, "direct_cost_pct": 45.0},
            "EVENT": {"name": "Eventos",           "expected_revenue_pct": 10.0, "direct_cost_pct": 35.0},
        },
    )

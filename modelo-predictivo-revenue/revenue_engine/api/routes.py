"""
Endpoints REST del Revenue Management Engine.
"""

from datetime import date, datetime
import io
import csv

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from revenue_engine.models import (
    HotelConfig, ScenarioName, SimulationInput,
)
from revenue_engine.engine.pricing_engine import RevenueManager
from revenue_engine.toledo_calendar import ToledoCalendar


# ── Modelos de request (Pydantic) ───────────────────────────────────
# Los modelos del motor (HotelConfig, etc.) usan @dataclass.
# Solo los schemas de entrada/salida de la API usan Pydantic BaseModel.

class SimulateRequest(BaseModel):
    occupancy: float = Field(default=0.70, description="Ocupación esperada (0-1)")
    target_margin: float = Field(default=20.0, description="Margen objetivo (%)")
    target_roi: float = Field(default=15.0, description="ROI objetivo anual (%)")
    total_investment: float = Field(default=1_200_000.0, description="Inversión total (€)")
    scenario: str = Field(default="realista", description="Escenario: pesimista/realista/optimista")


class ROIRequest(BaseModel):
    annual_profit: float = Field(default=120_000.0, description="Beneficio neto anual (€)")
    total_investment: float = Field(default=1_200_000.0, description="Inversión total (€)")


class BookingPaceRequest(BaseModel):
    arrival_date: str = Field(description="Fecha de llegada (YYYY-MM-DD)")
    current_bookings: int = Field(default=0, description="Reservas confirmadas")
    total_rooms: int = Field(default=22, description="Total habitaciones del hotel")
    current_price: float = Field(default=80.0, description="Precio medio actual (€)")


router = APIRouter()


def get_manager() -> RevenueManager:
    """Crea un RevenueManager fresco por request. Sin estado mutable compartido."""
    config = HotelConfig.from_seed("posada_silleria")
    return RevenueManager(config)


@router.post("/simulate")
async def simulate(
    req: SimulateRequest,
    manager: RevenueManager = Depends(get_manager),
):
    """Ejecuta una simulación completa de pricing y rentabilidad."""
    scenario_map = {
        "pesimista": ScenarioName.PESIMISTA,
        "realista": ScenarioName.REALISTA,
        "optimista": ScenarioName.OPTIMISTA,
    }
    scenario_name = scenario_map.get(req.scenario.lower(), ScenarioName.REALISTA)
    
    result = manager.run_simulation(
        occupancy=req.occupancy,
        target_margin=req.target_margin,
        target_roi=req.target_roi,
        total_investment=req.total_investment,
        scenario_name=scenario_name,
    )
    
    return {"status": "ok", "result": result.to_dict()}


@router.get("/breakeven")
async def breakeven(
    manager: RevenueManager = Depends(get_manager),
    target_margin: float = Query(20.0),
    total_investment: float = Query(1_200_000.0),
):
    """Análisis de break-even con múltiples escenarios."""
    analysis = manager.breakeven_analysis(target_margin, total_investment)
    return {"status": "ok", "data": analysis}


@router.get("/seasonality")
async def seasonality(year: int = Query(2026, description="Año")):
    """Matriz de coeficientes estacionales para Toledo."""
    calendar = ToledoCalendar(year=year)
    
    periods = []
    for p in calendar.get_periods():
        try:
            sample_date = date(year, p.start[0], p.start[1])
        except (ValueError, OverflowError):
            sample_date = date(year, 6, 15)
        
        periods.append({
            "code": p.code,
            "name": p.name,
            "start": f"{p.start[0]:02d}-{p.start[1]:02d}",
            "end": f"{p.end[0]:02d}-{p.end[1]:02d}",
            "coefficient": p.coefficient,
            "is_event": p.is_event,
        })
    
    # Puentes
    puentes = [
        {"name": p[2], "start": p[0].isoformat(), "end": p[1].isoformat()}
        for p in calendar.get_puentes()
    ]
    
    return {
        "status": "ok",
        "year": year,
        "easter_sunday": calendar.easter_sunday.isoformat(),
        "periods": periods,
        "puentes": puentes,
    }


@router.get("/prices/daily")
async def daily_prices(
    manager: RevenueManager = Depends(get_manager),
    start_date: str = Query("2026-01-01"),
    end_date: str = Query("2026-12-31"),
):
    """Precios dinámicos para cada día del rango."""
    try:
        start = date.fromisoformat(start_date)
        end = date.fromisoformat(end_date)
    except ValueError:
        raise HTTPException(400, "Fechas inválidas. Use formato ISO: YYYY-MM-DD")
    
    pricing = manager.cost_engine.calculate(occupancy=0.70)
    base_prices = {cp.cat_id: cp.base_price for cp in pricing}
    marginal_costs = {cp.cat_id: cp.marginal_cost for cp in pricing}
    
    daily = manager.run_daily_pricing(start, end, base_prices, marginal_costs)
    
    return {
        "status": "ok",
        "prices": [
            {
                "date": p.date.isoformat(),
                "category": p.room_cat_id,
                "season": p.season,
                "coefficient": p.season_coefficient,
                "base_price": p.base_price,
                "final_price": p.final_price,
            }
            for p in daily
        ],
    }


@router.post("/roi")
async def roi_simulation(req: ROIRequest):
    """Cálculo de ROI y payback."""
    from revenue_engine.engine.roi_calculator import ROICalculator
    from revenue_engine.models import InvestmentParams
    
    calc = ROICalculator(InvestmentParams(total_investment=req.total_investment))
    result = calc.calculate(req.annual_profit, req.total_investment)
    projection = calc.project_years(req.annual_profit, years=10)
    sensitivity = calc.sensitivity_analysis(req.annual_profit)
    
    return {
        "status": "ok",
        "metrics": result,
        "projection": projection,
        "sensitivity": sensitivity,
    }


@router.get("/report/csv")
async def report_csv(
    manager: RevenueManager = Depends(get_manager),
    scenario: str = Query("realista"),
    occupancy: float = Query(0.70),
):
    """Exporta el reporte mensual a CSV."""
    scenario_map = {
        "pesimista": ScenarioName.PESIMISTA,
        "realista": ScenarioName.REALISTA,
        "optimista": ScenarioName.OPTIMISTA,
    }
    scenario_name = scenario_map.get(scenario.lower(), ScenarioName.REALISTA)
    
    result = manager.run_simulation(occupancy=occupancy, scenario_name=scenario_name)
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    writer.writerow(["RESUMEN EJECUTIVO"])
    writer.writerow(["Métrica", "Valor"])
    writer.writerow(["Ocupación", f"{occupancy:.1%}"])
    writer.writerow(["Ingreso Bruto Anual", f"{result.total_revenue:.2f}€"])
    writer.writerow(["Costes Totales", f"{result.total_costs:.2f}€"])
    writer.writerow(["Beneficio Neto", f"{result.net_profit:.2f}€"])
    writer.writerow(["Margen Neto", f"{result.net_margin_pct:.2f}%"])
    writer.writerow(["Break-Even Ocupación", f"{result.breakeven_occupancy_pct:.1f}%"])
    writer.writerow(["ROI", f"{result.roi_pct:.2f}%"])
    writer.writerow(["Payback", f"{result.payback_years:.2f} años"])
    writer.writerow([])
    
    writer.writerow(["DESGLOSE POR CATEGORÍA"])
    writer.writerow(["Categoría", "Unidades", "CosteFijo/N", "CosteVar/N", "CosteMarginal", "Precio"])
    for cp in result.category_pricing:
        writer.writerow([
            cp.cat_name, cp.room_count,
            f"{cp.fixed_per_night:.2f}€",
            f"{cp.variable_per_night:.2f}€",
            f"{cp.marginal_cost:.2f}€",
            f"{cp.base_price:.2f}€",
        ])
    writer.writerow([])
    
    writer.writerow(["P&L MENSUAL"])
    writer.writerow(["Mes", "Temporada", "Ingresos", "Costes", "Beneficio", "Margen%"])
    for m in (result.monthly_pnl or []):
        writer.writerow([
            m["month_name"], m["season_name"],
            f"{m['revenue']:.2f}€", f"{m['costs']:.2f}€",
            f"{m['profit']:.2f}€", f"{m['margin_pct']:.1f}%",
        ])
    
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=report_{scenario}_{date.today()}.csv"},
    )


@router.post("/booking-pace")
async def booking_pace(
    req: BookingPaceRequest,
    manager: RevenueManager = Depends(get_manager),
):
    """Proyección de ocupación por booking pace."""
    try:
        arrival = date.fromisoformat(req.arrival_date)
    except ValueError:
        raise HTTPException(400, "Fecha inválida. Use formato ISO: YYYY-MM-DD")
    
    report = manager.booking_pace.snapshot_report(
        d=arrival,
        current_bookings=req.current_bookings,
        total_rooms=req.total_rooms,
        current_price=req.current_price,
    )
    
    return {"status": "ok", "data": report}


@router.get("/ota-analysis")
async def ota_analysis(bar_price: float = Query(100.0)):
    """Análisis comparativo de canales OTA vs directo."""
    from revenue_engine.engine.ota import CommissionModel, CannibalizationModel
    
    commission = CommissionModel(bar_price=bar_price)
    channels = commission.channel_report()
    
    cannibalization = CannibalizationModel()
    mix = cannibalization.analyze_channel_mix(
        bar_price=bar_price,
        direct_demand=30,
        ota_demand=20,
    )
    
    return {
        "status": "ok",
        "channels": channels,
        "cannibalization_analysis": mix,
    }


@router.get("/health")
async def health():
    """Health check."""
    return {
        "status": "healthy",
        "engine": "Revenue Management v1.0.0",
        "hotel": "Hotel Posada de la Sillería",
    }

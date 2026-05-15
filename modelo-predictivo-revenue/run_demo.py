#!/usr/bin/env python3
"""
Script de integración — demo rápida del Revenue Management Engine.

Ejecuta una simulación completa y muestra los resultados en consola.

Uso:
    python run_demo.py
"""

import sys
import io
from pathlib import Path

# Forzar UTF-8 para evitar problemas de codificación en Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Asegurar que el paquete está en el path
sys.path.insert(0, str(Path(__file__).parent))

from revenue_engine.models import HotelConfig, ScenarioName
from revenue_engine.engine.pricing_engine import RevenueManager


def main():
    print("═══ MODELO PREDICTIVO DE REVENUE MANAGEMENT ═══")
    print("═══════════ Hotel Posada de la Sillería ═══════\n")
    
    # 1. Cargar configuración
    print("📦 Cargando datos del hotel...")
    config = HotelConfig.from_seed("posada_silleria")
    manager = RevenueManager(config)
    
    print(f"   Hotel:          {config.hotel_name}")
    print(f"   Ubicación:      {config.location}")
    print(f"   Habitaciones:   {config.total_rooms()} ({sum(c.room_count for c in config.room_categories)} disponibles)")
    print(f"   Categorías:     {', '.join(c.name for c in config.room_categories)}")
    print(f"   Costes Fijos:   {manager.cost_engine.total_fixed_costs:,.2f}€/año ({manager.cost_engine.total_fixed_costs_monthly:,.2f}€/mes)\n")
    
    # 2. Simulación multi-escenario
    print("📊 EJECUTANDO SIMULACIONES MULTI-ESCENARIO\n")
    
    escenarios = [
        ("🔴 Pesimista",  0.45, "ocupación baja (45%)"),
        ("🟡 Realista",   0.70, "ocupación moderada (70%)"),
        ("🟢 Optimista",  0.85, "ocupación alta (85%)"),
    ]
    
    for emoji, occ, desc in escenarios:
        print(f"  {emoji} {desc}...")
        result = manager.run_simulation(occupancy=occ, scenario_name=ScenarioName.REALISTA)
        
        print(f"     Ingresos:      {result.total_revenue:>12,.2f}€")
        print(f"     Costes:        {result.total_costs:>12,.2f}€")
        print(f"     Beneficio:     {result.net_profit:>12,.2f}€")
        print(f"     Margen:        {result.net_margin_pct:>8.2f}%")
        print(f"     BE Ocupación:  {result.breakeven_occupancy_pct:>8.1f}%")
        print(f"     ROI:           {result.roi_pct:>8.2f}%")
        print(f"     Payback:       {result.payback_years:>8.2f} años\n")
    
    # 3. Precios por categoría
    print("💰 PRECIOS RECOMENDADOS (Escenario Realista 70%)\n")
    pricing = manager.cost_engine.calculate(occupancy=0.70, target_margin=20.0)
    
    print(f"  {'Categoría':<20} {'Coste':>10} {'Precio':>10} {'Margen':>10} {'Margen%':>8}")
    print(f"  {'─'*58}")
    
    for p in pricing:
        margin = p.base_price - p.marginal_cost
        margin_pct = (margin / p.base_price * 100)
        print(f"  {p.cat_name:<20} {p.marginal_cost:>8.2f}€ {p.base_price:>8.2f}€ "
              f"{margin:>8.2f}€ {margin_pct:>6.1f}%")
    
    # 4. Calendario estacional
    print("\n📅 CALENDARIO ESTACIONAL TOLEDO 2026\n")
    cal = manager.calendar
    
    fechas_ejemplo = [
        ("Año Nuevo",    date(2026, 1, 1)),
        ("Baja Invierno", date(2026, 1, 20)),
        ("Media Invierno", date(2026, 3, 5)),
        ("Viernes Santo", date(2026, 4, 3)),
        ("Domingo Resurr.", date(2026, 4, 5)),
        ("Corpus Christi", date(2026, 6, 4)),
        ("Verano",       date(2026, 8, 15)),
        ("Hispanidad",   date(2026, 10, 12)),
        ("Navidad",      date(2026, 12, 25)),
    ]
    
    print(f"  {'Fecha':<20} {'Coeficiente':<15} {'Temporada'}")
    print(f"  {'─'*50}")
    for name, d in fechas_ejemplo:
        coeff = cal.get_coefficient(d)
        season = manager.seasonal.get_season_name(d)
        print(f"  {name:<20} {coeff:>8.4f}     {season}")
    
    print("\n✅ Demo completada con éxito.")


if __name__ == "__main__":
    from datetime import date
    main()

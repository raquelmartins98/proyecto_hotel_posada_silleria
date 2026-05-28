"""Motor de cálculo puro — funciones sin efectos secundarios.

Todas las funciones en este paquete son determinísticas y no realizan I/O.
Esto permite testear los cálculos financieros de forma aislada.
"""

"""Motor de cálculo puro — funciones sin efectos secundarios.

Todas las funciones en este paquete son determinísticas y no realizan I/O.
"""

from posada_revenue.engine.marginal_cost import marginal_cost
from posada_revenue.engine.allocation import allocate_fixed_costs_to_room

# Los siguientes módulos se importan al crearlos:
# from posada_revenue.engine.breakeven import breakeven_price, breakeven_with_fixed
# from posada_revenue.engine.dynamic_pricing import dynamic_price, suggested_price
# from posada_revenue.engine.profit_allocation import allocate_profit_target, required_revenue
# from posada_revenue.engine.roi import payback_period, net_present_value, internal_rate_of_return

__all__ = [
    "marginal_cost",
    "allocate_fixed_costs_to_room",
]

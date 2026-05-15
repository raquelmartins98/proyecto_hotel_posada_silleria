"""
Motor de Reparto Homogéneo de Beneficio entre Líneas de Negocio.

Distribuye el objetivo de beneficio de forma proporcional al margen
de contribución de cada línea de negocio (alojamiento, restauración, eventos).
"""

from typing import Dict, List, Optional, Tuple


class ProfitDistributionEngine:
    """
    Distribuye el beneficio objetivo entre las líneas de negocio.
    
    Principio: cada línea recibe una parte del beneficio proporcional
    a su margen de contribución esperado.
    
    AllocatedProfit_j = TargetProfit * (
        Revenue_j * ContributionMargin_j
        / Σ(Revenue_k * ContributionMargin_k)
    )
    """
    
    def __init__(
        self,
        biz_lines: Dict[str, Dict],
        alojamiento_revenue: float,
    ):
        """
        Args:
            biz_lines: Dict con líneas de negocio
                {"ALOJ": {"name": ..., "expected_revenue_pct": ..., "direct_cost_pct": ...}}
            alojamiento_revenue: Ingreso estimado de alojamiento
        """
        self.biz_lines = biz_lines
        self.alojamiento_revenue = alojamiento_revenue
    
    def estimate_line_revenues(self) -> Dict[str, float]:
        """
        Estima los ingresos de cada línea basándose en el mix histórico.
        
        REST_revenue = ALOJ_revenue * (pct_REST / pct_ALOJ)
        EVENT_revenue = ALOJ_revenue * (pct_EVENT / pct_ALOJ)
        """
        revenues = {}
        
        aloj_pct = self.biz_lines.get("ALOJ", {}).get("expected_revenue_pct", 65.0)
        revenues["ALOJ"] = self.alojamiento_revenue
        
        for code, info in self.biz_lines.items():
            if code == "ALOJ":
                continue
            pct = info.get("expected_revenue_pct", 0)
            revenues[code] = (
                self.alojamiento_revenue * (pct / aloj_pct)
                if aloj_pct > 0 else 0
            )
        
        return revenues
    
    def contribution_margins(self) -> Dict[str, float]:
        """Calcula el margen de contribución de cada línea."""
        margins = {}
        for code, info in self.biz_lines.items():
            margins[code] = 100 - info.get("direct_cost_pct", 0)
        return margins
    
    def weighted_contribution(self, revenues: Dict[str, float]) -> Dict[str, float]:
        """Contribución ponderada = Revenue * ContributionMargin."""
        margins = self.contribution_margins()
        weighted = {}
        for code, rev in revenues.items():
            weighted[code] = rev * (margins.get(code, 0) / 100)
        return weighted
    
    def distribute(
        self,
        target_profit: float,
    ) -> Dict[str, float]:
        """
        Distribuye el beneficio objetivo entre líneas.
        
        Args:
            target_profit: Beneficio objetivo total a distribuir
        
        Returns:
            Dict con {line_code: beneficio_asignado}
        """
        revenues = self.estimate_line_revenues()
        weighted = self.weighted_contribution(revenues)
        total_weighted = sum(weighted.values())
        
        if total_weighted == 0:
            return {code: 0.0 for code in self.biz_lines}
        
        allocation = {}
        for code in self.biz_lines:
            allocation[code] = round(
                target_profit * weighted.get(code, 0) / total_weighted,
                2,
            )
        
        # Ajustar por redondeo para que sumen exactamente target_profit
        total_allocated = sum(allocation.values())
        diff = round(target_profit - total_allocated, 2)
        if diff != 0 and allocation:
            # Ajustar la línea con mayor peso
            max_code = max(allocation, key=allocation.get)
            allocation[max_code] = round(allocation[max_code] + diff, 2)
        
        return allocation
    
    def report(self, target_profit: float) -> Dict:
        """
        Reporte completo de distribución de beneficio.
        """
        revenues = self.estimate_line_revenues()
        margins = self.contribution_margins()
        weighted = self.weighted_contribution(revenues)
        allocation = self.distribute(target_profit)
        
        lines = []
        for code, info in self.biz_lines.items():
            lines.append({
                "code": code,
                "name": info["name"],
                "estimated_revenue": round(revenues.get(code, 0), 2),
                "direct_cost_pct": info["direct_cost_pct"],
                "contribution_margin_pct": margins.get(code, 0),
                "weighted_contribution": round(weighted.get(code, 0), 2),
                "weight_pct": round(
                    weighted.get(code, 0) / sum(weighted.values()) * 100
                    if sum(weighted.values()) > 0 else 0,
                    2,
                ),
                "allocated_profit": round(allocation.get(code, 0), 2),
            })
        
        return {
            "target_profit": round(target_profit, 2),
            "total_allocated": round(sum(allocation.values()), 2),
            "verified": abs(target_profit - sum(allocation.values())) < 0.01,
            "lines": lines,
        }

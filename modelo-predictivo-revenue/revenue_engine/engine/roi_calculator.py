"""
Motor de Cálculo de ROI y Payback.

Implementa:
    - ROI anual sobre inversión total
    - Payback period (años para recuperar inversión)
    - Economic Value Added (EVA)
    - Amortización y coste de financiación
    - Proyección multi-anual
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional
import math

from revenue_engine.models import InvestmentParams


class ROICalculator:
    """
    Calcula métricas de rentabilidad sobre la inversión.
    
    Fórmulas:
        ROI = (NetProfit / TotalInvestment) * 100
        Payback = TotalInvestment / AnnualNetProfit
        EVA = NetProfit - (TotalInvestedCapital * WACC / 100)
    """
    
    def __init__(self, investment: InvestmentParams):
        self.investment = investment
    
    @property
    def annual_loan_payment(self) -> float:
        """Pago anual del préstamo (método francés)."""
        if self.investment.loan_amount <= 0 or self.investment.loan_annual_rate <= 0:
            return 0.0
        
        P = self.investment.loan_amount
        r = self.investment.loan_annual_rate / 100 / 12  # tasa mensual
        n = self.investment.loan_term_years * 12  # meses
        
        if r <= 0 or n <= 0:
            return P / max(n, 1)
        
        monthly = P * r * (1 + r)**n / ((1 + r)**n - 1)
        return round(monthly * 12, 2)  # pago anual
    
    @property
    def annual_depreciation(self) -> float:
        """Amortización anual lineal."""
        if self.investment.amortization_years <= 0:
            return 0.0
        return round(self.investment.total_investment / self.investment.amortization_years, 2)
    
    def calculate(
        self,
        annual_net_profit: float,
        total_investment: Optional[float] = None,
    ) -> Dict:
        """
        Calcula métricas de rentabilidad.
        
        Args:
            annual_net_profit: Beneficio neto anual después de costes
            total_investment: Inversión total (usa InvestmentParams si no se especifica)
        
        Returns:
            Dict con métricas calculadas
        """
        if total_investment is None:
            total_investment = self.investment.total_investment
        
        if total_investment <= 0:
            return {
                "roi_pct": 0.0,
                "payback_years": float('inf'),
                "adjusted_roi_pct": 0.0,
                "eva": 0.0,
                "annual_loan_payment": self.annual_loan_payment,
                "annual_depreciation": self.annual_depreciation,
            }
        
        # Beneficio después de intereses (pero antes de amortización contable)
        profit_after_loan = annual_net_profit - self.annual_loan_payment
        
        # ROI
        roi = (annual_net_profit / total_investment) * 100
        
        # Payback
        payback = total_investment / annual_net_profit if annual_net_profit > 0 else float('inf')
        
        # ROI ajustado (después de coste de capital)
        capital_charge = total_investment * self.investment.wacc / 100
        adjusted_roi = ((annual_net_profit - capital_charge) / total_investment) * 100
        
        # Economic Value Added
        eva = annual_net_profit - capital_charge
        
        return {
            "roi_pct": round(roi, 2),
            "payback_years": round(payback, 2),
            "adjusted_roi_pct": round(adjusted_roi, 2),
            "eva": round(eva, 2),
            "annual_loan_payment": round(self.annual_loan_payment, 2),
            "annual_depreciation": round(self.annual_depreciation, 2),
        }
    
    def project_years(
        self,
        annual_net_profit: float,
        years: int = 10,
    ) -> List[Dict]:
        """
        Proyección multi-anual de rentabilidad.
        
        Incluye:
        - Amortización acumulada
        - Pago de intereses decreciente
        - Valor neto contable
        - ROI acumulado
        """
        projection = []
        
        remaining_debt = self.investment.loan_amount
        annual_payment = self.annual_loan_payment
        monthly_rate = self.investment.loan_annual_rate / 100 / 12
        
        for year in range(1, years + 1):
            if remaining_debt > 0 and annual_payment > 0:
                # Desglose interés vs. principal (aproximación anual)
                if monthly_rate > 0:
                    # Calcular interés del año
                    interest_year = 0
                    for _ in range(12):
                        interest_month = remaining_debt * monthly_rate
                        principal_month = min(
                            (annual_payment / 12) - interest_month,
                            remaining_debt,
                        )
                        interest_year += interest_month
                        remaining_debt -= principal_month
                        if remaining_debt <= 0:
                            remaining_debt = 0
                            break
                else:
                    interest_year = 0
                    remaining_debt -= annual_payment
                    remaining_debt = max(0, remaining_debt)
            else:
                interest_year = 0
            
            net_profit_after_loan = annual_net_profit - interest_year
            
            # Valor neto contable de la inversión
            book_value = max(
                0,
                self.investment.total_investment
                - (self.annual_depreciation * year)
            )
            
            investment_remaining = max(
                0,
                self.investment.total_investment
                - (self.annual_depreciation * (year - 1))
            )
            
            roi_year = (net_profit_after_loan / investment_remaining * 100) if investment_remaining > 0 else 0
            
            projection.append({
                "year": year,
                "net_profit": round(net_profit_after_loan, 2),
                "interest_paid": round(interest_year, 2),
                "remaining_debt": round(max(0, remaining_debt), 2),
                "book_value": round(book_value, 2),
                "roi_pct": round(roi_year, 2),
                "cumulative_cash_flow": round(
                    net_profit_after_loan * year, 2  # simplified
                ),
            })
        
        return projection
    
    def sensitivity_analysis(
        self,
        base_net_profit: float,
        occupancy_variations: List[float] = None,
    ) -> Dict:
        """
        Análisis de sensibilidad: ¿cómo cambia el ROI con la ocupación?
        
        Args:
            base_net_profit: Beneficio neto base
            occupancy_variations: Variaciones de ocupación a probar
        
        Returns:
            Dict con escenarios
        """
        if occupancy_variations is None:
            occupancy_variations = [-0.20, -0.10, -0.05, 0.0, 0.05, 0.10, 0.20]
        
        scenarios = []
        for var in occupancy_variations:
            adjusted_profit = base_net_profit * (1 + var)
            result = self.calculate(adjusted_profit)
            scenarios.append({
                "occupancy_variation_pct": round(var * 100, 1),
                "net_profit": round(adjusted_profit, 2),
                "roi_pct": result["roi_pct"],
                "payback_years": result["payback_years"],
                "status": "RENTABLE" if result["roi_pct"] > self.investment.wacc else "NO_RENTABLE",
            })
        
        return {"base_investment": self.investment.total_investment, "scenarios": scenarios}

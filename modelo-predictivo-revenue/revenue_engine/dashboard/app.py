"""
Dashboard interactivo del Revenue Management Engine.

Panel de control para:
    - Simulación de pricing y rentabilidad
    - Visualización de precios dinámicos
    - Análisis de booking pace
    - Proyección de ROI
    - Calendario estacional de Toledo
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import date, timedelta, datetime
from typing import Dict, List

from revenue_engine.models import HotelConfig, ScenarioName
from revenue_engine.engine.pricing_engine import RevenueManager
from revenue_engine.toledo_calendar import ToledoCalendar

# ─── CONFIGURACIÓN DE PÁGINA ───
st.set_page_config(
    page_title="Revenue Management — Posada de la Sillería",
    page_icon="🏨",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("🏨 Modelo Predictivo de Revenue Management")
st.markdown("### Hotel Posada de la Sillería — Toledo")
st.markdown("---")

# ─── CARGA DEL MOTOR ───
@st.cache_resource
def load_manager():
    config = HotelConfig.from_seed("posada_silleria")
    return RevenueManager(config)


manager = load_manager()

# ─── SIDEBAR ───
st.sidebar.header("⚙️ Parámetros de Simulación")

occupancy = st.sidebar.slider(
    "Ocupación esperada",
    min_value=0.0, max_value=1.0, value=0.70, step=0.05,
    format="%.0f%%",
)

target_margin = st.sidebar.slider(
    "Margen objetivo (%)",
    min_value=5.0, max_value=50.0, value=20.0, step=1.0,
)

target_roi = st.sidebar.slider(
    "ROI objetivo anual (%)",
    min_value=5.0, max_value=30.0, value=15.0, step=1.0,
)

total_investment = st.sidebar.number_input(
    "Inversión total (€)",
    min_value=100_000, max_value=10_000_000, value=1_200_000, step=50_000,
    format="%d",
)

scenario = st.sidebar.selectbox(
    "Escenario",
    options=["realista", "pesimista", "optimista"],
    index=0,
)

scenario_map = {
    "realista": ScenarioName.REALISTA,
    "pesimista": ScenarioName.PESIMISTA,
    "optimista": ScenarioName.OPTIMISTA,
}

# ─── BOTÓN DE SIMULACIÓN ───
if st.sidebar.button("▶ Ejecutar Simulación", type="primary", use_container_width=True):
    with st.spinner("Calculando..."):
        result = manager.run_simulation(
            occupancy=occupancy,
            target_margin=target_margin,
            target_roi=target_roi,
            total_investment=total_investment,
            scenario_name=scenario_map[scenario],
        )

    # ─── MÉTRICAS CLAVE ───
    st.subheader("📊 Resumen Ejecutivo")
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric("Ingreso Bruto Anual", f"{result.total_revenue:,.0f}€",
                  help="Ingreso total estimado del período")
    with col2:
        st.metric("Beneficio Neto", f"{result.net_profit:,.0f}€",
                  delta=f"{result.net_margin_pct:.1f}% margen",
                  help="Beneficio después de costes")
    with col3:
        st.metric("Break-Even Ocupación", f"{result.breakeven_occupancy_pct:.1f}%",
                  delta=f"{occupancy - result.breakeven_occupancy_pct/100:.1%} sobre objetivo",
                  delta_color="inverse",
                  help="Ocupación necesaria para cubrir costes")
    with col4:
        st.metric("ROI Anual", f"{result.roi_pct:.2f}%",
                  delta=f"{result.roi_pct - target_roi:.1f}% vs objetivo",
                  help="Retorno sobre inversión anual")
    with col5:
        st.metric("Payback", f"{result.payback_years:.2f} años",
                  help="Años para recuperar la inversión")

    st.markdown("---")

    # ─── DESGLOSE POR CATEGORÍA ───
    st.subheader("🛏️ Desglose por Categoría de Habitación")

    cat_data = []
    for cp in result.category_pricing:
        margin_eur = cp.base_price - cp.marginal_cost
        margin_pct = margin_eur / cp.base_price * 100 if cp.base_price > 0 else 0
        cat_data.append({
            "Categoría": cp.cat_name,
            "Unidades": cp.room_count,
            "Coste Fijo/N": cp.fixed_per_night,
            "Coste Variable/N": cp.variable_per_night,
            "Coste Marginal": cp.marginal_cost,
            "Preció Base (€)": cp.base_price,
            "Margen (€)": round(margin_eur, 2),
            "Margen (%)": round(margin_pct, 1),
        })

    df_cats = pd.DataFrame(cat_data)
    st.dataframe(df_cats, use_container_width=True, hide_index=True)

    # Gráfico de barras
    fig_cats = px.bar(
        df_cats, x="Categoría", y=["Coste Marginal", "Preció Base (€)"],
        barmode="group", title="Coste Marginal vs Precio Base por Categoría",
        color_discrete_sequence=["#c44e52", "#4c72b0"],
    )
    st.plotly_chart(fig_cats, use_container_width=True)

    st.markdown("---")

    # ─── P&L MENSUAL ───
    st.subheader("📆 P&L Estacional")

    if result.monthly_pnl:
        df_pnl = pd.DataFrame(result.monthly_pnl)
        df_pnl_display = df_pnl.rename(columns={
            "month_name": "Mes",
            "season_name": "Temporada",
            "revenue": "Ingresos",
            "costs": "Costes",
            "profit": "Beneficio",
            "margin_pct": "Margen %",
        })
        df_pnl_display["Ingresos"] = df_pnl_display["Ingresos"].apply(lambda x: f"{x:,.2f}€")
        df_pnl_display["Costes"] = df_pnl_display["Costes"].apply(lambda x: f"{x:,.2f}€")
        df_pnl_display["Beneficio"] = df_pnl_display["Beneficio"].apply(lambda x: f"{x:,.2f}€")

        col_pnl1, col_pnl2 = st.columns([2, 1])

        with col_pnl1:
            st.dataframe(
                df_pnl_display[["Mes", "Temporada", "Ingresos", "Costes", "Beneficio", "Margen %"]],
                use_container_width=True, hide_index=True,
            )

        with col_pnl2:
            # Gráfico de barras apiladas mensual
            fig_pnl = go.Figure()
            fig_pnl.add_trace(go.Bar(
                name="Beneficio",
                x=df_pnl["month_name"],
                y=df_pnl["profit"],
                marker_color=["green" if p >= 0 else "red" for p in df_pnl["profit"]],
            ))
            fig_pnl.add_trace(go.Scatter(
                name="Acumulado",
                x=df_pnl["month_name"],
                y=df_pnl["running_profit"],
                line=dict(color="blue", width=2),
                mode="lines+markers",
                yaxis="y2",
            ))
            fig_pnl.update_layout(
                title="Beneficio Mensual",
                yaxis=dict(title="Beneficio (€)"),
                yaxis2=dict(
                    title="Acumulado (€)",
                    overlaying="y",
                    side="right",
                ),
                height=350,
                margin=dict(l=20, r=20, t=40, b=20),
            )
            st.plotly_chart(fig_pnl, use_container_width=True)

    st.markdown("---")

    # ─── REPARTO DE BENEFICIO ───
    st.subheader("📊 Reparto Homogéneo de Beneficio")
    col_dist1, col_dist2 = st.columns([1, 2])

    with col_dist1:
        df_alloc = pd.DataFrame([
            {"Línea": manager.config.biz_lines.get(c, {}).get("name", c),
             "Beneficio Asignado": f"{p:,.2f}€/mes"}
            for c, p in result.allocated_profits.items()
        ])
        st.dataframe(df_alloc, use_container_width=True, hide_index=True)

    with col_dist2:
        fig_alloc = px.pie(
            names=[manager.config.biz_lines.get(c, {}).get("name", c)
                   for c in result.allocated_profits.keys()],
            values=list(result.allocated_profits.values()),
            title="Distribución del Beneficio Objetivo por Línea de Negocio",
            color_discrete_sequence=px.colors.qualitative.Set2,
        )
        st.plotly_chart(fig_alloc, use_container_width=True)

    st.markdown("---")

    # ─── PRECIOS DINÁMICOS ───
    st.subheader("📈 Precios Dinámicos Anuales")
    if result.daily_prices:
        # Convertir a DataFrame
        price_rows = []
        for date_str, cat_prices in list(result.daily_prices.items())[::7]:  # semanal
            for cat_id, price in cat_prices.items():
                cat_name = next(
                    (c.name for c in manager.config.room_categories if c.cat_id == cat_id),
                    cat_id,
                )
                price_rows.append({
                    "Fecha": date_str,
                    "Categoría": cat_name,
                    "Precio (€)": price,
                })

        if price_rows:
            df_prices = pd.DataFrame(price_rows)

            fig_prices = px.line(
                df_prices, x="Fecha", y="Precio (€)", color="Categoría",
                title="Evolución Anual de Precios por Categoría",
                color_discrete_sequence=px.colors.qualitative.Set1,
            )
            fig_prices.update_xases(
                dtick="M1", tickformat="%b",
                rangeslider_visible=True,
            )
            st.plotly_chart(fig_prices, use_container_width=True)

    st.success("✅ Simulación completada con éxito")

# ─── INFORMACIÓN DEL HOTEL ───
else:
    st.info("👈 Ajusta los parámetros en la barra lateral y pulsa 'Ejecutar Simulación'")

    st.markdown("### 📋 Configuración Actual del Hotel")

    col_h1, col_h2 = st.columns(2)

    with col_h1:
        st.markdown(f"**Hotel:** {manager.config.hotel_name}")
        st.markdown(f"**Ubicación:** {manager.config.location}")
        st.markdown(f"**Habitaciones totales:** {manager.config.total_rooms()}")
        st.markdown(f"**Costes fijos mensuales:** {manager.cost_engine.total_fixed_costs:,.2f}€")

        st.markdown("#### Categorías de Habitación")
        rooms_df = pd.DataFrame([
            {"Categoría": c.name, "Unidades": c.room_count,
             "Capacidad": c.max_guests, "m²": c.sqm, "Peso": c.weight_factor}
            for c in manager.config.room_categories
        ])
        st.dataframe(rooms_df, use_container_width=True, hide_index=True)

    with col_h2:
        st.markdown("#### Líneas de Negocio")
        biz_df = pd.DataFrame([
            {"Línea": v["name"], "Ingreso Esperado": f'{v["expected_revenue_pct"]}%',
             "Coste Directo": f'{v["direct_cost_pct"]}%'}
            for v in manager.config.biz_lines.values()
        ])
        st.dataframe(biz_df, use_container_width=True, hide_index=True)

        st.markdown("#### Parámetros de Inversión")
        inv = manager.config.investment
        st.markdown(f"- Inversión total: **{inv.total_investment:,.0f}€**")
        st.markdown(f"- Préstamo: **{inv.loan_amount:,.0f}€** al **{inv.loan_annual_rate}%**")
        st.markdown(f"- Plazo: **{inv.loan_term_years} años**")
        st.markdown(f"- Amortización: **{inv.amortization_years} años**")
        st.markdown(f"- WACC: **{inv.wacc}%**")

    st.markdown("---")
    st.markdown(
        "### 📖 Cómo usar este dashboard\n\n"
        "1. Ajusta los parámetros en la barra lateral (ocupación, margen, ROI, inversión)\n"
        "2. Selecciona el escenario (realista, pesimista, optimista)\n"
        "3. Pulsa **'Ejecutar Simulación'**\n"
        "4. Explora los resultados: resumen ejecutivo, desglose por categoría, P&L mensual,\n"
        "   reparto de beneficio y precios dinámicos anuales"
    )


# ─── FOOTER ───
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: gray; font-size: 0.8em;'>"
    "Revenue Management Engine v1.0.0 — Hotel Posada de la Sillería (Toledo) "
    "| Desarrollado con Python, FastAPI, Streamlit"
    "</div>",
    unsafe_allow_html=True,
)

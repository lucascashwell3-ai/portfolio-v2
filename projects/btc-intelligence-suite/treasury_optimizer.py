"""
BTC Treasury Optimizer
======================
Models optimal BTC acquisition strategy for corporate treasuries.
Replicates/extends Saylor's "BTC Yield" KPI logic with stress testing.

Run: streamlit run app.py
"""

import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from dataclasses import dataclass
from typing import Tuple
import warnings
warnings.filterwarnings("ignore")

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="BTC Treasury Optimizer",
    page_icon="₿",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Styling ───────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&family=JetBrains+Mono:wght@400;600&display=swap');

    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .main { background-color: #0a0a0a; }
    .stApp { background-color: #0a0a0a; color: #e8e8e8; }

    .metric-card {
        background: linear-gradient(135deg, #111111 0%, #1a1a1a 100%);
        border: 1px solid #2a2a2a;
        border-radius: 8px;
        padding: 20px;
        margin: 8px 0;
    }
    .metric-label {
        font-size: 11px;
        font-weight: 600;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        color: #888;
        margin-bottom: 6px;
    }
    .metric-value {
        font-family: 'JetBrains Mono', monospace;
        font-size: 28px;
        font-weight: 600;
        color: #f7931a;
    }
    .metric-sub {
        font-size: 12px;
        color: #666;
        margin-top: 4px;
    }
    .positive { color: #00c853; }
    .negative { color: #ff1744; }
    .neutral  { color: #888; }
    .section-header {
        font-size: 13px;
        font-weight: 600;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        color: #f7931a;
        border-bottom: 1px solid #222;
        padding-bottom: 8px;
        margin: 24px 0 16px 0;
    }
    .insight-box {
        background: #111;
        border-left: 3px solid #f7931a;
        padding: 12px 16px;
        border-radius: 0 6px 6px 0;
        margin: 8px 0;
        font-size: 13px;
        color: #ccc;
    }
    div[data-testid="stSidebar"] {
        background-color: #0d0d0d;
        border-right: 1px solid #1e1e1e;
    }
    .stSlider > div > div { background: #222; }
</style>
""", unsafe_allow_html=True)

# ── Historical BTC data (mock — monthly closes, 2020-2024) ────────────────────
BTC_HISTORICAL = {
    "2020-01": 9350, "2020-04": 8624, "2020-07": 11351, "2020-10": 13804,
    "2021-01": 33141, "2021-04": 57750, "2021-07": 41538, "2021-10": 62000,
    "2022-01": 38500, "2022-04": 46300, "2022-07": 23300, "2022-10": 20492,
    "2023-01": 23122, "2023-04": 29244, "2023-07": 29230, "2023-10": 34671,
    "2024-01": 42600, "2024-04": 71000, "2024-07": 66000, "2024-10": 68500,
    "2024-12": 97000,
}

BTC_DRAWDOWNS = {
    "2011 Crash": -93,
    "2013-14 Mt.Gox": -85,
    "2018 Bear": -84,
    "2020 COVID": -63,
    "2022 Bear": -77,
    "Median drawdown": -75,
}

# ── Core math ─────────────────────────────────────────────────────────────────
@dataclass
class TreasuryInputs:
    cash_usd: float          # available treasury cash ($M)
    btc_alloc_pct: float     # % of cash going to BTC
    shares_outstanding: float # millions
    share_price: float        # current share price
    debt_capacity: float      # additional debt willing to issue ($M)
    btc_price: float          # current BTC price
    time_horizon_yrs: int
    btc_cagr_assumption: float  # conservative annual growth assumption
    cost_of_debt: float       # interest rate on any BTC-backed debt


def compute_btc_yield(btc_holdings: float, shares: float, btc_price: float) -> float:
    """BTC Yield = BTC per diluted share. Saylor's core KPI."""
    return (btc_holdings / shares) * btc_price


def model_acquisition_tranches(inputs: TreasuryInputs) -> pd.DataFrame:
    """Model quarterly BTC acquisition over time horizon."""
    cash_deployed = inputs.cash_usd * (inputs.btc_alloc_pct / 100)
    total_capital = cash_deployed + inputs.debt_capacity
    quarterly_deploy = total_capital / (inputs.time_horizon_yrs * 4)

    rows = []
    cumulative_btc = 0
    cumulative_cost = 0

    for q in range(inputs.time_horizon_yrs * 4):
        # BTC price grows at CAGR + noise
        price_at_quarter = inputs.btc_price * ((1 + inputs.btc_cagr_assumption) ** (q / 4))
        btc_acquired = quarterly_deploy / price_at_quarter
        cumulative_btc += btc_acquired
        cumulative_cost += quarterly_deploy

        nav = cumulative_btc * price_at_quarter
        btc_yield = compute_btc_yield(cumulative_btc, inputs.shares_outstanding, price_at_quarter)
        unrealized_gain = nav - cumulative_cost

        rows.append({
            "Quarter": f"Q{(q%4)+1} Y{(q//4)+1}",
            "Q_Index": q,
            "BTC Price": price_at_quarter,
            "BTC Acquired": btc_acquired,
            "Cumulative BTC": cumulative_btc,
            "Capital Deployed ($M)": quarterly_deploy,
            "Cumulative Cost ($M)": cumulative_cost,
            "NAV ($M)": nav / 1e6,
            "Unrealized Gain ($M)": unrealized_gain / 1e6,
            "BTC Yield ($/share)": btc_yield,
            "NAV Premium Factor": nav / (cumulative_cost * 1e6) if cumulative_cost > 0 else 1,
        })

    return pd.DataFrame(rows)


def stress_test(inputs: TreasuryInputs, df: pd.DataFrame) -> pd.DataFrame:
    """Apply historical drawdown scenarios to final NAV."""
    final_btc = df["Cumulative BTC"].iloc[-1]
    final_cost = df["Cumulative Cost ($M)"].iloc[-1] * 1e6
    final_price = df["BTC Price"].iloc[-1]

    rows = []
    for scenario, dd_pct in BTC_DRAWDOWNS.items():
        shocked_price = final_price * (1 + dd_pct / 100)
        shocked_nav = final_btc * shocked_price
        loss_vs_cost = shocked_nav - final_cost
        rows.append({
            "Scenario": scenario,
            "Drawdown": f"{dd_pct}%",
            "BTC Price After": f"${shocked_price:,.0f}",
            "Portfolio NAV ($M)": shocked_nav / 1e6,
            "P&L vs Cost ($M)": loss_vs_cost / 1e6,
            "Solvent": shocked_nav > (inputs.debt_capacity * 1e6 * 1.1),
        })

    return pd.DataFrame(rows)


def dilution_analysis(inputs: TreasuryInputs) -> pd.DataFrame:
    """Model equity dilution from ATM offering to fund BTC purchases."""
    rows = []
    for dilution_pct in [0, 2, 5, 10, 15, 20, 25]:
        new_shares = inputs.shares_outstanding * (1 + dilution_pct / 100)
        capital_raised = (new_shares - inputs.shares_outstanding) * inputs.share_price
        btc_purchased = capital_raised / inputs.btc_price
        btc_yield_before = 0  # baseline zero
        btc_yield_after = compute_btc_yield(btc_purchased, new_shares, inputs.btc_price)
        rows.append({
            "Dilution %": f"{dilution_pct}%",
            "New Shares (M)": new_shares,
            "Capital Raised ($M)": capital_raised / 1e6,
            "BTC Purchased": btc_purchased,
            "BTC/Share": btc_purchased / new_shares,
            "Dilution Worth It": btc_purchased / new_shares > 0.0001,
        })
    return pd.DataFrame(rows)


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ₿ Treasury Config")
    st.markdown("---")

    st.markdown("**Corporate Profile**")
    cash_usd = st.slider("Cash on Balance Sheet ($M)", 100, 50000, 2000, step=100)
    shares_outstanding = st.slider("Shares Outstanding (M)", 1, 5000, 250, step=10)
    share_price = st.slider("Current Share Price ($)", 5, 2000, 85, step=5)
    debt_capacity = st.slider("Debt Capacity for BTC ($M)", 0, 20000, 500, step=100)

    st.markdown("---")
    st.markdown("**BTC Parameters**")
    btc_price = st.slider("Current BTC Price ($)", 30000, 200000, 97000, step=1000)
    btc_alloc_pct = st.slider("% of Cash → BTC", 1, 100, 25, step=1)
    btc_cagr = st.slider("BTC CAGR Assumption (%/yr)", 0, 80, 25, step=5)
    cost_of_debt = st.slider("Cost of Debt (%)", 0.0, 12.0, 3.0, step=0.25)

    st.markdown("---")
    st.markdown("**Horizon**")
    time_horizon = st.slider("Time Horizon (Years)", 1, 10, 4, step=1)

    st.markdown("---")
    st.caption("Mock data prototype. Not financial advice.")

# ── Build inputs & run model ──────────────────────────────────────────────────
inputs = TreasuryInputs(
    cash_usd=cash_usd * 1e6,
    btc_alloc_pct=btc_alloc_pct,
    shares_outstanding=shares_outstanding * 1e6,
    share_price=share_price,
    debt_capacity=debt_capacity * 1e6,
    btc_price=btc_price,
    time_horizon_yrs=time_horizon,
    btc_cagr_assumption=btc_cagr / 100,
    cost_of_debt=cost_of_debt / 100,
)

df = model_acquisition_tranches(inputs)
stress_df = stress_test(inputs, df)
dilution_df = dilution_analysis(inputs)

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div style='padding: 24px 0 8px 0;'>
    <div style='font-size:11px;letter-spacing:0.15em;color:#f7931a;font-weight:600;'>CORPORATE TREASURY INTELLIGENCE</div>
    <div style='font-size:36px;font-weight:700;color:#fff;margin:4px 0;'>BTC Treasury Optimizer</div>
    <div style='font-size:14px;color:#666;'>Model · Stress Test · Optimize acquisition strategy</div>
</div>
""", unsafe_allow_html=True)

st.markdown("---")

# ── KPI Row ───────────────────────────────────────────────────────────────────
final = df.iloc[-1]
total_capital = (cash_usd * btc_alloc_pct / 100) + debt_capacity
final_btc = final["Cumulative BTC"]
final_nav = final["NAV ($M)"]
final_gain = final["Unrealized Gain ($M)"]
moic = final_nav / (total_capital / 1e6) if total_capital > 0 else 1
btc_per_share = final_btc / (shares_outstanding * 1e6)

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.markdown(f"""
    <div class='metric-card'>
        <div class='metric-label'>Total BTC Acquired</div>
        <div class='metric-value'>₿{final_btc:,.1f}</div>
        <div class='metric-sub'>Over {time_horizon}yr horizon</div>
    </div>""", unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class='metric-card'>
        <div class='metric-label'>Portfolio NAV</div>
        <div class='metric-value'>${final_nav:,.0f}M</div>
        <div class='metric-sub'>At terminal BTC price</div>
    </div>""", unsafe_allow_html=True)

with col3:
    gain_class = "positive" if final_gain > 0 else "negative"
    st.markdown(f"""
    <div class='metric-card'>
        <div class='metric-label'>Unrealized Gain</div>
        <div class='metric-value {gain_class}'>${final_gain:,.0f}M</div>
        <div class='metric-sub'>{moic:.2f}x MOIC on deployed capital</div>
    </div>""", unsafe_allow_html=True)

with col4:
    st.markdown(f"""
    <div class='metric-card'>
        <div class='metric-label'>BTC Yield (Saylor KPI)</div>
        <div class='metric-value'>{btc_per_share*1e6:.4f}</div>
        <div class='metric-sub'>BTC per diluted share</div>
    </div>""", unsafe_allow_html=True)

with col5:
    capital_deployed = total_capital / 1e6
    st.markdown(f"""
    <div class='metric-card'>
        <div class='metric-label'>Capital Deployed</div>
        <div class='metric-value'>${capital_deployed:,.0f}M</div>
        <div class='metric-sub'>${cash_usd * btc_alloc_pct / 100:,.0f}M cash + ${debt_capacity:,.0f}M debt</div>
    </div>""", unsafe_allow_html=True)

# ── Main charts ───────────────────────────────────────────────────────────────
st.markdown("<div class='section-header'>Acquisition Model</div>", unsafe_allow_html=True)

col_l, col_r = st.columns(2)

with col_l:
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Scatter(
        x=df["Quarter"], y=df["Cumulative BTC"],
        name="Cumulative BTC", line=dict(color="#f7931a", width=2.5),
        fill="tozeroy", fillcolor="rgba(247,147,26,0.08)"
    ), secondary_y=False)
    fig.add_trace(go.Scatter(
        x=df["Quarter"], y=df["BTC Price"],
        name="BTC Price", line=dict(color="#888", width=1.5, dash="dot"),
    ), secondary_y=True)
    fig.update_layout(
        title="BTC Accumulation vs Price",
        plot_bgcolor="#0d0d0d", paper_bgcolor="#0d0d0d",
        font=dict(color="#888", size=11),
        legend=dict(bgcolor="#111", bordercolor="#222"),
        height=320,
    )
    fig.update_yaxes(title_text="BTC Held", secondary_y=False, gridcolor="#1a1a1a")
    fig.update_yaxes(title_text="BTC Price ($)", secondary_y=True, gridcolor="#1a1a1a")
    fig.update_xaxes(gridcolor="#1a1a1a", tickangle=45, nticks=10)
    st.plotly_chart(fig, use_container_width=True)

with col_r:
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(
        x=df["Quarter"], y=df["NAV ($M)"],
        name="NAV", line=dict(color="#00c853", width=2.5),
        fill="tozeroy", fillcolor="rgba(0,200,83,0.06)"
    ))
    fig2.add_trace(go.Scatter(
        x=df["Quarter"], y=df["Cumulative Cost ($M)"],
        name="Cost Basis", line=dict(color="#ff6b35", width=2, dash="dash"),
    ))
    fig2.update_layout(
        title="NAV vs Cost Basis ($M)",
        plot_bgcolor="#0d0d0d", paper_bgcolor="#0d0d0d",
        font=dict(color="#888", size=11),
        legend=dict(bgcolor="#111", bordercolor="#222"),
        height=320,
    )
    fig2.update_yaxes(gridcolor="#1a1a1a")
    fig2.update_xaxes(gridcolor="#1a1a1a", tickangle=45, nticks=10)
    st.plotly_chart(fig2, use_container_width=True)

# ── BTC Yield over time ───────────────────────────────────────────────────────
st.markdown("<div class='section-header'>BTC Yield — Saylor's Core KPI</div>", unsafe_allow_html=True)

fig3 = go.Figure()
fig3.add_trace(go.Bar(
    x=df["Quarter"], y=df["BTC Yield ($/share)"],
    marker_color="#f7931a", marker_opacity=0.85, name="BTC Yield ($/share)"
))
fig3.update_layout(
    title="BTC Yield per Diluted Share Over Time",
    plot_bgcolor="#0d0d0d", paper_bgcolor="#0d0d0d",
    font=dict(color="#888", size=11),
    height=260,
    showlegend=False,
)
fig3.update_yaxes(gridcolor="#1a1a1a", title="$ BTC Value / Share")
fig3.update_xaxes(gridcolor="#1a1a1a", tickangle=45, nticks=12)
st.plotly_chart(fig3, use_container_width=True)

# ── Stress Test ───────────────────────────────────────────────────────────────
st.markdown("<div class='section-header'>Stress Test — Historical Drawdown Scenarios</div>", unsafe_allow_html=True)

col_s1, col_s2 = st.columns([3, 2])

with col_s1:
    colors = ["#00c853" if s else "#ff1744" for s in stress_df["Solvent"]]
    fig4 = go.Figure(go.Bar(
        x=stress_df["Scenario"],
        y=stress_df["Portfolio NAV ($M)"],
        marker_color=colors,
        text=[f"${v:,.0f}M" for v in stress_df["Portfolio NAV ($M)"]],
        textposition="outside",
    ))
    # Cost basis line
    fig4.add_hline(
        y=total_capital / 1e6,
        line_dash="dot", line_color="#f7931a",
        annotation_text=f"Cost Basis ${total_capital/1e6:,.0f}M",
        annotation_font_color="#f7931a",
    )
    if debt_capacity > 0:
        fig4.add_hline(
            y=debt_capacity / 1e6,
            line_dash="dash", line_color="#ff6b35",
            annotation_text=f"Debt Floor ${debt_capacity/1e6:,.0f}M",
            annotation_font_color="#ff6b35",
        )
    fig4.update_layout(
        title="NAV Under Historical Crash Scenarios",
        plot_bgcolor="#0d0d0d", paper_bgcolor="#0d0d0d",
        font=dict(color="#888", size=11),
        height=320,
        showlegend=False,
    )
    fig4.update_yaxes(gridcolor="#1a1a1a", title="NAV ($M)")
    fig4.update_xaxes(gridcolor="#1a1a1a")
    st.plotly_chart(fig4, use_container_width=True)

with col_s2:
    st.markdown("<br>", unsafe_allow_html=True)
    for _, row in stress_df.iterrows():
        solvent_icon = "✅" if row["Solvent"] else "⚠️"
        pnl_class = "positive" if row["P&L vs Cost ($M)"] > 0 else "negative"
        st.markdown(f"""
        <div class='metric-card' style='padding:12px 16px;'>
            <div style='font-size:12px;font-weight:600;color:#ccc;'>{solvent_icon} {row['Scenario']}</div>
            <div style='font-size:11px;color:#666;margin:2px 0;'>BTC {row['Drawdown']} → {row['BTC Price After']}</div>
            <div style='font-size:13px;' class='{pnl_class}'>
                P&L: ${row['P&L vs Cost ($M)']:,.0f}M
            </div>
        </div>""", unsafe_allow_html=True)

# ── Dilution Analysis ─────────────────────────────────────────────────────────
st.markdown("<div class='section-header'>Dilution Analysis — ATM Equity Tradeoff</div>", unsafe_allow_html=True)

fig5 = make_subplots(specs=[[{"secondary_y": True}]])
fig5.add_trace(go.Bar(
    x=dilution_df["Dilution %"],
    y=dilution_df["BTC Purchased"],
    name="BTC Purchased", marker_color="#f7931a", marker_opacity=0.8,
), secondary_y=False)
fig5.add_trace(go.Scatter(
    x=dilution_df["Dilution %"],
    y=dilution_df["Capital Raised ($M)"],
    name="Capital Raised ($M)", line=dict(color="#00c853", width=2.5),
    mode="lines+markers",
), secondary_y=True)
fig5.update_layout(
    title="BTC Purchased & Capital Raised vs. Equity Dilution",
    plot_bgcolor="#0d0d0d", paper_bgcolor="#0d0d0d",
    font=dict(color="#888", size=11),
    legend=dict(bgcolor="#111", bordercolor="#222"),
    height=300,
)
fig5.update_yaxes(title_text="BTC Purchased", secondary_y=False, gridcolor="#1a1a1a")
fig5.update_yaxes(title_text="Capital Raised ($M)", secondary_y=True, gridcolor="#1a1a1a")
fig5.update_xaxes(gridcolor="#1a1a1a")
st.plotly_chart(fig5, use_container_width=True)

# ── Saylor Insight Box ────────────────────────────────────────────────────────
st.markdown("<div class='section-header'>Strategy Synthesis</div>", unsafe_allow_html=True)

annual_debt_service = (debt_capacity * 1e6 * cost_of_debt / 100) / 1e6
btc_needed_to_service = annual_debt_service * 1e6 / btc_price

col_i1, col_i2 = st.columns(2)
with col_i1:
    st.markdown(f"""
    <div class='insight-box'>
        <strong>BTC Yield Trajectory</strong><br>
        At a {btc_cagr}%/yr BTC CAGR, your {btc_per_share*1e6:.4f} BTC/share KPI grows to
        <strong style='color:#f7931a'>{df.iloc[-1]['BTC Yield ($/share)']:.2f}</strong> $/share by
        year {time_horizon}. This is the metric Saylor prioritizes over EPS or free cash flow.
    </div>
    <div class='insight-box'>
        <strong>Debt Service Coverage</strong><br>
        Annual interest on ${debt_capacity:,.0f}M debt at {cost_of_debt}% = <strong>${annual_debt_service:,.1f}M/yr</strong>.
        Requires selling ≈ <strong>₿{btc_needed_to_service:,.2f}/yr</strong> at current prices to service
        — or {btc_needed_to_service/final_btc*100:.1f}% of total holdings.
    </div>
    """, unsafe_allow_html=True)

with col_i2:
    solvency_count = stress_df["Solvent"].sum()
    solvency_pct = solvency_count / len(stress_df) * 100
    worst_nav = stress_df["Portfolio NAV ($M)"].min()
    st.markdown(f"""
    <div class='insight-box'>
        <strong>Solvency Under Stress</strong><br>
        Portfolio remains above debt floor in
        <strong style='color:{"#00c853" if solvency_pct >= 50 else "#ff1744"}'>{solvency_count}/{len(stress_df)} scenarios</strong>
        ({solvency_pct:.0f}%). Worst-case NAV: <strong>${worst_nav:,.0f}M</strong>.
        {"Consider reducing leverage." if solvency_pct < 50 else "Leverage appears manageable across historical scenarios."}
    </div>
    <div class='insight-box'>
        <strong>Optimal Allocation Signal</strong><br>
        At {btc_alloc_pct}% cash allocation + ${debt_capacity:,.0f}M debt, total capital deployed is
        <strong>${total_capital/1e6:,.0f}M</strong> for <strong>₿{final_btc:,.1f}</strong>.
        {"Increase allocation — BTC CAGR assumption significantly exceeds debt cost." if btc_cagr/100 > cost_of_debt/100 * 2 else "Allocation appears conservative given current parameters."}
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")
st.caption("Prototype · Mock data · CAGR assumptions are illustrative · Not financial advice · Built for MSTR/Strive pitch")

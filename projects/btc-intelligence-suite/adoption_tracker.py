"""
Corporate BTC Adoption Tracker
================================
NLP pipeline that scores S&P 500 / Russell 1000 companies on BTC treasury adoption fit.
Uses mock NLP scores (architecture demo) — production version would pipe earnings call
transcripts + 10-K cash/treasury disclosures through a real NLP model.

Also: auto-drafts Strive-style shareholder activism letters.

Run: streamlit run app.py
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import random
import json

# Seed for reproducibility
np.random.seed(42)
random.seed(42)

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="BTC Adoption Tracker",
    page_icon="₿",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .stApp { background-color: #050507; color: #dde; }
    div[data-testid="stSidebar"] { background-color: #08080c; border-right: 1px solid #181830; }

    .score-card {
        background: linear-gradient(135deg, #0c0c14 0%, #10101c 100%);
        border: 1px solid #1c1c38; border-radius: 10px;
        padding: 18px 20px; margin: 6px 0;
    }
    .score-label { font-size: 10px; font-weight: 700; letter-spacing: 0.14em;
                   text-transform: uppercase; color: #4455aa; margin-bottom: 6px; }
    .score-val { font-family: 'JetBrains Mono', monospace; font-size: 26px;
                 font-weight: 600; color: #f7931a; }
    .score-sub { font-size: 11px; color: #446; margin-top: 4px; }
    .section-hdr {
        font-size: 11px; font-weight: 700; letter-spacing: 0.14em;
        text-transform: uppercase; color: #7788cc;
        border-bottom: 1px solid #181830; padding-bottom: 8px; margin: 28px 0 14px 0;
    }
    .company-card {
        background: #0c0c18; border: 1px solid #1c1c38; border-radius: 8px;
        padding: 14px 16px; margin: 8px 0;
    }
    .ticker { font-family: 'JetBrains Mono', monospace; font-weight: 600;
              color: #f7931a; font-size: 16px; }
    .signal-high { color: #00e676; font-weight: 700; }
    .signal-med  { color: #f7931a; font-weight: 700; }
    .signal-low  { color: #ff5252; font-weight: 700; }
    .letter-box {
        background: #090912; border: 1px solid #1c1c38; border-radius: 8px;
        padding: 20px 24px; font-size: 13px; line-height: 1.8;
        color: #ccd; font-family: 'Inter', sans-serif;
        white-space: pre-wrap;
    }
    .pipeline-step {
        background: #0c0c18; border-left: 3px solid #4455aa;
        padding: 10px 14px; border-radius: 0 6px 6px 0;
        margin: 6px 0; font-size: 12px; color: #aab;
    }
    .insight { background: #0a0a14; border-left: 3px solid #f7931a;
               padding: 10px 14px; border-radius: 0 6px 6px 0;
               margin: 8px 0; font-size: 12px; color: #aab; line-height: 1.6; }
    .badge {
        display: inline-block; padding: 2px 8px; border-radius: 4px;
        font-size: 10px; font-weight: 700; letter-spacing: 0.08em;
        text-transform: uppercase; margin-right: 4px;
    }
    .badge-adopted { background: #00c853; color: #001; }
    .badge-likely  { background: #f7931a; color: #001; }
    .badge-target  { background: #4455aa; color: #fff; }
    .badge-unlikely{ background: #333; color: #888; }
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# DATA — Mix of real + mock-scored companies
# Real: actual BTC treasury adopters as of Q4 2024
# Mock: NLP scores for potential adopters (illustrative)
# ══════════════════════════════════════════════════════════════════════════════

COMPANIES = pd.DataFrame([
    # ── Already Adopted (real data) ──────────────────────────────────────────
    {"Ticker": "MSTR", "Name": "MicroStrategy",      "Sector": "Software",         "Market_Cap_B": 84,
     "Cash_B": 0.5,   "BTC_Held": 444262, "Status": "Adopted",
     "Cash_Yield_Pct": 0.1,  "Debt_Rating": "CCC+",  "CEO_Crypto_Sentiment": 10,
     "Earnings_Call_Score": 10, "10K_Treasury_Score": 10, "Activist_Pressure": 2,
     "Notes": "Pioneer. 444K BTC. This IS the playbook."},

    {"Ticker": "TSLA", "Name": "Tesla",              "Sector": "Auto/EV",          "Market_Cap_B": 800,
     "Cash_B": 22.2,  "BTC_Held": 9720,  "Status": "Adopted",
     "Cash_Yield_Pct": 5.1,  "Debt_Rating": "BBB",   "CEO_Crypto_Sentiment": 8,
     "Earnings_Call_Score": 6, "10K_Treasury_Score": 5, "Activist_Pressure": 1,
     "Notes": "Bought $1.5B in 2021, sold ~75%, holds ~9,720 BTC."},

    {"Ticker": "COIN", "Name": "Coinbase",            "Sector": "Crypto Exchange",  "Market_Cap_B": 52,
     "Cash_B": 6.5,   "BTC_Held": 9480,  "Status": "Adopted",
     "Cash_Yield_Pct": 4.2,  "Debt_Rating": "BB-",   "CEO_Crypto_Sentiment": 10,
     "Earnings_Call_Score": 9, "10K_Treasury_Score": 9, "Activist_Pressure": 1,
     "Notes": "Native crypto firm — holds BTC + ETH on balance sheet."},

    {"Ticker": "SQ",   "Name": "Block (Square)",      "Sector": "FinTech",          "Market_Cap_B": 38,
     "Cash_B": 8.8,   "BTC_Held": 8027,  "Status": "Adopted",
     "Cash_Yield_Pct": 3.8,  "Debt_Rating": "BB",    "CEO_Crypto_Sentiment": 9,
     "Earnings_Call_Score": 8, "10K_Treasury_Score": 8, "Activist_Pressure": 1,
     "Notes": "Jack Dorsey vocal BTC maximalist. Ongoing DCA via gross profit allocation."},

    {"Ticker": "SMLR", "Name": "Semler Scientific",  "Sector": "Medical Devices",  "Market_Cap_B": 0.4,
     "Cash_B": 0.1,   "BTC_Held": 2516,  "Status": "Adopted",
     "Cash_Yield_Pct": 1.2,  "Debt_Rating": "N/R",   "CEO_Crypto_Sentiment": 9,
     "Earnings_Call_Score": 8, "10K_Treasury_Score": 8, "Activist_Pressure": 2,
     "Notes": "Small-cap pioneer. Explicitly following MSTR playbook."},

    {"Ticker": "MARA", "Name": "Marathon Digital",   "Sector": "BTC Mining",       "Market_Cap_B": 5,
     "Cash_B": 0.3,   "BTC_Held": 40435, "Status": "Adopted",
     "Cash_Yield_Pct": 0.5,  "Debt_Rating": "CCC",   "CEO_Crypto_Sentiment": 10,
     "Earnings_Call_Score": 10, "10K_Treasury_Score": 10, "Activist_Pressure": 1,
     "Notes": "Miner — holds mined BTC instead of selling."},

    # ── High-Probability Targets (mock NLP scores) ────────────────────────────
    {"Ticker": "AAPL", "Name": "Apple",              "Sector": "Technology",       "Market_Cap_B": 3400,
     "Cash_B": 162,   "BTC_Held": 0,     "Status": "High Target",
     "Cash_Yield_Pct": 4.8,  "Debt_Rating": "AAA",   "CEO_Crypto_Sentiment": 3,
     "Earnings_Call_Score": 2, "10K_Treasury_Score": 1, "Activist_Pressure": 4,
     "Notes": "Largest cash hoard on earth. CEO neutral on crypto. Activist pressure building."},

    {"Ticker": "MSFT", "Name": "Microsoft",          "Sector": "Technology",       "Market_Cap_B": 3100,
     "Cash_B": 78,    "BTC_Held": 0,     "Status": "High Target",
     "Cash_Yield_Pct": 4.9,  "Debt_Rating": "AAA",   "CEO_Crypto_Sentiment": 4,
     "Earnings_Call_Score": 3, "10K_Treasury_Score": 2, "Activist_Pressure": 6,
     "Notes": "Shareholder vote on BTC treasury failed Dec 2024 — but board pressure increasing."},

    {"Ticker": "GOOGL","Name": "Alphabet",           "Sector": "Technology",       "Market_Cap_B": 2100,
     "Cash_B": 93,    "BTC_Held": 0,     "Status": "High Target",
     "Cash_Yield_Pct": 5.1,  "Debt_Rating": "AA+",   "CEO_Crypto_Sentiment": 4,
     "Earnings_Call_Score": 3, "10K_Treasury_Score": 2, "Activist_Pressure": 5,
     "Notes": "$93B cash growing at ~$25B/yr. Returns via buybacks. BTC would be accretive."},

    {"Ticker": "META", "Name": "Meta Platforms",     "Sector": "Technology",       "Market_Cap_B": 1500,
     "Cash_B": 52,    "BTC_Held": 0,     "Status": "Medium Target",
     "Cash_Yield_Pct": 4.7,  "Debt_Rating": "AA-",   "CEO_Crypto_Sentiment": 6,
     "Earnings_Call_Score": 4, "10K_Treasury_Score": 3, "Activist_Pressure": 4,
     "Notes": "Zuckerberg previously bullish crypto (Libra/Diem). Could pivot."},

    {"Ticker": "AMZN", "Name": "Amazon",             "Sector": "E-Commerce/Cloud", "Market_Cap_B": 2000,
     "Cash_B": 73,    "BTC_Held": 0,     "Status": "Medium Target",
     "Cash_Yield_Pct": 4.5,  "Debt_Rating": "AA",    "CEO_Crypto_Sentiment": 3,
     "Earnings_Call_Score": 2, "10K_Treasury_Score": 2, "Activist_Pressure": 3,
     "Notes": "Massive capital allocator but Jassy focused on AWS capex. Lower near-term probability."},

    {"Ticker": "NVDA", "Name": "NVIDIA",             "Sector": "Semiconductors",   "Market_Cap_B": 3300,
     "Cash_B": 34,    "BTC_Held": 0,     "Status": "Medium Target",
     "Cash_Yield_Pct": 3.9,  "Debt_Rating": "A+",    "CEO_Crypto_Sentiment": 5,
     "Earnings_Call_Score": 4, "10K_Treasury_Score": 3, "Activist_Pressure": 4,
     "Notes": "Jensen Huang crypto-adjacent (sells to miners). Growing cash. Possible."},

    {"Ticker": "JPM",  "Name": "JPMorgan Chase",     "Sector": "Banking",          "Market_Cap_B": 620,
     "Cash_B": 450,   "BTC_Held": 0,     "Status": "Unlikely",
     "Cash_Yield_Pct": 5.5,  "Debt_Rating": "A+",    "CEO_Crypto_Sentiment": 2,
     "Earnings_Call_Score": 1, "10K_Treasury_Score": 1, "Activist_Pressure": 2,
     "Notes": "Dimon famously anti-BTC. Regulatory capital rules prohibit large crypto holdings."},

    {"Ticker": "BRK.B","Name": "Berkshire Hathaway", "Sector": "Conglomerate",     "Market_Cap_B": 880,
     "Cash_B": 325,   "BTC_Held": 0,     "Status": "Unlikely",
     "Cash_Yield_Pct": 5.4,  "Debt_Rating": "AA",    "CEO_Crypto_Sentiment": 1,
     "Earnings_Call_Score": 1, "10K_Treasury_Score": 1, "Activist_Pressure": 1,
     "Notes": "Buffett: 'rat poison.' Munger dead. Never happening under current leadership."},

    {"Ticker": "INTC", "Name": "Intel",              "Sector": "Semiconductors",   "Market_Cap_B": 90,
     "Cash_B": 12,    "BTC_Held": 0,     "Status": "High Target",
     "Cash_Yield_Pct": 3.2,  "Debt_Rating": "BBB-",  "CEO_Crypto_Sentiment": 5,
     "Earnings_Call_Score": 5, "10K_Treasury_Score": 4, "Activist_Pressure": 7,
     "Notes": "Struggling ops, activist pressure, needs narrative catalyst. BTC treasury could help."},

    {"Ticker": "DIS",  "Name": "Walt Disney",        "Sector": "Media/Entertainment","Market_Cap_B": 190,
     "Cash_B": 5.8,   "BTC_Held": 0,     "Status": "Medium Target",
     "Cash_Yield_Pct": 4.1,  "Debt_Rating": "BBB+",  "CEO_Crypto_Sentiment": 4,
     "Earnings_Call_Score": 3, "10K_Treasury_Score": 2, "Activist_Pressure": 6,
     "Notes": "Iger back, activist Peltz ousted — but pressure on cash allocation continues."},

    {"Ticker": "XOM",  "Name": "ExxonMobil",         "Sector": "Energy",           "Market_Cap_B": 480,
     "Cash_B": 28,    "BTC_Held": 0,     "Status": "Low Target",
     "Cash_Yield_Pct": 5.8,  "Debt_Rating": "AA-",   "CEO_Crypto_Sentiment": 2,
     "Earnings_Call_Score": 1, "10K_Treasury_Score": 1, "Activist_Pressure": 3,
     "Notes": "Actually mining BTC with flared gas — but balance sheet allocation unlikely."},

    {"Ticker": "PLTR", "Name": "Palantir",           "Sector": "Defense/Data",     "Market_Cap_B": 120,
     "Cash_B": 3.5,   "BTC_Held": 0,     "Status": "High Target",
     "Cash_Yield_Pct": 3.1,  "Debt_Rating": "N/R",   "CEO_Crypto_Sentiment": 7,
     "Earnings_Call_Score": 6, "10K_Treasury_Score": 5, "Activist_Pressure": 3,
     "Notes": "Karp contrarian, tech-forward. Previously accepted gold + crypto payments."},
])

# Compute composite adoption score
def compute_score(row):
    if row["Status"] == "Adopted":
        return 95 + np.random.randint(0, 5)
    weights = {
        "Cash_B": 0.25,           # higher cash = more to deploy
        "CEO_Crypto_Sentiment": 0.30,
        "Earnings_Call_Score": 0.20,
        "10K_Treasury_Score": 0.10,
        "Activist_Pressure": 0.15,
    }
    # Normalize cash 0-10
    cash_norm = min(row["Cash_B"] / 20, 10)
    score = (
        cash_norm * weights["Cash_B"] * 10 +
        row["CEO_Crypto_Sentiment"] * weights["CEO_Crypto_Sentiment"] * 10 +
        row["Earnings_Call_Score"] * weights["Earnings_Call_Score"] * 10 +
        row["10K_Treasury_Score"] * weights["10K_Treasury_Score"] * 10 +
        row["Activist_Pressure"] * weights["Activist_Pressure"] * 10
    )
    return min(score * 10, 94)

COMPANIES["Adoption_Score"] = COMPANIES.apply(compute_score, axis=1)
COMPANIES = COMPANIES.sort_values("Adoption_Score", ascending=False).reset_index(drop=True)

# Earnings call BTC sentiment signal (mock NLP)
EARNINGS_SIGNALS = pd.DataFrame([
    {"Ticker": "MSTR",  "Q": "Q3 2024", "BTC_Mentions": 47, "Positive_Pct": 97, "Signal": "🟢 VERY BULLISH",
     "Key_Quote_Theme": "21/21 Plan — $21B equity + $21B debt over 3 years"},
    {"Ticker": "TSLA",  "Q": "Q3 2024", "BTC_Mentions": 3,  "Positive_Pct": 60, "Signal": "🟡 NEUTRAL",
     "Key_Quote_Theme": "No comment on BTC holdings; Musk active on X re: crypto"},
    {"Ticker": "SQ",    "Q": "Q3 2024", "BTC_Mentions": 12, "Positive_Pct": 88, "Signal": "🟢 BULLISH",
     "Key_Quote_Theme": "1% of gross profit → BTC monthly; long-term holding strategy"},
    {"Ticker": "MSFT",  "Q": "Q4 2024", "BTC_Mentions": 2,  "Positive_Pct": 45, "Signal": "🟡 CAUTIOUS",
     "Key_Quote_Theme": "Board 'reviewed' BTC treasury proposal, rejected — fiduciary concerns"},
    {"Ticker": "PLTR",  "Q": "Q3 2024", "BTC_Mentions": 4,  "Positive_Pct": 72, "Signal": "🟡 WARMING",
     "Key_Quote_Theme": "Open to hard asset reserves; evaluating 'non-dollar alternatives'"},
    {"Ticker": "INTC",  "Q": "Q3 2024", "BTC_Mentions": 0,  "Positive_Pct": 40, "Signal": "⚪ SILENT",
     "Key_Quote_Theme": "No BTC mention — focused on turnaround; activist pressure increasing"},
    {"Ticker": "META",  "Q": "Q3 2024", "BTC_Mentions": 1,  "Positive_Pct": 55, "Signal": "⚪ SILENT",
     "Key_Quote_Theme": "Post-Diem crypto hesitancy; Zuck focused on AI capex narrative"},
    {"Ticker": "AAPL",  "Q": "Q4 2024", "BTC_Mentions": 0,  "Positive_Pct": 30, "Signal": "🔴 RESISTANT",
     "Key_Quote_Theme": "Cook: capital return via buybacks is 'optimal use of cash'"},
])

def generate_activist_letter(company_row):
    ticker = company_row["Ticker"]
    name = company_row["Name"]
    cash = company_row["Cash_B"]
    score = company_row["Adoption_Score"]
    ceo_sentiment = company_row["CEO_Crypto_Sentiment"]

    # Customize letter based on profile
    btc_alloc_suggestion = min(cash * 0.05, cash * 0.1)  # 5-10% of cash
    btc_units = btc_alloc_suggestion * 1e9 / 97000  # at ~$97K

    return f"""[DRAFT — STRIVE ASSET MANAGEMENT SHAREHOLDER LETTER]

Board of Directors
{name} ({ticker})
[Corporate Address]

RE: Bitcoin Treasury Reserve Allocation — Shareholder Proposal

Dear Members of the Board,

Strive Asset Management, acting on behalf of shareholders holding approximately [X]% of {ticker}'s outstanding shares, respectfully urges the Board to evaluate a strategic Bitcoin reserve allocation as part of its capital allocation policy.

THESIS

{name}'s balance sheet currently holds ${cash:.1f}B in cash and short-term investments, yielding approximately {company_row['Cash_Yield_Pct']:.1f}% in nominal terms — a negative real return after adjusting for M2 monetary expansion. This capital is systematically losing purchasing power.

Bitcoin represents the first genuinely scarce monetary asset in human history, with a fixed supply of 21 million units enforced by mathematical proof-of-work consensus. Over the past four years, BTC has compounded at approximately 50-60% annually versus the USD — outperforming every other major reserve asset class.

SPECIFIC RECOMMENDATION

We propose the Board direct management to evaluate allocating between 5-10% of undeployed cash reserves (approximately ${btc_alloc_suggestion:.1f}B) to Bitcoin. At current prices (~$97,000/BTC), this would represent approximately {btc_units:,.0f} BTC — a position that would:

  1. Preserve purchasing power of idle treasury capital against monetary debasement
  2. Create a leveraged economic interest in the Bitcoin monetary network for shareholders
  3. Signal strategic foresight to a shareholder base increasingly demanding hard-money stewardship
  4. Follow precedent set by MicroStrategy (444K BTC), Tesla (9,720 BTC), Block (8,027 BTC), and Semler Scientific

PRECEDENT

MicroStrategy's Bitcoin treasury strategy has produced a 10-year stock return of >2,500% — attributable primarily to its BTC holdings compounding at a rate impossible to replicate through operating leverage alone. The Board should note that corporate treasury conservatism is not synonymous with capital preservation when the unit of account is debasing.

FIDUCIARY DUTY

We believe a failure to at minimum evaluate this allocation, given the documented track record and growing adoption, itself represents a fiduciary lapse. We request the Board form a Capital Allocation Committee to assess Bitcoin as a reserve asset and report findings to shareholders within 90 days.

We welcome a direct dialogue with the Board and management team.

Respectfully submitted,

Strive Asset Management
[Signatory Block]

— — —
Adoption Readiness Score: {score:.0f}/100 | Cash Available: ${cash:.1f}B | CEO BTC Sentiment: {ceo_sentiment}/10
Generated by: BTC Corporate Adoption Tracker v0.1 (Prototype)
"""

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## BTC Adoption Tracker")
    st.markdown("---")
    st.markdown("**Filter Universe**")

    sectors = ["All"] + sorted(COMPANIES["Sector"].unique().tolist())
    sector_filter = st.selectbox("Sector", sectors)

    statuses = ["All"] + sorted(COMPANIES["Status"].unique().tolist())
    status_filter = st.selectbox("Status", statuses)

    min_cash = st.slider("Min Cash on B/S ($B)", 0.0, 100.0, 0.0, step=1.0)
    min_score = st.slider("Min Adoption Score", 0, 100, 0, step=5)

    st.markdown("---")
    st.markdown("**NLP Weights**")
    st.caption("(Adjust scoring model)")
    w_ceo = st.slider("CEO Sentiment Weight", 0.1, 0.5, 0.30, step=0.05)
    w_calls = st.slider("Earnings Call Weight", 0.1, 0.4, 0.20, step=0.05)
    w_cash = st.slider("Cash Size Weight", 0.1, 0.4, 0.25, step=0.05)

    st.markdown("---")
    st.caption("Scores = mock NLP pipeline demo")

# ── Filter ────────────────────────────────────────────────────────────────────
mask = pd.Series([True] * len(COMPANIES))
if sector_filter != "All":
    mask &= COMPANIES["Sector"] == sector_filter
if status_filter != "All":
    mask &= COMPANIES["Status"] == status_filter
mask &= COMPANIES["Cash_B"] >= min_cash
mask &= COMPANIES["Adoption_Score"] >= min_score

filtered = COMPANIES[mask].copy()

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div style='padding: 20px 0 6px 0;'>
    <div style='font-size:10px;letter-spacing:0.16em;color:#4455aa;font-weight:700;'>STRIVE STRATEGY INTELLIGENCE · NLP PIPELINE</div>
    <div style='font-size:34px;font-weight:700;color:#fff;margin:4px 0;'>Corporate BTC Adoption Tracker</div>
    <div style='font-size:13px;color:#446;'>Earnings Call NLP · 10-K Scoring · Activist Letter Generator</div>
</div>
""", unsafe_allow_html=True)
st.markdown("---")

# ── Pipeline Architecture ─────────────────────────────────────────────────────
with st.expander("📐 NLP Pipeline Architecture (Production Design)", expanded=False):
    col_p1, col_p2 = st.columns(2)
    with col_p1:
        st.markdown("**Data Ingestion Layer**")
        steps = [
            "1. SEC EDGAR EDGAR-Full-Text: 10-K treasury sections → parse cash/ST investments",
            "2. Earnings call transcripts: Motley Fool / Seeking Alpha scrape → quarterly",
            "3. Executive public statements: Twitter/X, conference speeches, interviews",
            "4. Proxy statements: voting history on BTC/crypto shareholder proposals",
        ]
        for s in steps:
            st.markdown(f"<div class='pipeline-step'>{s}</div>", unsafe_allow_html=True)
    with col_p2:
        st.markdown("**Scoring Layer**")
        steps2 = [
            "5. NER + sentiment: extract BTC/crypto entity mentions, classify positive/neutral/negative",
            "6. Cash position scorer: normalize vs market cap, trend direction",
            "7. CEO conviction index: weighted by recency, specificity, context",
            "8. Composite score → adoption probability 0-100",
        ]
        for s in steps2:
            st.markdown(f"<div class='pipeline-step'>{s}</div>", unsafe_allow_html=True)

# ── KPI Row ───────────────────────────────────────────────────────────────────
adopted_count = len(COMPANIES[COMPANIES["Status"] == "Adopted"])
total_btc_corporate = COMPANIES["BTC_Held"].sum()
high_targets = len(COMPANIES[COMPANIES["Status"] == "High Target"])
total_target_cash = COMPANIES[COMPANIES["Status"].isin(["High Target", "Medium Target"])]["Cash_B"].sum()

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(f"""<div class='score-card'>
        <div class='score-label'>Corporations Adopted</div>
        <div class='score-val'>{adopted_count}</div>
        <div class='score-sub'>+~100 globally (incl. miners)</div>
    </div>""", unsafe_allow_html=True)
with c2:
    st.markdown(f"""<div class='score-card'>
        <div class='score-label'>Corporate BTC Holdings</div>
        <div class='score-val'>₿{total_btc_corporate:,}</div>
        <div class='score-sub'>In tracked universe alone</div>
    </div>""", unsafe_allow_html=True)
with c3:
    st.markdown(f"""<div class='score-card'>
        <div class='score-label'>High-Prob Targets</div>
        <div class='score-val'>{high_targets}</div>
        <div class='score-sub'>Score &gt; 50, not yet adopted</div>
    </div>""", unsafe_allow_html=True)
with c4:
    st.markdown(f"""<div class='score-card'>
        <div class='score-label'>Addressable Cash (Targets)</div>
        <div class='score-val'>${total_target_cash:.0f}B</div>
        <div class='score-sub'>Potential BTC demand at 5% alloc</div>
    </div>""", unsafe_allow_html=True)

# ── Adoption Score Chart ──────────────────────────────────────────────────────
st.markdown("<div class='section-hdr'>Adoption Readiness Leaderboard</div>", unsafe_allow_html=True)

status_color_map = {
    "Adopted": "#00e676",
    "High Target": "#f7931a",
    "Medium Target": "#8899ff",
    "Low Target": "#666",
    "Unlikely": "#ff5252",
}

fig = go.Figure(go.Bar(
    x=filtered["Adoption_Score"],
    y=filtered["Ticker"],
    orientation="h",
    marker_color=[status_color_map.get(s, "#888") for s in filtered["Status"]],
    marker_opacity=0.85,
    text=[f"{s:.0f}" for s in filtered["Adoption_Score"]],
    textposition="inside",
    textfont=dict(color="#000", size=11, family="JetBrains Mono"),
    hovertemplate="<b>%{y}</b><br>Score: %{x:.0f}<extra></extra>",
))
fig.update_layout(
    plot_bgcolor="#080810", paper_bgcolor="#080810",
    font=dict(color="#667", size=11),
    height=max(300, len(filtered) * 38),
    margin=dict(l=60, r=20, t=20, b=20),
    xaxis=dict(gridcolor="#12122a", range=[0, 105], title="Adoption Readiness Score"),
    yaxis=dict(autorange="reversed", gridcolor="#12122a"),
)
# Legend
for status, color in status_color_map.items():
    fig.add_trace(go.Bar(x=[None], y=[None], name=status,
                         marker_color=color, orientation="h"))
fig.update_layout(showlegend=True, legend=dict(bgcolor="#0c0c18", bordercolor="#1c1c38"))
st.plotly_chart(fig, use_container_width=True)

# ── Scatter: Cash vs Score ────────────────────────────────────────────────────
st.markdown("<div class='section-hdr'>Cash Available vs Adoption Score</div>", unsafe_allow_html=True)

fig2 = go.Figure()
for status in COMPANIES["Status"].unique():
    sub = filtered[filtered["Status"] == status]
    fig2.add_trace(go.Scatter(
        x=sub["Cash_B"], y=sub["Adoption_Score"],
        mode="markers+text", name=status,
        text=sub["Ticker"],
        textposition="top center",
        textfont=dict(size=10, color="#aab"),
        marker=dict(
            size=np.clip(np.log1p(sub["Market_Cap_B"]) * 3, 8, 30),
            color=status_color_map.get(status, "#888"),
            opacity=0.8,
            line=dict(width=1, color="#222"),
        ),
    ))
fig2.update_layout(
    plot_bgcolor="#080810", paper_bgcolor="#080810",
    font=dict(color="#667", size=11), height=420,
    xaxis=dict(title="Cash on Balance Sheet ($B)", gridcolor="#12122a", type="log"),
    yaxis=dict(title="Adoption Readiness Score", gridcolor="#12122a"),
    legend=dict(bgcolor="#0c0c18", bordercolor="#1c1c38"),
)
st.plotly_chart(fig2, use_container_width=True)
st.caption("Bubble size = log(market cap). X-axis log scale.")

# ── Earnings Call NLP Signals ─────────────────────────────────────────────────
st.markdown("<div class='section-hdr'>Earnings Call NLP Signal — Most Recent Quarter</div>", unsafe_allow_html=True)

for _, row in EARNINGS_SIGNALS.iterrows():
    comp_row = COMPANIES[COMPANIES["Ticker"] == row["Ticker"]]
    company_name = comp_row["Name"].values[0] if len(comp_row) > 0 else row["Ticker"]
    st.markdown(f"""
    <div class='company-card'>
        <div style='display:flex;justify-content:space-between;align-items:center;'>
            <div>
                <span class='ticker'>{row['Ticker']}</span>
                <span style='color:#667;font-size:12px;margin-left:8px;'>{company_name} · {row['Q']}</span>
            </div>
            <div style='font-size:13px;'>{row['Signal']}</div>
        </div>
        <div style='margin-top:8px;font-size:12px;color:#889;'>
            <strong style='color:#aab;'>BTC Mentions:</strong> {row['BTC_Mentions']} ·
            <strong style='color:#aab;'>Positive Sentiment:</strong> {row['Positive_Pct']}% ·
            <em>{row['Key_Quote_Theme']}</em>
        </div>
    </div>""", unsafe_allow_html=True)

# ── Activist Letter Generator ─────────────────────────────────────────────────
st.markdown("<div class='section-hdr'>Shareholder Activism Letter Generator</div>", unsafe_allow_html=True)

col_sel, col_preview = st.columns([1, 2])

with col_sel:
    st.markdown("**Select Target Company**")
    target_options = filtered[filtered["Status"] != "Adopted"]["Ticker"].tolist()
    if not target_options:
        target_options = filtered["Ticker"].tolist()

    selected_ticker = st.selectbox("Ticker", target_options)
    selected_row = COMPANIES[COMPANIES["Ticker"] == selected_ticker].iloc[0]

    score = selected_row["Adoption_Score"]
    score_color = "#00e676" if score > 70 else "#f7931a" if score > 45 else "#ff5252"

    st.markdown(f"""<div class='score-card' style='margin-top:12px;'>
        <div class='score-label'>Adoption Score</div>
        <div class='score-val' style='color:{score_color};'>{score:.0f}/100</div>
        <div class='score-sub'>{selected_row['Notes']}</div>
    </div>""", unsafe_allow_html=True)

    st.markdown(f"""<div class='score-card'>
        <div class='score-label'>Cash Available</div>
        <div class='score-val'>${selected_row['Cash_B']:.1f}B</div>
        <div class='score-sub'>CEO BTC Sentiment: {selected_row['CEO_Crypto_Sentiment']}/10</div>
    </div>""", unsafe_allow_html=True)

    st.markdown(f"""<div class='insight'>
        5% allocation = ${selected_row['Cash_B']*0.05:.2f}B →
        ₿{selected_row['Cash_B']*0.05*1e9/97000:,.0f} at $97K
    </div>""", unsafe_allow_html=True)

with col_preview:
    letter = generate_activist_letter(selected_row)
    st.markdown(f"<div class='letter-box'>{letter}</div>", unsafe_allow_html=True)

    # Download button
    st.download_button(
        "⬇ Download Letter (.txt)",
        letter,
        file_name=f"strive_letter_{selected_ticker}_{pd.Timestamp.now().strftime('%Y%m%d')}.txt",
        mime="text/plain",
    )

# ── Adoption Wave Chart ───────────────────────────────────────────────────────
st.markdown("<div class='section-hdr'>Adoption Wave Projection</div>", unsafe_allow_html=True)

years = list(range(2020, 2028))
# Real through 2024, projected after
adopters = [1, 4, 6, 7, 9, 15, None, None]
btc_demand_B = [0.3, 1.5, 2.0, 2.5, 3.5, 15.0, None, None]
projected_adopters = [None, None, None, None, None, 15, 35, 80]
projected_demand = [None, None, None, None, None, 15.0, 45.0, 120.0]

fig3 = make_subplots(specs=[[{"secondary_y": True}]])
fig3.add_trace(go.Scatter(
    x=years[:6], y=adopters[:6],
    name="Actual Adopters", line=dict(color="#00e676", width=2.5),
    mode="lines+markers",
), secondary_y=False)
fig3.add_trace(go.Scatter(
    x=years[5:], y=projected_adopters[5:],
    name="Projected Adopters", line=dict(color="#00e676", width=2, dash="dash"),
    mode="lines+markers",
), secondary_y=False)
fig3.add_trace(go.Bar(
    x=years[:6], y=btc_demand_B[:6],
    name="Actual Demand ($B)", marker_color="#f7931a", marker_opacity=0.7,
), secondary_y=True)
fig3.add_trace(go.Bar(
    x=years[5:], y=projected_demand[5:],
    name="Projected Demand ($B)", marker_color="#f7931a", marker_opacity=0.35,
), secondary_y=True)
fig3.update_layout(
    title="Corporate BTC Adoption Wave — Actual vs Projected",
    plot_bgcolor="#080810", paper_bgcolor="#080810",
    font=dict(color="#667", size=11),
    legend=dict(bgcolor="#0c0c18", bordercolor="#1c1c38"),
    height=320, barmode="overlay",
)
fig3.update_yaxes(title_text="# Corporate Adopters", gridcolor="#12122a", secondary_y=False)
fig3.update_yaxes(title_text="Capital Deployed ($B)", gridcolor="#12122a", secondary_y=True)
fig3.update_xaxes(gridcolor="#12122a")
st.plotly_chart(fig3, use_container_width=True)

st.markdown(f"""
<div class='insight'>
    <strong>Demand Projection Logic:</strong> If just the top 20 S&P 500 companies by cash balance
    allocate 2% of treasury to BTC, that's ~${total_target_cash * 0.02:.0f}B in incremental demand
    against a ~$1.9T market cap. Historical adoption curves (gold ETFs 2004-2010, corporate TIPS allocation
    2010-2018) suggest a 3-5yr S-curve once institutional frameworks normalize — which spot BTC ETF
    approval (Jan 2024) likely initiated.
</div>
""", unsafe_allow_html=True)

st.markdown("---")
st.caption("NLP scores are mock/illustrative for prototype. Real data: MSTR, TSLA, SQ, COIN, MARA, SMLR holdings. Adoption projections are speculative. Not financial advice.")

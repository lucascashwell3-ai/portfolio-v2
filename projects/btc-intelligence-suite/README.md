# BTC Intelligence Suite
### Built for MSTR / Strive portfolio

Three Streamlit prototypes demonstrating AI-powered Bitcoin treasury intelligence tools.

---

## Quick Start (any app)

```bash
cd <app_folder>
pip install -r requirements.txt
streamlit run app.py
```

---

## App 1: BTC Treasury Optimizer (`/treasury_optimizer`)

**Pitch:** Interactive model for optimal BTC acquisition strategy for any corporate treasury.

**What it does:**
- Models quarterly BTC accumulation over 1-10yr horizon
- Replicates Saylor's "BTC Yield" KPI (BTC per diluted share) — the metric MSTR publishes quarterly
- Stress-tests portfolio against all historical BTC drawdowns (2011 crash -93%, 2022 bear -77%, etc.)
- Models dilution tradeoff: how much equity dilution is worth it for how much BTC?
- Separates capital sources: cash vs. ATM equity vs. convertible debt

**Key insight it surfaces:** At what BTC price does the portfolio become insolvent given current debt? At what dilution level does each new share still increase BTC/share?

**Target audience:** CFOs, treasury teams, institutional investors evaluating the Saylor playbook for their own balance sheet.

---

## App 2: MSTR Convertible Bond Decoder (`/convertible_decoder`)

**Pitch:** Full decomposition of MicroStrategy's actual capital structure using real public filing data.

**What it does:**
- Displays all 7 convertible note tranches with coupon, conversion premium, conversion price, status
- Real-time NAV calculation: adjustable BTC price → instant equity NAV, premium/discount to market cap
- Historical NAV premium chart: MSTR vs BTC NAV/share since Aug 2020
- Arbitrage signal: current premium vs historical range
- All 23 BTC acquisition tranches with source (cash/convertible/ATM equity), BTC price paid, total capital
- DCA analysis: blended average cost basis, unrealized gain vs current price
- Capital source breakdown: 57% ATM equity, 28% convertible notes, 15% cash

**Data:** All MSTR figures are real, sourced from public 8-K filings, 10-Q/10-K, and press releases.

**Key insight:** MSTR's "BTC treasury company" model works because it can raise equity at a premium to NAV — each share issued above NAV is immediately BTC-accretive on a per-share basis. The CB decoder makes this mechanical relationship visible.

---

## App 3: Corporate BTC Adoption Tracker (`/adoption_tracker`)

**Pitch:** NLP pipeline that scores S&P 500 companies on BTC treasury adoption probability + auto-drafts Strive-style activist letters.

**What it does:**
- Scores 18 companies (6 adopted, 12 targets) on adoption readiness (0-100)
- Scoring factors: CEO crypto sentiment, earnings call BTC mentions, cash size, debt rating, activist pressure
- Earnings call NLP signal panel: BTC mention count, positive sentiment %, key theme per company
- Interactive scatter: cash available vs adoption score, bubble size = market cap
- Adoption wave projection: actual adopters 2020-2024, projected S-curve 2025-2027
- **Activist Letter Generator:** select any target company → generates full Strive-style shareholder letter with company-specific data (cash position, 5% allocation suggestion, BTC units, precedent section)
- Download letter as .txt

**Production extension:** Replace mock NLP scores with real pipeline: SEC EDGAR full-text search → earnings call transcript scrape → Claude API sentiment classification → live scoring.

**Key insight:** If the top 20 S&P 500 companies by cash balance allocate just 2% of treasury, that's ~$75B+ in incremental BTC demand — against a ~$1.9T total market cap. The adoption tracker makes this pipeline legible.

---

## Architecture Notes

| App | Data | NLP | Live feeds |
|-----|------|-----|-----------|
| Treasury Optimizer | Mock (parametric) | N/A | No — slider-driven |
| Convertible Decoder | **Real** (MSTR public filings) | N/A | BTC price / MSTR price manual input |
| Adoption Tracker | Mixed (real adopters, mock scores) | Mock pipeline shown | Extend with EDGAR + transcripts |

### Production Extensions (not built in prototype)
- EDGAR full-text search → auto-parse cash positions from 10-K
- Earnings transcript API (Motley Fool, Seeking Alpha, or Refinitiv) → real NLP
- CoinGecko / Coinbase API → live BTC price feed
- MSTR real-time NAV → auto-refresh every 15min
- Email/Slack alert when adoption score crosses threshold

---

## Why These Tools Signal Fit

- **Treasury Optimizer** → Shows you've internalized the Saylor playbook mechanically, not just directionally
- **Convertible Decoder** → Demonstrates ability to read capital structure filings and model NAV dynamics — relevant to MSTR's actual investor relations + strategy function
- **Adoption Tracker** → Directly replicates Strive's core business: identify targets, generate activist materials, track progress

All three speak in MSTR/Strive's native vocabulary: BTC Yield, NAV premium, hard money reserve, monetary debasement, 21/21 Plan.

# Phase Completion Criteria

A phase is done when all criteria are met — not when the code runs.

---

## Phase 0 — Universe Construction

- [ ] Master ticker table exists with all required fields: `ticker`, `exchange`, `adr_ticker`, `adr_exchange`, `sector`, `market_cap_usd`
- [ ] TWSE/TPEx top 200 by market cap populated (source: FinMind)
- [ ] S&P 500 constituents populated (source: Wikipedia / yfinance)
- [ ] ADR mapping complete for dual-listed Taiwan names (~10 companies)
- [ ] No duplicate nodes — each company appears exactly once with `.TW` as canonical if dual-listed
- [ ] Saved to `data/processed/universe.csv`
- [ ] **Sanity check:** spot-verify 10 random tickers against known data (TSMC = `2330.TW`, Apple = `AAPL`, etc.)

---

## Phase 1 — Graph Construction

- [ ] Tier 1 edges extracted from SEC EDGAR 10-K and 20-F filings (2015–2024)
- [ ] Tier 2 edges extracted from Risk Factor text via NLP
- [ ] Entity resolution applied — all company names mapped to canonical tickers
- [ ] Edge schema complete: `source`, `target`, `weight`, `source_filing`, `year`, `tier`
- [ ] Temporal edges indexed by filing year — no cross-year edge contamination
- [ ] **Look-ahead audit:** confirm no edge uses a filing date after the year it applies to
- [ ] **Degree distribution documented:** plot and record min/mean/median/max degree across nodes
- [ ] **Gate check:** mean degree ≥ 3 across the universe; if not, document and reassess before Phase 3
- [ ] Saved to `data/graphs/`

---

## Phase 2 — Feature Engineering

- [ ] All node features computed per company per quarter: revenue growth, gross margin, inventory days, capex/revenue, customer concentration, geo revenue mix, price momentum (1m/3m/12m), realized volatility (60d)
- [ ] Edge features computed: revenue dependency weight, data tier, relationship age
- [ ] Missing data policy documented and applied consistently (not decided ad hoc per feature)
- [ ] **No forward-looking features:** all features use only information available as of quarter-end
- [ ] Feature correlation matrix reviewed — no feature pair with |r| > 0.95 (would indicate duplication)
- [ ] Saved to `data/processed/features/`

---

## Phase 3 — GNN Training

- [ ] Baseline run complete: static graph + linear model with IC documented (this is H5 gate)
- [ ] **IC gate:** baseline IC > 0 in training period before proceeding to GNN
- [ ] GAT model trains without divergence on 2015–2020 training set
- [ ] Validation IC (2021) is positive and within reasonable range of training IC (no severe overfitting)
- [ ] Multi-task loss α tuned on validation set
- [ ] Model checkpoint saved with config and random seed for reproducibility
- [ ] Training curve (loss, IC by epoch) saved to `notebooks/`

---

## Phase 4 — Signal Construction

- [ ] Stress propagation score computed for all nodes, all quarters
- [ ] Neighborhood return momentum score computed
- [ ] Bottleneck centrality delta computed
- [ ] Combined signal (GNN features + price factors) via ridge regression and LightGBM
- [ ] **IC computed on out-of-sample period (2022–2024)** for all signal variants
- [ ] Graph ablation run: IC with vs. without edges documented
- [ ] Tier ablation run: IC with Tier 1 only vs. Tier 1+2+3 documented
- [ ] Signal documented in `notebooks/` with IC table

---

## Phase 5 — Backtest & Validation

- [ ] Walk-forward backtest complete: 2022–2024 out-of-sample
- [ ] All target metrics computed: IC, ICIR, annual return, max drawdown, Sharpe ratio
- [ ] Separate results for TW-only, US-only, and cross-market signal
- [ ] Cross-market asymmetry test run (H4)
- [ ] Temporal ablation: static vs. temporal graph performance compared
- [ ] Transaction costs applied correctly: 0.1% US, 0.3% TW one-way
- [ ] Short-selling feasibility confirmed for TW leg (or long-only variant documented)
- [ ] **Regime test:** pre-2020 and post-2020 performance reported separately
- [ ] Results written up in `notebooks/backtest_results.ipynb`

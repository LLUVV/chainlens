# chainlens

Supply chain graph neural network for cross-market stock alpha — Taiwan (TWSE/TPEx) + US (NYSE/NASDAQ).

The core thesis: supply chain shocks propagate through company networks before stock prices reflect them. A GNN trained on the supplier→customer graph can front-run second- and third-order effects.

---

## Research Pipeline

```
Phase 0  Universe        → define tradeable node list (TW + US)
Phase 1  Graph           → construct supply chain graph (nodes + edges)
Phase 2  Features        → company fundamentals as node features
Phase 3  Model           → GNN training + embedding extraction
Phase 4  Signal          → alpha construction from embeddings + price
Phase 5  Backtest        → walk-forward validation, IC/ICIR, returns
```

---

## Phase 0 — Universe Construction

**Goal:** a master ticker table — every tradeable node with metadata.

| Field | Description |
|---|---|
| `ticker` | Canonical trading ticker (`2330.TW`, `AAPL`) |
| `exchange` | `TWSE`, `TPEx`, `NYSE`, `NASDAQ` |
| `adr_ticker` | US ADR ticker if dual-listed (e.g., `TSM` for `2330.TW`) |
| `adr_exchange` | `NYSE` / `NASDAQ` if applicable |
| `sector` | GICS sector |
| `market_cap_usd` | For filtering liquidity |

**Sources:**
- Taiwan: FinMind API → TWSE/TPEx top 200 by market cap
- US: S&P 500 constituent list (Wikipedia / yfinance)
- ADR mapping: hardcoded for ~10 dual-listed Taiwan names (TSMC, UMC, ASE, AUO, CHT, HIMX, IMOS…)

**Key rule:** if a company has both a `.TW` ticker and a US ADR, the `.TW` ticker is the canonical trading node. The ADR is used only as a data source for SEC filings.

---

## Phase 1 — Graph Construction

### 1a. Edge Extraction — Supply Chain Relationships

Edges are directed: `supplier → customer`.

**Tier 1 — Structured, quantified (best quality)**

Source: SEC EDGAR 10-K (US companies) and 20-F (Taiwan ADRs)

SEC regulations require disclosure of any customer representing >10% of revenue. This produces edges with a numeric weight (revenue share %).

```
TSMC 20-F:  "Apple Inc. accounted for ~25% of net revenue"
            → edge: 2330.TW → AAPL, weight=0.25
```

Tools: `edgartools` (Python, MIT), SEC EDGAR bulk download API

**Tier 2 — Named, unquantified**

Source: Item 1A Risk Factors text in 10-K / 20-F

Companies name key suppliers/customers in risk disclosures without percentages. NLP entity extraction recovers these as binary edges.

```
Apple 10-K: "We rely on TSMC as our primary chip manufacturer..."
            → edge: 2330.TW → AAPL, weight=null
```

Tools: spaCy or LLM-based entity extraction, company name → ticker resolution

**Tier 3 — Inferred from Taiwan filings**

Source: MOPS annual reports (unstructured, mostly Chinese text)

For Taiwan-only companies not covered by Tier 1/2. Requires NLP on Chinese text.

Tools: FinMind + custom NLP pipeline

### 1b. Entity Resolution

Raw text names (`"Taiwan Semiconductor Manufacturing"`, `"TSMC"`, `"台積電"`) must be mapped to canonical tickers. Strategy:
1. Fuzzy match against universe ticker + company name table
2. Alias dictionary for common variants
3. Manual review for ambiguous cases

### 1c. Graph Schema

```python
Node {
    id:                  str      # canonical ticker
    exchange:            str
    adr_ticker:          str | None
    # features added in Phase 2
}

Edge {
    source:              str      # supplier ticker
    target:              str      # customer ticker
    weight:              float | None  # revenue share, null if unquantified
    source_filing:       str      # e.g. "AAPL 10-K 2023"
    year:                int      # filing year (for temporal graph)
    tier:                int      # 1/2/3 data quality
}
```

### 1d. Temporal Graph

Edges are extracted per filing year, creating a time-indexed graph. A 2018 supply relationship may not exist in 2023. The temporal dimension is critical for avoiding look-ahead bias in training.

---

## Phase 2 — Feature Engineering

### Node Features (per company, per quarter)

| Feature | Source | Notes |
|---|---|---|
| Revenue (YoY growth) | SEC XBRL / FinMind | Normalized |
| Gross margin | SEC XBRL / FinMind | |
| Inventory days | SEC XBRL / FinMind | Key leading indicator |
| Capex / Revenue | SEC XBRL / FinMind | Investment cycle signal |
| Customer concentration | 10-K Item 1A | Herfindahl index of top customers |
| Geographic revenue mix | 10-K segment disclosures | TW/US/China/Other |
| Price momentum (1m, 3m, 12m) | yfinance | Standard factor |
| Volatility (realized, 60d) | yfinance | |

### Edge Features

| Feature | Notes |
|---|---|
| Revenue dependency weight | % of supplier revenue from this customer |
| Data tier | 1/2/3 — proxy for confidence |
| Relationship age | How many consecutive years edge has appeared |

---

## Phase 3 — GNN Architecture

### Baseline: Graph Attention Network (GAT)

- Learns attention weights over neighbor edges — naturally handles varying edge quality (Tier 1 vs Tier 2)
- Per-node embedding captures both own features and supply chain neighborhood context
- Output: 64-dim node embedding per company per quarter

### Temporal Extension: Temporal Graph Network (TGN)

- Maintains per-node memory that updates as edges and features change over time
- Critical for modeling how a shock at a supplier node propagates downstream over quarters
- Training: predict node state at t+1 given graph state at t

### Training Objective (two heads)

```
Head 1 — Supply chain stress score
  Label: realized inventory disruption events (earnings misses on supply-side)
  Loss:  binary cross-entropy

Head 2 — Forward return prediction
  Label: 1-quarter forward return (market-adjusted)
  Loss:  MSE or ranking loss (ListMLE)
```

Multi-task loss: `L = α * L_stress + (1-α) * L_return`

### Walk-Forward Training Protocol

```
Train: 2015–2020  (5 years)
Val:   2021       (1 year)
Test:  2022–2024  (out-of-sample)

Re-train annually with expanding window.
Never use future graph structure in training (edges only from filings available at time t).
```

---

## Phase 4 — Signal Construction

### GNN Embedding → Alpha

After training, each node has a quarterly embedding vector. Alpha signals derived from it:

1. **Stress propagation score** — weighted average of upstream supplier stress scores (Head 1 output), propagated through the graph. High score = your suppliers are under pressure before you report it.

2. **Neighborhood return momentum** — if your supply chain neighbors had positive surprises last quarter, does that predict your return next quarter?

3. **Bottleneck centrality delta** — change in a node's weighted betweenness centrality. If a company becomes more central (more paths depend on it), it may be a risk concentration or a pricing power signal.

### Combination with Price Factors

Final signal = GNN embedding features + standard price factors (momentum, value, quality). Combine via:
- Ridge regression (interpretable baseline)
- LightGBM (captures non-linearity)
- Test whether GNN features add IC beyond price factors alone

---

## Phase 5 — Backtest & Validation

### Metrics

| Metric | Target |
|---|---|
| IC (Information Coefficient) | > 0.05 consistently |
| ICIR | > 0.5 |
| Annual return (L/S) | > 10% |
| Max drawdown | < 20% |
| Sharpe ratio | > 1.0 |

### Backtest Design

- Universe: TWSE Top 200 + S&P 500
- Rebalance: quarterly (aligned with earnings/filing cycle)
- Transaction costs: 0.1% US, 0.3% TW (realistic for retail)
- Long/short: top and bottom quintile by signal score
- Separate evaluation for TW-only, US-only, cross-market signal

### Key Validation Tests

1. **Graph ablation** — does performance degrade if edges are removed? (Confirms the graph structure matters, not just node features)
2. **Tier ablation** — Tier 1 edges only vs Tier 1+2+3. How much do lower-quality edges add?
3. **Temporal ablation** — static graph vs temporal graph. Is the time dimension worth the complexity?
4. **Cross-market test** — can US supply chain data predict TW stock returns and vice versa?

---

## Data Sources

| Data Type | Source | Cost |
|---|---|---|
| US supply chain edges | SEC EDGAR 10-K via `edgartools` | Free |
| TW ADR supply chain edges | SEC EDGAR 20-F via `edgartools` | Free |
| US company fundamentals | SEC XBRL via `edgartools` | Free |
| TW company fundamentals | FinMind API | Free (300 req/hr) |
| US stock prices | `yfinance` | Free |
| TW stock prices | `yfinance` (`.TW` suffix) / FinMind | Free |
| Dense relationship data | FactSet Revere via WRDS | Free with university access |

---

## Prior Art

Key papers this project builds on. See `PRIOR_ART.md` for full detail and commercial data landscape.

| Paper | Key Finding |
|---|---|
| Cohen & Frazzini (2008) | Customer earnings surprises predict supplier returns with delay — foundational evidence for H1 |
| Menzly & Ozbas (2010) | Effect is stronger for less-covered firms — supports the Taiwan small-cap angle |
| Ahern (2013) | Network centrality is priced in cross-section of returns — grounds the centrality delta signal |
| Herskovic (2018) | Supply chain network structure affects systematic risk and expected returns — theoretical foundation |
| Barrot & Sauvagnat (2016) | Supplier shocks propagate to customer sales — empirical support for the stress propagation mechanism |
| Feng et al. (2019) | Ranking loss outperforms MSE for portfolio signal construction — informs loss function choice |

---

## Folder Structure

```
chainlens/
├── src/
│   ├── universe/          # Phase 0: master ticker table
│   ├── pipeline/
│   │   ├── edgar/         # SEC 10-K/20-F extraction
│   │   ├── finmind/       # Taiwan fundamentals + prices
│   │   └── prices/        # yfinance price pulls
│   ├── graph/             # Phase 1: graph construction + schema
│   ├── features/          # Phase 2: feature engineering
│   ├── models/            # Phase 3: GAT, TGN implementations
│   ├── signals/           # Phase 4: alpha construction
│   └── backtest/          # Phase 5: walk-forward backtest
├── notebooks/             # exploratory analysis per phase
├── data/
│   ├── raw/               # unprocessed downloads
│   ├── processed/         # cleaned nodes, edges, features
│   └── graphs/            # serialized graph objects
├── configs/
│   └── config.yaml        # universe params, model hyperparams
└── tests/
```

---

## Risks

Five risks that could kill the project. See `RISKS.md` for full detail.

| # | Risk | When to Test |
|---|---|---|
| 1 | **Graph too sparse** — >10% revenue threshold leaves most nodes with 2–3 edges; GNN has nothing to aggregate | Immediately after Phase 1 |
| 2 | **Look-ahead bias** — filing dates accidentally contaminate training graph with future information | Before any training run |
| 3 | **No IC on simple version** — if static graph + linear model shows no IC, the GNN won't fix it | Before Phase 3 |
| 4 | **Taiwan short-selling constraints** — thin borrow market + 0.3% transaction tax may make the short leg unexecutable | Before Phase 5 |
| 5 | **Regime non-stationarity** — pre/post-2020 supply chain structure is materially different; model may not generalize | During Phase 5 validation |

Risks 1 and 3 are go/no-go gates. Resolve them before building the full stack.

---

## Status

- [x] Phase 0: Universe construction — 703 nodes (200 TW, 503 US), 7 ADR cross-references
- [ ] Phase 1: Graph construction
- [ ] Phase 2: Feature engineering
- [ ] Phase 3: GNN training — **gate: run static graph + linear model IC check first**
- [ ] Phase 4: Signal construction
- [ ] Phase 5: Backtest

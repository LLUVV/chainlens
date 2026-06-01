# Decision Log

Architecture and design choices — what we decided and why. Update when a decision is made or revisited.

---

## Graph Architecture

**GAT over GraphSAGE**
GAT learns attention weights over neighbors, which naturally handles edge quality variation (Tier 1 edges are more reliable than Tier 2/3). GraphSAGE treats all neighbors equally. Given that our graph has mixed-quality edges, attention is the right inductive bias.

**Temporal graph (TGN) over static graph**
Supply chain relationships change materially over 5–10 year windows — a customer representing 25% of revenue in 2015 may have diversified away by 2022. A static graph trained on the full period would treat edges as permanent and introduce structural look-ahead. TGN maintains per-node memory that updates as edges appear/disappear.

**Multi-task training (stress head + return head)**
Two reasons: (1) stress supervision provides a training signal for nodes that have stable returns but do experience supply disruptions — it catches more of the graph. (2) stress detection is independently useful as an early warning system, regardless of whether the return head generalizes.

---

## Universe

**TWSE Top 200 + S&P 500, not full market**
Liquidity filter. Taiwan small-caps have wide spreads and thin borrow markets — the short leg of a L/S strategy is difficult to execute. The top 200 by market cap covers the companies that are actually part of the global supply chain and can be traded.

**`.TW` ticker as canonical, not US ADR**
Dual-listed companies (TSMC, UMC, ASE) trade in both markets. Using `.TW` as the node avoids double-counting and currency conversion noise in return calculations. The ADR is used only as a data source for SEC filings.

---

## Data

**SEC EDGAR as primary source for Tier 1 edges**
The >10% revenue customer disclosure is mandatory, standardized, and legally verified. It's the highest-confidence edge source available for free. Limitation: it only captures large, concentrated relationships.

**FinMind for Taiwan fundamentals over direct MOPS scraping**
FinMind provides a structured API over MOPS data in a normalized format. Scraping MOPS directly requires handling messy HTML and inconsistent formatting across companies. The rate limit (300 req/hr free tier) is manageable for quarterly data pulls.

**WRDS / FactSet Revere deferred**
FactSet Revere has superior edge coverage but requires institutional access. Once UCLA MS enrollment is active (Sep 2026), WRDS access should become available. The pipeline is designed so Revere edges can be added as a Tier 0 layer without restructuring the schema.

---

## Backtest

**Quarterly rebalance over monthly**
Supply chain signal comes from quarterly filings. Monthly rebalancing would require interpolating between data points that don't change at that frequency, adding noise without adding information. Quarterly also reduces transaction cost drag.

**Walk-forward validation over random split**
A random train/test split in a time-series context leaks future data into training. Walk-forward (expanding window, annual re-train) reflects actual deployment conditions: you only know what was available at time t.

**2020–2021 treated as a regime break, not normal training data**
COVID disrupted supply chains in a historically unprecedented way. Including this period naively in training could teach the model patterns that don't recur. Handle separately: either exclude from training, or train a separate model and blend.

---

## Open Decisions

- [ ] Loss function for return head: MSE vs. ranking loss (ListMLE). MSE optimizes point prediction; ranking loss optimizes ordering, which is what a L/S portfolio actually needs.
- [ ] Whether to include Tier 3 edges (Chinese NLP) in v1 or defer to v2.
- [ ] Position sizing: equal weight vs. signal-proportional weight within quintiles.

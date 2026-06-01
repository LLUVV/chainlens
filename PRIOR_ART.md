# Prior Art

What's been done, what's been proven, and where this project sits relative to existing work.

---

## Foundational Academic Papers

**Cohen & Frazzini (2008) — "Economic Links and Predictable Returns"**
*Journal of Finance*
The paper that started this field. Using Compustat customer segment disclosures, they show that customer earnings surprises predict supplier stock returns with a delay — markets are slow to propagate information along supply chain links. This is the empirical foundation for H1.
Key finding: a strategy long suppliers of positive-surprise customers and short suppliers of negative-surprise customers earns ~1.5% monthly alpha (pre-cost).
Limitation: US-only, static graph, no ML.

**Menzly & Ozbas (2010) — "Market Segmentation and Cross-predictability of Returns"**
*Journal of Finance*
Extends Cohen & Frazzini to industries — upstream industries predict downstream industry returns and vice versa. Shows the effect is stronger when analyst coverage is lower (less attention = more mispricing). Relevant to the Taiwan small-cap angle.

**Ahern (2013) — "Network Centrality and the Cross Section of Stock Returns"**
Constructs an input-output network from BEA data and shows that network centrality (how central a firm is in the supply chain) is priced in the cross section of returns. More central firms earn higher returns (risk) or lower returns (mispricing) depending on specification.
Relevant to the bottleneck centrality delta signal in Phase 4.

**Herskovic (2018) — "Networks in Production: Asset Pricing Implications"**
*Journal of Finance*
Theoretical model: firms connected through supply chain networks have correlated cash flow shocks. Network structure affects systematic risk and expected returns. Provides theoretical grounding for why graph features should predict returns, not just identify mispricings.

**Barrot & Sauvagnat (2016) — "Input Specificity and the Propagation of Idiosyncratic Shocks in Production Networks"**
*Quarterly Journal of Economics*
Natural disaster shocks (earthquakes, hurricanes) to suppliers propagate to customers in sales and employment. The effect is stronger when the supplier relationship is more specific (harder to replace). Empirical evidence for the stress propagation mechanism in H3.

---

## Recent ML / GNN Applications

**Matsunaga, Suzumura & Takahashi (2019) — "Exploring Graph Neural Networks for Stock Market Predictions with Rolling Window Analysis"**
One of the first GNN applications to stock prediction using industry relation graphs. Shows GNN embeddings add predictive power over LSTM baselines. Not supply-chain-specific — uses industry co-movement graphs.

**Feng et al. (2019) — "Temporal Relational Ranking for Stock Prediction"**
Uses relational data (industry, supply chain) with a graph attention mechanism for stock ranking. Demonstrates ranking loss outperforms MSE loss for portfolio construction (relevant to the open decision on loss function).

**General observation on ML finance papers (2020–2024):**
Most use Chinese A-share data (abundant, well-structured) or US-only data. Taiwan-US cross-market with supply chain is not well-covered. Most treat the graph as static. Very few use TGN-style temporal memory.

---

## Commercial Data

**FactSet Revere**
The gold standard supply chain database. Covers ~10,000 companies globally with supplier/customer relationships sourced from filings, earnings calls, and analyst research. Tier 0 quality — quantified, verified, updated quarterly. Cost: ~$100K+/year commercial. Available via WRDS with university access (target: UCLA Sep 2026).
*This project should be designed to ingest Revere data as a Tier 0 layer once access is available.*

**Bloomberg SPLC (Supply Chain Analysis)**
Bloomberg terminal product. Same tier as Revere. Requires terminal access (~$25K/year). Not a priority given WRDS path.

**S&P Global Panjiva**
Trade flow data — actual import/export shipments. Different from filing-based data: catches relationships not disclosed in filings. Expensive. Could be a future Tier 0.5 layer between Revere and filing-based edges.

---

## What This Project Does Differently

| Dimension | Prior work | This project |
|---|---|---|
| Geography | US-only or China A-shares | Taiwan + US cross-market |
| Graph type | Static | Temporal (TGN) |
| Edge source | Compustat / BEA / single source | Multi-tier (SEC + NLP + FinMind) |
| Model | Linear / shallow ML / simple GNN | GAT + TGN + multi-task |
| Signal | Return prediction | Return + stress propagation |
| Language | N/A | Chinese NLP for MOPS (Tier 3) |

The differentiated claim: cross-market Taiwan-US propagation is under-researched, and the temporal graph captures relationship changes that static models miss. The stress detection head is an addition not present in prior work.

---

## What Prior Work Has Already Proven (Don't Reinvent)

- First-order supply chain return predictability exists (Cohen & Frazzini). Start from this as given; focus on what adds to it.
- Effect is stronger for less-covered firms (Menzly & Ozbas). Expect the Taiwan small-cap signal to be stronger than large-cap US.
- Network centrality matters for risk (Ahern, Herskovic). Centrality delta is worth computing.
- Ranking loss is better than MSE for portfolio signal (Feng et al.). Resolve the open decision in DECISIONS.md accordingly.

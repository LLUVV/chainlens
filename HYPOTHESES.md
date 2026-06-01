# Testable Hypotheses

Each hypothesis is stated precisely enough to be falsified. For each: what we expect, how we measure it, and what result would kill it.

---

## H1 — First-Order Lag Effect

**Claim:** When a customer company reports an earnings surprise (beat or miss), its direct suppliers' stock prices do not fully adjust within the same week.

**Measure:** Event study around customer earnings dates. Compute abnormal return of supplier stocks in the 1–4 weeks following the announcement. If suppliers fully price the information immediately, CAAR ≈ 0 post-announcement.

**Kill condition:** CAAR is statistically indistinguishable from zero in the 1–4 week window.

**Why it matters:** This is the baseline. If first-order effects are already fully priced, second and third-order effects certainly are.

---

## H2 — Second-Order Effects Are Less Priced Than First-Order

**Claim:** The returns of a supplier's supplier (two hops from the earnings event) adjust more slowly than direct suppliers (one hop).

**Measure:** Same event study as H1, split by graph distance from the earnings event. Compare CAAR across hop-1 and hop-2 nodes.

**Kill condition:** Hop-2 CAARs are not meaningfully larger than hop-1 CAARs in the post-announcement window.

**Why it matters:** The competitive advantage of the graph model depends on this being true. If the market prices all hops equally fast, the graph adds no information over a pairwise model.

---

## H3 — Inventory Days as a Leading Indicator

**Claim:** Rising inventory days at a supplier node predicts a negative earnings surprise at its downstream customer nodes within 1–2 quarters.

**Measure:** Rank supplier nodes by QoQ inventory days change. Compute forward earnings surprise distribution for their customer nodes. Test whether top-decile inventory buildup predicts negative surprise at rate above base rate.

**Kill condition:** No statistically significant relationship between supplier inventory days change and downstream customer earnings surprise.

**Why it matters:** This is the stress propagation mechanism that justifies Head 1 of the model. If it doesn't exist in raw data, the stress head has no supervision signal worth learning.

---

## H4 — Cross-Market Propagation Is Asymmetric

**Claim:** Taiwan supply chain events predict US stock returns more reliably than US events predict Taiwan returns, because Taiwan companies are earlier in the supply chain (upstream component makers).

**Measure:** Compute IC of cross-market signal separately in both directions (TW→US and US→TW). Compare magnitude and statistical significance.

**Kill condition:** IC is similar in both directions, suggesting no asymmetry. OR both directions have IC ≈ 0.

**Why it matters:** The Taiwan-US cross-market angle is the core differentiator of this project. If the propagation is symmetric or absent, the project reduces to a US-only supply chain model with added complexity.

---

## H5 — Graph Features Add IC Beyond Price Factors

**Claim:** The GNN embedding features contribute measurable IC over a baseline model that uses only standard price factors (momentum, value, quality).

**Measure:** Train two models on the same universe and period: (A) price factors only, (B) price factors + GNN embeddings. Compare out-of-sample IC and ICIR. Test significance of the IC difference.

**Kill condition:** Model B's IC is not statistically significantly higher than Model A's.

**Why it matters:** If graph features don't add IC beyond price factors, the entire Phase 1–3 pipeline is overhead with no payoff.

---

## H6 — Stress Signal Has 1–2 Quarter Lead Time

**Claim:** The stress propagation score (Head 1 output) is a leading indicator of earnings misses, visible 1–2 quarters before the miss is reported.

**Measure:** For nodes that eventually reported a supply-side earnings miss, compute the average stress score in the 1, 2, 3, and 4 quarters prior. Test whether stress scores are elevated pre-miss vs. control group.

**Kill condition:** Stress scores are not elevated in the quarters preceding the miss, or are elevated only in the quarter immediately before (not enough lead time to trade).

**Why it matters:** The practical value of the stress head depends on lead time. A signal visible the same quarter as the miss is useless for a quarterly rebalance strategy.

---

## Hypothesis Priority

Test in this order — each is a gate for the next:

1. H1 (first-order lag exists at all)
2. H3 (inventory days mechanism)
3. H5 (graph adds IC beyond price factors)
4. H2, H4, H6 (refinements that matter only if H1/H3/H5 pass)

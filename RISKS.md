# Project Risks

Five risks that could kill the project, not just slow it down.

---

## 1. Graph Too Sparse to Learn From

The >10% revenue threshold in SEC filings means most nodes have 2–3 edges. GNNs need meaningful neighborhoods to aggregate over. If the average company has 2 disclosed relationships, the architecture reduces to pairwise comparison with extra steps.

**Test early:** build the graph and check the actual degree distribution. If it's thin, the GNN doesn't save you.

---

## 2. Look-Ahead Bias in Graph Construction

The most dangerous failure mode — invisible until late. If any edge in the training graph came from a filing not publicly available at prediction time (e.g., a 10-K filed March 2021 used to train on 2020 data), the backtest is contaminated. The model looks good; it's memorizing the future.

The temporal graph design acknowledges this, but implementation bugs here are hard to detect because the model still learns *something* — just not what you think.

**Mitigation:** enforce strict filing-date cutoffs at every stage of graph construction. Audit edge timestamps before any training run.

---

## 3. No IC on the Simple Version

Before GNN, before TGN, before multi-task training: does supply chain neighborhood predict returns at all using a static graph and linear regression?

If the answer is no, complexity doesn't fix it. GNNs amplify signal — they don't conjure it from noise.

**Test first:** static graph + linear model + IC check. This is the go/no-go gate for the full architecture.

---

## 4. Taiwan Short-Selling Constraints

A long/short strategy on TWSE is not equivalent to NYSE. Taiwan's borrow market is thin, short-selling regulations are more restrictive, and the securities transaction tax (0.3% one-way) means ~0.6% round-trip per trade per quarter.

If shorting is unreliable, the strategy becomes long-only with factor exposure — not a market-neutral alpha source. This changes backtest design and realistic return expectations entirely.

**Clarify early:** what is the actual execution universe and can both legs be traded?

---

## 5. Regime Non-Stationarity

The supply chain structure of 2015–2019 is materially different from 2022–2024. COVID reshuffled relationships. The CHIPS Act, US-China export restrictions, and nearshoring broke edges that existed for a decade and created new ones not yet in any filing.

A model trained on the pre-2020 graph may be learning patterns that no longer exist.

**Mitigation:** weight recent training data more heavily. Test separately on pre- and post-2020 periods. Treat 2020–2021 as a regime break, not normal noise.

---

## Priority Order

Risks 1 and 3 are testable immediately without the full stack. Resolve them first — they are the go/no-go gates. Risks 2, 4, and 5 are execution risks that matter only if 1 and 3 pass.

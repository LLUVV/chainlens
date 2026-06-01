from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Edge:
    """A directed supply chain relationship: source supplies to target.

    Tier legend (matches config edge_tiers):
        0 = FactSet Revere (reserved, not yet available)
        1 = Quantified: company named + revenue % stated in SEC filing
        2 = Named: company mentioned as supplier/customer, no percentage
        3 = Inferred: MOPS/Chinese NLP (deferred to v2)
    """
    source: str                   # supplier canonical ticker  (e.g. "2330.TW")
    target: str                   # customer canonical ticker  (e.g. "AAPL")
    weight: Optional[float]       # revenue share 0.0–1.0 (Tier 1 only; None for Tier 2+)
    fiscal_year: int              # fiscal year being reported (e.g. 2022)
    filing_date: str              # YYYY-MM-DD when filing became public on EDGAR
    source_filing: str            # human-readable id, e.g. "TSM 20-F FY2022"
    tier: int                     # 0–3 per legend above
    filer_ticker: str = ""        # canonical ticker of the company that filed (may differ from source)
    direction_in_filing: str = "" # "supplier_names_customer" | "customer_names_supplier"

    def __post_init__(self):
        if self.weight is not None:
            # Store as fraction, not percentage
            if self.weight > 1.0:
                self.weight = self.weight / 100.0
            assert 0.0 < self.weight <= 1.0, f"weight out of range: {self.weight}"
        assert self.tier in (0, 1, 2, 3), f"invalid tier: {self.tier}"
        assert self.source != self.target, f"self-loop not allowed: {self.source}"

    @property
    def key(self) -> tuple:
        """Deduplication key: same source/target/year."""
        return (self.source, self.target, self.fiscal_year)

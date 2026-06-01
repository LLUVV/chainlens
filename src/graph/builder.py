"""
Phase 1 — Temporal graph builder.

Takes the raw edge DataFrame (from extractor.py) and assembles per-year
networkx graphs with look-ahead protection: a graph for year Y includes
only edges whose filing_date <= the training cutoff for year Y.

The filing-date cutoff is:
    cutoff(Y) = {fiscal_year_end(Y)} + {filing_lag}
    Default filing lag: 180 days (conservative — 10-Ks due 60–90 days
    after fiscal year end, 20-Fs due up to 120 days after).

Saved as:
    data/graphs/graph_{year}.pkl     ← networkx DiGraph
    data/graphs/edges_{year}.parquet ← edge table for that snapshot
"""
from __future__ import annotations

import logging
import pickle
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import networkx as nx
import pandas as pd

logger = logging.getLogger(__name__)
PROJECT_ROOT = Path(__file__).parent.parent.parent
EDGE_PATH    = PROJECT_ROOT / "data" / "processed" / "edges" / "edges_raw.parquet"
GRAPH_DIR    = PROJECT_ROOT / "data" / "graphs"

_FILING_LAG_DAYS = 180   # edges available this many days after fiscal year end


def _cutoff_date(fiscal_year: int, lag_days: int = _FILING_LAG_DAYS) -> str:
    """Latest date at which edges for fiscal_year are considered public."""
    # Assume fiscal year ends Dec 31
    year_end = datetime(fiscal_year, 12, 31)
    cutoff = year_end + timedelta(days=lag_days)
    return cutoff.strftime("%Y-%m-%d")


def build_snapshot(
    edges_df: pd.DataFrame,
    fiscal_year: int,
    training_cutoff: Optional[str] = None,
    tiers: list[int] = (1, 2),
) -> nx.DiGraph:
    """
    Build a directed graph for a single fiscal year.

    Includes only edges where:
      - fiscal_year matches
      - filing_date <= training_cutoff  (look-ahead protection)
      - tier in tiers

    Node attributes: ticker (same as node id)
    Edge attributes: weight, tier, source_filing, filing_date
    """
    if training_cutoff is None:
        training_cutoff = _cutoff_date(fiscal_year)

    mask = (
        (edges_df["fiscal_year"] == fiscal_year)
        & (edges_df["filing_date"] <= training_cutoff)
        & (edges_df["tier"].isin(tiers))
    )
    subset = edges_df[mask]

    G = nx.DiGraph()
    G.graph["fiscal_year"] = fiscal_year
    G.graph["training_cutoff"] = training_cutoff
    G.graph["tiers"] = list(tiers)

    for _, row in subset.iterrows():
        src, tgt = row["source"], row["target"]
        G.add_node(src)
        G.add_node(tgt)
        # If edge already exists, keep highest-quality (lowest tier number)
        if G.has_edge(src, tgt):
            existing = G[src][tgt]
            if row["tier"] >= existing.get("tier", 9):
                continue
        G.add_edge(src, tgt,
                   weight=row.get("weight"),
                   tier=int(row["tier"]),
                   source_filing=str(row.get("source_filing", "")),
                   filing_date=str(row.get("filing_date", "")))

    return G


def build_all_snapshots(
    edges_df: pd.DataFrame,
    years: Optional[list[int]] = None,
    tiers: list[int] = (1, 2),
) -> dict[int, nx.DiGraph]:
    """Build and save a graph snapshot for each year in the edge dataset."""
    if years is None:
        years = sorted(edges_df["fiscal_year"].dropna().unique().astype(int))

    GRAPH_DIR.mkdir(parents=True, exist_ok=True)
    graphs: dict[int, nx.DiGraph] = {}

    for year in years:
        G = build_snapshot(edges_df, year, tiers=tiers)
        graphs[year] = G

        # Save
        pkl_path = GRAPH_DIR / f"graph_{year}.pkl"
        with open(pkl_path, "wb") as f:
            pickle.dump(G, f)

        # Also save edge table for this year
        mask = edges_df["fiscal_year"] == year
        edges_df[mask].to_parquet(GRAPH_DIR / f"edges_{year}.parquet", index=False)

        logger.info(
            f"  {year}: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges "
            f"(cutoff: {G.graph['training_cutoff']})"
        )

    return graphs


def load_snapshot(year: int) -> nx.DiGraph:
    pkl_path = GRAPH_DIR / f"graph_{year}.pkl"
    with open(pkl_path, "rb") as f:
        return pickle.load(f)

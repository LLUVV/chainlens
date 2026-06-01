"""
Phase 1 validation: look-ahead audit + degree distribution check.

Two critical checks (per RISKS.md):
  1. Look-ahead audit: no edge has filing_date after the training cutoff
     for its fiscal year. This is the most dangerous silent failure mode.
  2. Degree distribution: mean node degree >= config.graph.min_mean_degree.
     If the graph is too sparse, the GNN has nothing to aggregate over.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from pathlib import Path

import networkx as nx
import numpy as np
import pandas as pd
import yaml

logger = logging.getLogger(__name__)
PROJECT_ROOT = Path(__file__).parent.parent.parent

_FILING_LAG_DAYS = 180


def _training_cutoff(fiscal_year: int) -> str:
    year_end = datetime(fiscal_year, 12, 31)
    return (year_end + timedelta(days=_FILING_LAG_DAYS)).strftime("%Y-%m-%d")


# ── Look-ahead audit ───────────────────────────────────────────────────────

def audit_lookahead(edges_df: pd.DataFrame) -> dict:
    """
    Check that no edge uses a filing published after its fiscal year's
    training cutoff. Flags any violations.

    Returns {
        "n_edges": int,
        "n_violations": int,
        "violation_rate": float,
        "violations": DataFrame (empty if clean)
    }
    """
    df = edges_df.copy()
    df["training_cutoff"] = df["fiscal_year"].apply(
        lambda y: _training_cutoff(int(y)) if pd.notna(y) else "9999-99-99"
    )
    df["filing_date"] = df["filing_date"].astype(str)

    violations = df[df["filing_date"] > df["training_cutoff"]]
    n = len(violations)
    rate = n / max(len(df), 1)

    result = {
        "n_edges":        len(df),
        "n_violations":   n,
        "violation_rate": rate,
        "violations":     violations,
    }

    if n == 0:
        logger.info("✓ Look-ahead audit PASSED: no violations")
    else:
        logger.error(
            f"✗ Look-ahead audit FAILED: {n} violations ({rate:.1%})\n"
            f"  Sample:\n{violations[['source','target','fiscal_year','filing_date','training_cutoff']].head(5)}"
        )

    return result


# ── Degree distribution ───────────────────────────────────────────────────

def audit_degree(graph_snapshots: dict[int, nx.DiGraph], min_mean_degree: float = 3.0) -> dict:
    """
    Check degree distribution across all year snapshots.

    Returns stats dict per year; logs a warning if any year fails the gate.
    """
    cfg_path = PROJECT_ROOT / "configs" / "config.yaml"
    with open(cfg_path) as f:
        cfg = yaml.safe_load(f)
    min_deg = cfg.get("graph", {}).get("min_mean_degree", min_mean_degree)

    stats = {}
    gate_passed = True

    for year, G in sorted(graph_snapshots.items()):
        if G.number_of_nodes() == 0:
            stats[year] = {"nodes": 0, "edges": 0, "mean_degree": 0.0, "gate": False}
            gate_passed = False
            continue

        degrees = [d for _, d in G.degree()]
        mean_deg = float(np.mean(degrees))
        max_deg  = int(np.max(degrees))
        pct_isolated = float(np.mean([d == 0 for d in degrees]))

        gate_ok = mean_deg >= min_deg
        if not gate_ok:
            gate_passed = False

        stats[year] = {
            "nodes":        G.number_of_nodes(),
            "edges":        G.number_of_edges(),
            "mean_degree":  round(mean_deg, 2),
            "max_degree":   max_deg,
            "pct_isolated": round(pct_isolated, 3),
            "gate":         gate_ok,
        }

        status = "✓" if gate_ok else "✗"
        logger.info(
            f"  {status} {year}: {G.number_of_nodes()} nodes, "
            f"{G.number_of_edges()} edges, mean_degree={mean_deg:.1f} "
            f"(gate: ≥{min_deg})"
        )

    if not gate_passed:
        logger.warning(
            "Degree gate FAILED for one or more years. "
            "Graph may be too sparse for GNN. "
            "Consider: (1) adding Tier 3 edges, (2) using a pairwise model instead."
        )
    else:
        logger.info("✓ Degree gate PASSED for all years")

    return stats


# ── Summary report ────────────────────────────────────────────────────────

def run_audit(edges_df: pd.DataFrame, graph_snapshots: dict[int, nx.DiGraph]) -> dict:
    """Run all Phase 1 audits and return combined results."""
    logger.info("=== Phase 1 Audit ===")

    la_result = audit_lookahead(edges_df)

    logger.info("\nDegree distribution by year:")
    deg_result = audit_degree(graph_snapshots)

    # Edge stats
    tier_counts = edges_df["tier"].value_counts().to_dict()
    logger.info(f"\nEdge tier breakdown: {tier_counts}")

    cross_market = edges_df[
        (edges_df["source"].str.endswith(".TW") & ~edges_df["target"].str.endswith(".TW"))
        | (~edges_df["source"].str.endswith(".TW") & edges_df["target"].str.endswith(".TW"))
    ]
    logger.info(f"Cross-market edges (TW↔US): {len(cross_market)}")

    return {
        "lookahead":          la_result,
        "degree":             deg_result,
        "tier_breakdown":     tier_counts,
        "n_cross_market":     len(cross_market),
    }

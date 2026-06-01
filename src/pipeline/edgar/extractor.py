"""
Phase 1 — Supply chain edge extractor (main orchestrator).

For each company in the universe that has an SEC CIK:
  1. List 10-K / 20-F filings for each target year
  2. Download and cache filing text sections
  3. Run Tier 1 (quantified) extraction
  4. Run Tier 2 (named) extraction
  5. Entity-resolve extracted names → canonical tickers
  6. Emit Edge objects

Output: data/processed/edges/edges_raw.parquet
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import pandas as pd
import yaml

from ...graph.schema import Edge
from ...universe.adr_mapping import ADR_MAP
from .cik_resolver import resolve_ciks
from .downloader import get_filing_sections, list_filings
from .entity_resolver import EntityResolver
from .tier1 import extract_tier1_candidates, build_company_regex
from .tier2 import extract_tier2_candidates

logger = logging.getLogger(__name__)
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
OUTPUT_PATH = PROJECT_ROOT / "data" / "processed" / "edges" / "edges_raw.parquet"


def _form_for_ticker(ticker: str) -> str:
    """TSMC + other TW ADRs file 20-F; US companies file 10-K."""
    return "20-F" if ticker in ADR_MAP else "10-K"


def _make_edges(
    filer_ticker: str,
    candidates: list[dict],
    resolver: EntityResolver,
    fiscal_year: int,
    filing_date: str,
    filing_label: str,
    tier: int,
) -> list[Edge]:
    """
    Convert raw extraction candidates into Edge objects.

    candidates have keys: company_name, pct (Tier 1) or absent (Tier 2),
    direction ("names_customer" | "names_supplier").
    """
    edges = []
    for cand in candidates:
        raw_name = cand["company_name"]
        other_ticker = resolver.resolve(raw_name)
        if not other_ticker:
            continue
        if other_ticker == filer_ticker:
            continue  # skip self-loops

        direction = cand.get("direction", "names_customer")
        pct = cand.get("pct", 0.0)

        # Determine edge direction: supplier → customer
        if direction == "names_customer":
            # Filer is the supplier, extracted company is the customer
            source, target = filer_ticker, other_ticker
        else:
            # Filer is the customer, extracted company is the supplier
            source, target = other_ticker, filer_ticker

        # Tier classification: only Tier 1 if percentage is meaningful
        edge_tier = 1 if (tier == 1 and pct >= 1.0) else 2

        try:
            edge = Edge(
                source=source,
                target=target,
                weight=pct / 100.0 if edge_tier == 1 else None,
                fiscal_year=fiscal_year,
                filing_date=filing_date,
                source_filing=filing_label,
                tier=edge_tier,
                filer_ticker=filer_ticker,
                direction_in_filing=direction,
            )
            edges.append(edge)
        except AssertionError:
            pass  # schema validation rejected (e.g. source == target)

    return edges


def extract_company(
    ticker: str,
    cik: str,
    resolver: EntityResolver,
    target_years: list[int],
    company_re=None,
) -> list[Edge]:
    """Extract all edges for one company across target filing years."""
    form = _form_for_ticker(ticker)
    filings = list_filings(cik, form)
    if not filings:
        logger.debug(f"  {ticker}: no {form} filings found")
        return []

    # Build year → filing map (most recent filing for each fiscal year)
    year_to_filing: dict[int, dict] = {}
    for f in filings:
        fy = f.get("fiscal_year")
        if fy and fy in target_years:
            year_to_filing[fy] = f  # later filings overwrite earlier (amendments)

    all_edges: list[Edge] = []

    for year, filing_meta in sorted(year_to_filing.items()):
        accession   = filing_meta["accession"]
        filing_date = filing_meta["filing_date"]
        primary_doc = filing_meta.get("primary_doc", "")
        label = f"{ticker} {form} FY{year}"

        logger.debug(f"  {label}  filed={filing_date}  acc={accession}")

        sections = get_filing_sections(cik, accession, primary_doc, form=form)
        if not sections:
            continue

        full_text  = sections.get("full", "")
        item1_text = sections.get("item1", "")
        item1a_text= sections.get("item1a", "")

        # Tier 1: quantified extraction using entity-aware regex
        t1_cands = extract_tier1_candidates(item1a_text + "\n" + item1_text, company_re)
        t1_edges = _make_edges(
            ticker, t1_cands, resolver, year, filing_date, label, tier=1
        )

        # Tier 2: named extraction (Item 1 + Item 1A only)
        t2_cands = extract_tier2_candidates(item1_text, item1a_text)
        t2_edges = _make_edges(
            ticker, t2_cands, resolver, year, filing_date, label, tier=2
        )

        before = len(all_edges)
        all_edges.extend(t1_edges + t2_edges)
        added = len(all_edges) - before
        if added:
            logger.info(f"  {label}: +{len(t1_edges)} T1  +{len(t2_edges)} T2  edges")

    return all_edges


def extract_all(
    universe: pd.DataFrame,
    target_years: Optional[list[int]] = None,
    tickers_filter: Optional[list[str]] = None,
) -> pd.DataFrame:
    """
    Run the full Phase 1 extraction pipeline.

    Args:
        universe:       master ticker table (Phase 0 output)
        target_years:   fiscal years to process (default: config filing_years)
        tickers_filter: if set, only process these tickers (for testing)

    Returns:
        DataFrame of edges with columns matching Edge fields.
    """
    if target_years is None:
        cfg_path = PROJECT_ROOT / "configs" / "config.yaml"
        with open(cfg_path) as f:
            cfg = yaml.safe_load(f)
        target_years = cfg["data"]["filing_years"]

    logger.info("=== Phase 1: Supply Chain Edge Extraction ===")
    logger.info(f"Target years: {target_years[0]}–{target_years[-1]}")

    resolver = EntityResolver(universe)
    company_re = build_company_regex(resolver._exact)  # entity-aware regex for Tier 1

    logger.info("Resolving CIKs for universe companies...")
    cik_map = resolve_ciks(universe)
    logger.info(f"  {len(cik_map)} companies with SEC filings")

    if tickers_filter:
        cik_map = {t: c for t, c in cik_map.items() if t in tickers_filter}
        logger.info(f"  Filtered to {len(cik_map)} tickers")

    all_edges: list[Edge] = []
    total = len(cik_map)

    for i, (ticker, cik) in enumerate(cik_map.items(), 1):
        logger.info(f"[{i}/{total}] {ticker} (CIK {cik})")
        edges = extract_company(ticker, cik, resolver, target_years, company_re)
        all_edges.extend(edges)

    logger.info(f"\nExtracted {len(all_edges)} raw edges total")

    if not all_edges:
        return pd.DataFrame()

    df = pd.DataFrame([vars(e) for e in all_edges])

    # Deduplicate: keep highest-tier (lowest tier number) per (source, target, year)
    df = (df.sort_values("tier")
            .drop_duplicates(subset=["source", "target", "fiscal_year"], keep="first")
            .reset_index(drop=True))

    logger.info(f"After dedup: {len(df)} edges")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(OUTPUT_PATH, index=False)
    logger.info(f"Saved → {OUTPUT_PATH}")

    return df


def run_pilot(universe: pd.DataFrame) -> pd.DataFrame:
    """
    Quick pilot: extract from Taiwan ADRs only (7 companies, FY2020–2023).
    Used to validate the pipeline before running the full universe.
    """
    adr_tickers = list(ADR_MAP.keys())
    pilot_years = [2020, 2021, 2022, 2023]
    logger.info(f"Running pilot extraction: {adr_tickers} × {pilot_years}")
    return extract_all(universe, target_years=pilot_years, tickers_filter=adr_tickers)

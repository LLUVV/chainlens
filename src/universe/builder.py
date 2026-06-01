"""
Phase 0 — Universe Constructor

Builds the master ticker table: all tradeable nodes for chainlens,
combining Taiwan (TWSE/TPEx) and US (S&P 500) stocks with ADR cross-references.

Usage:
    python -m src.universe.builder
    python -m src.universe.builder --enrich-caps   # also fetch US market caps (slow)
"""
import argparse
import logging
import sys
from pathlib import Path

import pandas as pd
import yaml

from .adr_mapping import ADR_MAP
from .tw_universe import build_tw_universe
from .us_universe import build_us_universe

PROJECT_ROOT = Path(__file__).parent.parent.parent
OUTPUT_DIR = PROJECT_ROOT / "data" / "processed" / "nodes"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def load_config() -> dict:
    config_path = PROJECT_ROOT / "configs" / "config.yaml"
    with open(config_path) as f:
        return yaml.safe_load(f)


def apply_adr_mapping(df: pd.DataFrame) -> pd.DataFrame:
    """Fill adr_ticker / adr_exchange for TW stocks that have a US ADR."""
    df = df.copy()
    for tw_ticker, adr_info in ADR_MAP.items():
        mask = df["ticker"] == tw_ticker
        if mask.any():
            df.loc[mask, "adr_ticker"] = adr_info["adr_ticker"]
            df.loc[mask, "adr_exchange"] = adr_info["adr_exchange"]
    return df


def build_universe(tw_top_n: int = 200, us_index: str = "sp500", enrich_caps: bool = False) -> pd.DataFrame:
    logger.info("=== Phase 0: Universe Construction ===")

    logger.info("--- Taiwan ---")
    tw = build_tw_universe(top_n=tw_top_n)
    logger.info(f"  TW universe: {len(tw)} stocks")

    logger.info("--- US ---")
    us = build_us_universe(index=us_index, enrich_caps=enrich_caps)
    logger.info(f"  US universe: {len(us)} stocks")

    logger.info("--- Merging ---")
    universe = pd.concat([tw, us], ignore_index=True)
    universe = apply_adr_mapping(universe)

    # Canonical column order
    universe = universe[[
        "ticker", "company_name", "exchange", "sector",
        "market_cap_usd", "adr_ticker", "adr_exchange",
    ]]

    # Basic validation
    assert universe["ticker"].is_unique, "Duplicate tickers found — check ADR deduplication"
    adr_count = universe["adr_ticker"].notna().sum()
    logger.info(
        f"Universe built: {len(universe)} nodes "
        f"({len(tw)} TW, {len(us)} US, {adr_count} with ADR cross-reference)"
    )

    return universe


def save(universe: pd.DataFrame) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    parquet_path = OUTPUT_DIR / "universe.parquet"
    csv_path = OUTPUT_DIR / "universe.csv"
    universe.to_parquet(parquet_path, index=False)
    universe.to_csv(csv_path, index=False)
    logger.info(f"Saved → {parquet_path}")
    logger.info(f"Saved → {csv_path}")


def summary(universe: pd.DataFrame) -> None:
    print("\n=== Universe Summary ===")
    print(f"Total nodes : {len(universe)}")
    print(f"\nBy exchange :")
    print(universe["exchange"].value_counts().to_string())
    print(f"\nWith ADR    : {universe['adr_ticker'].notna().sum()}")
    tw_adr = universe[universe["adr_ticker"].notna()][["ticker", "company_name", "adr_ticker"]]
    if not tw_adr.empty:
        print("\nTW ↔ ADR cross-reference:")
        print(tw_adr.to_string(index=False))
    print(f"\nTop 10 by market cap (TW):")
    tw = universe[universe["exchange"].isin(["TWSE", "TPEx"])].dropna(subset=["market_cap_usd"])
    print(tw.nlargest(10, "market_cap_usd")[["ticker", "company_name", "market_cap_usd"]].to_string(index=False))


def main():
    parser = argparse.ArgumentParser(description="Build chainlens universe (Phase 0)")
    parser.add_argument("--enrich-caps", action="store_true", help="Fetch US market caps via yfinance (slow)")
    args = parser.parse_args()

    cfg = load_config()
    universe = build_universe(
        tw_top_n=cfg["universe"]["tw_top_n"],
        us_index=cfg["universe"]["us_index"],
        enrich_caps=args.enrich_caps,
    )
    save(universe)
    summary(universe)


if __name__ == "__main__":
    main()

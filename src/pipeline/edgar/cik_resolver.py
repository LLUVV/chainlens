"""
Resolve SEC CIK numbers for universe companies.

Uses SEC's official company_tickers_exchange.json to map tickers → CIKs.
For Taiwan ADRs, resolves via the ADR ticker (e.g., TSM → CIK for TSMC).
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

import pandas as pd
import requests

from ...universe.adr_mapping import ADR_MAP

logger = logging.getLogger(__name__)

SEC_TICKERS_URL = "https://www.sec.gov/files/company_tickers_exchange.json"
_HEADERS = {"User-Agent": "chainlens research jimbo21xc30@gmail.com"}
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
_CACHE_PATH = PROJECT_ROOT / "data" / "raw" / "edgar" / "company_tickers.json"


def _fetch_sec_tickers() -> dict:
    """Download SEC's full ticker→CIK mapping (cached locally)."""
    if _CACHE_PATH.exists():
        with open(_CACHE_PATH) as f:
            return json.load(f)
    logger.info("Downloading SEC company tickers from EDGAR...")
    resp = requests.get(SEC_TICKERS_URL, headers=_HEADERS, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    _CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(_CACHE_PATH, "w") as f:
        json.dump(data, f)
    logger.info(f"  Cached → {_CACHE_PATH}")
    return data


def build_ticker_to_cik() -> dict[str, str]:
    """Return dict: ticker (uppercase) → zero-padded CIK string (10 digits)."""
    raw = _fetch_sec_tickers()
    # Format: {"data": [[cik, name, ticker, exchange], ...], "fields": [...]}
    result: dict[str, str] = {}
    for row in raw.get("data", []):
        cik, name, ticker, exchange = row[0], row[1], row[2], row[3]
        cik_padded = str(cik).zfill(10)
        result[ticker.upper()] = cik_padded
    return result


def resolve_ciks(universe: pd.DataFrame) -> dict[str, str]:
    """
    Map tradeable tickers in universe to their SEC CIKs.

    For US stocks: match by ticker directly.
    For TW ADRs: match by ADR ticker (TSM → CIK for TSMC's SEC filings).
    For TW-only stocks: no CIK (they don't file with SEC).

    Returns dict: canonical_ticker → cik (only includes companies with SEC filings).
    """
    ticker_to_cik = build_ticker_to_cik()

    result: dict[str, str] = {}
    no_cik: list[str] = []

    for _, row in universe.iterrows():
        ticker = row["ticker"]
        exchange = row.get("exchange", "")

        # US stocks: direct lookup
        if exchange == "US":
            cik = ticker_to_cik.get(ticker.upper())
            if cik:
                result[ticker] = cik
            else:
                no_cik.append(ticker)
            continue

        # Taiwan stocks: look up via ADR ticker if available
        adr_info = ADR_MAP.get(ticker)
        if adr_info:
            adr_ticker = adr_info["adr_ticker"]
            cik = ticker_to_cik.get(adr_ticker.upper())
            if cik:
                result[ticker] = cik  # key is .TW canonical, CIK is from ADR filing
            else:
                no_cik.append(f"{ticker}(ADR:{adr_ticker})")
        # TW-only: skip (they appear as edge targets but don't file with SEC)

    logger.info(
        f"CIK resolution: {len(result)} companies matched, "
        f"{len(no_cik)} not found in EDGAR"
    )
    if no_cik:
        logger.debug(f"  No CIK: {no_cik[:20]}{'...' if len(no_cik) > 20 else ''}")

    return result

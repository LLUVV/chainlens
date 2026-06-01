from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

import pandas as pd
import requests

logger = logging.getLogger(__name__)

FINMIND_BASE = "https://api.finmindtrade.com/api/v4/data"
TWSE_BASE = "https://www.twse.com.tw/rwd/zh/afterTrading"
_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; chainlens/1.0; research)"}


def _finmind(dataset: str, **params) -> pd.DataFrame:
    params["dataset"] = dataset
    resp = requests.get(FINMIND_BASE, params=params, timeout=30)
    resp.raise_for_status()
    body = resp.json()
    if body.get("status") != 200:
        raise RuntimeError(f"FinMind [{dataset}]: {body.get('msg')}")
    return pd.DataFrame(body["data"])


def fetch_tw_stock_info() -> pd.DataFrame:
    """All tradeable TW stocks from FinMind.

    Deduplicates on stock_id (FinMind returns same stock under multiple
    industry_category entries when category changes). Keeps latest date.

    Returns columns: stock_id, company_name, sector, tw_exchange_type
    """
    df = _finmind("TaiwanStockInfo")

    # type field observed values: "twse" for all stocks in free tier.
    # FinMind free tier returns TWSE-listed stocks only.
    df = df[df["type"].str.lower().isin({"twse", "otc"})].copy()

    # Keep only 4-digit numeric IDs (drops ETFs, warrants, preferred shares)
    df = df[df["stock_id"].str.match(r"^\d{4}$")].copy()

    # Deduplicate: same stock_id appears multiple times when sector changes.
    # Sort by date desc, keep first (most recent sector classification).
    df = df.sort_values("date", ascending=False).drop_duplicates(subset="stock_id", keep="first")

    return (
        df.rename(columns={"stock_name": "company_name", "industry_category": "sector"})
        [["stock_id", "company_name", "sector", "type"]]
        .rename(columns={"type": "tw_exchange_type"})
        .reset_index(drop=True)
    )


def _twd_usd_rate() -> float:
    """NTD per 1 USD from yfinance TWD=X, fallback 32.0."""
    try:
        import yfinance as yf
        rate = yf.Ticker("TWD=X").fast_info.last_price
        if rate and 25.0 < rate < 45.0:
            logger.info(f"  TWD/USD rate: {rate:.2f}")
            return float(rate)
    except Exception:
        pass
    logger.warning("  Could not fetch TWD/USD rate, using 32.0")
    return 32.0


def _yf_market_cap_twd(ticker: str) -> Optional[float]:
    """Fetch market cap in local currency (TWD for .TW tickers). Returns None on failure."""
    try:
        import yfinance as yf
        mc = yf.Ticker(ticker).fast_info.market_cap
        return float(mc) if mc and mc > 0 else None
    except Exception:
        return None


def fetch_tw_market_caps(stock_ids: list[str], max_workers: int = 20) -> pd.DataFrame:
    """Fetch USD market caps for a list of TW stock IDs via yfinance (threaded).

    yfinance returns market cap in TWD (local currency) for .TW tickers.
    This function fetches TWD values concurrently, then converts to USD.

    Returns DataFrame with columns: stock_id, market_cap_usd
    """
    tickers = [sid + ".TW" for sid in stock_ids]
    ticker_to_id = {sid + ".TW": sid for sid in stock_ids}

    logger.info(f"  Fetching market caps for {len(tickers)} TW stocks (threaded, {max_workers} workers)...")
    caps_twd: dict[str, Optional[float]] = {}

    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = {ex.submit(_yf_market_cap_twd, t): t for t in tickers}
        done = 0
        for fut in as_completed(futures):
            ticker = futures[fut]
            caps_twd[ticker] = fut.result()
            done += 1
            if done % 100 == 0:
                logger.info(f"    {done}/{len(tickers)} done...")

    twd_rate = _twd_usd_rate()
    rows = [
        {"stock_id": ticker_to_id[t], "market_cap_usd": (v / twd_rate) if v is not None else None}
        for t, v in caps_twd.items()
    ]
    return pd.DataFrame(rows)


def build_tw_universe(top_n: int = 200) -> pd.DataFrame:
    """Build Taiwan tradeable universe, sorted by market cap, top top_n stocks.

    Output columns:
        ticker, company_name, exchange, sector, market_cap_usd,
        adr_ticker (None), adr_exchange (None)
    ADR fields are populated by builder.py.
    """
    logger.info("Fetching TW stock info from FinMind...")
    info = fetch_tw_stock_info()
    logger.info(f"  {len(info)} unique tradeable stocks")

    caps = fetch_tw_market_caps(info["stock_id"].tolist())
    merged = info.merge(caps, on="stock_id", how="left")
    merged["market_cap_usd"] = pd.to_numeric(merged["market_cap_usd"], errors="coerce")

    n_with_cap = merged["market_cap_usd"].notna().sum()
    logger.info(f"  Market cap fetched for {n_with_cap}/{len(merged)} stocks")

    # Validate: TSMC should be ~$500B–$1T USD
    tsmc = merged[merged["stock_id"] == "2330"]["market_cap_usd"]
    if not tsmc.empty and pd.notna(tsmc.iloc[0]):
        logger.info(f"  TSMC market cap: ${tsmc.iloc[0]/1e9:.0f}B USD (sanity check)")

    top = (
        merged.dropna(subset=["market_cap_usd"])
        .sort_values("market_cap_usd", ascending=False)
        .head(top_n)
        .copy()
    )
    logger.info(f"  Top {top_n} selected (min cap: ${top['market_cap_usd'].min()/1e9:.1f}B USD)")

    # yfinance-compatible ticker: all from FinMind free tier are TWSE (.TW)
    top["ticker"] = top["stock_id"] + ".TW"
    top["exchange"] = top["tw_exchange_type"].str.upper().map({"TWSE": "TWSE", "OTC": "TPEx"}).fillna("TWSE")

    return top[["ticker", "company_name", "exchange", "sector", "market_cap_usd"]].assign(
        adr_ticker=None, adr_exchange=None
    )

import io
import logging

import pandas as pd
import requests

logger = logging.getLogger(__name__)

SP500_WIKI = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; chainlens/1.0; research project)"}


def _fix_ticker(raw: str) -> str:
    """Wikipedia uses dots; yfinance uses hyphens for share classes (BRK.B → BRK-B)."""
    return raw.replace(".", "-")


def fetch_sp500() -> pd.DataFrame:
    """Scrape S&P 500 constituents from Wikipedia.

    Returns columns: ticker, company_name, exchange, sector, market_cap_usd
    """
    logger.info("Fetching S&P 500 list from Wikipedia...")
    resp = requests.get(SP500_WIKI, headers=_HEADERS, timeout=30)
    resp.raise_for_status()
    tables = pd.read_html(io.StringIO(resp.text), header=0)
    df = tables[0]

    # Wikipedia columns: Symbol, Security, GICS Sector, GICS Sub-Industry,
    #                    Headquarters Location, Date added, CIK, Founded
    df = df.rename(columns={
        "Symbol": "raw_ticker",
        "Security": "company_name",
        "GICS Sector": "sector",
        "GICS Sub-Industry": "sub_industry",
    })
    df["ticker"] = df["raw_ticker"].apply(_fix_ticker)

    # Exchange: determine from ticker patterns
    # Almost all S&P 500 are NYSE or NASDAQ; we tag as "US" and refine if needed
    df["exchange"] = "US"
    df["market_cap_usd"] = None   # enriched optionally in enrich_us_market_caps()
    df["adr_ticker"] = None
    df["adr_exchange"] = None

    logger.info(f"  {len(df)} S&P 500 constituents")
    return df[["ticker", "company_name", "exchange", "sector", "market_cap_usd", "adr_ticker", "adr_exchange"]]


def enrich_us_market_caps(df: pd.DataFrame, batch_size: int = 100) -> pd.DataFrame:
    """Optionally fill market_cap_usd for US stocks via yfinance fast_info.

    This is slow (~1–2 min for 500 stocks). Skip if only ranking is needed.
    """
    import yfinance as yf
    from tqdm import tqdm

    caps = {}
    tickers = df["ticker"].tolist()
    logger.info(f"Fetching market caps for {len(tickers)} US stocks via yfinance...")

    for i in tqdm(range(0, len(tickers), batch_size), desc="market caps"):
        batch = tickers[i : i + batch_size]
        for t in batch:
            try:
                caps[t] = yf.Ticker(t).fast_info.market_cap
            except Exception:
                caps[t] = None

    df = df.copy()
    df["market_cap_usd"] = df["ticker"].map(caps)
    return df


def build_us_universe(index: str = "sp500", enrich_caps: bool = False) -> pd.DataFrame:
    """Build US tradeable universe.

    Args:
        index:       "sp500" (only supported index for now)
        enrich_caps: if True, fetch market caps from yfinance (slow)
    """
    if index != "sp500":
        raise NotImplementedError(f"Index '{index}' not yet supported; use 'sp500'")

    df = fetch_sp500()
    if enrich_caps:
        df = enrich_us_market_caps(df)
    return df

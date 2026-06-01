# Taiwan companies with US ADR listings that file 20-F with the SEC.
# key          = canonical trading ticker (.TW = TWSE, .TWO = TPEx)
# adr_ticker   = US ADR ticker — used for SEC EDGAR data sourcing only, never for trading
# adr_exchange = listing exchange of the ADR
# adr_ratio    = number of TW ordinary shares represented by 1 ADR
#                Used for cross-market price calibration:
#                  implied_usd_price = adr_price_usd / adr_ratio
#                  implied_rate      = tw_price_twd / implied_usd_price
#                For ADR-linked stocks, market cap is sourced from the ADR ticker
#                (already in USD) rather than converting TW price via spot FX.

ADR_MAP: dict[str, dict] = {
    "2330.TW": {"adr_ticker": "TSM",  "adr_exchange": "NYSE",   "adr_ratio": 5},
    "2303.TW": {"adr_ticker": "UMC",  "adr_exchange": "NYSE",   "adr_ratio": 2},
    "3711.TW": {"adr_ticker": "ASX",  "adr_exchange": "NYSE",   "adr_ratio": 5},
    "2409.TW": {"adr_ticker": "AUO",  "adr_exchange": "NYSE",   "adr_ratio": 10},
    "2412.TW": {"adr_ticker": "CHT",  "adr_exchange": "NYSE",   "adr_ratio": 10},
    "3036.TW": {"adr_ticker": "HIMX", "adr_exchange": "NASDAQ", "adr_ratio": 2},
    "8150.TW": {"adr_ticker": "IMOS", "adr_exchange": "NASDAQ", "adr_ratio": 20},
}

# Reverse map: ADR ticker → canonical TW ticker (for resolving SEC filing references)
ADR_REVERSE: dict[str, str] = {v["adr_ticker"]: k for k, v in ADR_MAP.items()}

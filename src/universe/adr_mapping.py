# Taiwan companies with US ADR listings that file 20-F with the SEC.
# key   = canonical trading ticker (.TW = TWSE, .TWO = TPEx)
# value = ADR info used only for SEC EDGAR data sourcing — never for trading

ADR_MAP: dict[str, dict[str, str]] = {
    "2330.TW": {"adr_ticker": "TSM",  "adr_exchange": "NYSE"},
    "2303.TW": {"adr_ticker": "UMC",  "adr_exchange": "NYSE"},
    "3711.TW": {"adr_ticker": "ASX",  "adr_exchange": "NYSE"},
    "2409.TW": {"adr_ticker": "AUO",  "adr_exchange": "NYSE"},
    "2412.TW": {"adr_ticker": "CHT",  "adr_exchange": "NYSE"},
    "3036.TW": {"adr_ticker": "HIMX", "adr_exchange": "NASDAQ"},
    "8150.TW": {"adr_ticker": "IMOS", "adr_exchange": "NASDAQ"},
}

# Reverse map: ADR ticker → canonical TW ticker (for resolving SEC filing references)
ADR_REVERSE: dict[str, str] = {v["adr_ticker"]: k for k, v in ADR_MAP.items()}

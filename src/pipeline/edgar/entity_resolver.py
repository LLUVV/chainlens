"""
Entity resolver: company name string → canonical ticker.

Strategy (in order):
  1. Exact match on lowercased alias table (fastest, most reliable)
  2. Universe company name exact match
  3. Fuzzy token match (difflib) with minimum similarity threshold
  4. Return None if no confident match found

The resolver is seeded from:
  - The hardcoded ALIASES dict (known supply chain companies)
  - The live universe DataFrame (all tradeable nodes)
"""
from __future__ import annotations

import difflib
import logging
import re
from typing import Optional

import pandas as pd

from .aliases import ALIAS_REVERSE, ALIASES

logger = logging.getLogger(__name__)

# Minimum similarity ratio for fuzzy matching (0–1)
_FUZZY_THRESHOLD = 0.82

# Legal suffixes to strip before matching
_SUFFIXES = re.compile(
    r'\b(?:Inc\.?|Corp\.?|Ltd\.?|Co\.?|LLC|L\.L\.C|plc|N\.V\.?|'
    r'S\.A\.?|A\.G\.?|GmbH|Holdings?|Group|International|Technologies?|'
    r'Corporation|Incorporated|Limited|Company)\b',
    re.IGNORECASE
)


def _normalize(name: str) -> str:
    """Lowercase, strip legal suffixes and punctuation for comparison."""
    s = _SUFFIXES.sub("", name)
    s = re.sub(r'[^\w\s]', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip().lower()
    return s


class EntityResolver:
    def __init__(self, universe: pd.DataFrame):
        """
        Args:
            universe: DataFrame with columns [ticker, company_name]
        """
        # Build lookup: lowercased name → ticker
        self._exact: dict[str, str] = dict(ALIAS_REVERSE)  # seed from aliases

        for _, row in universe.iterrows():
            ticker = row["ticker"]
            name = str(row["company_name"])
            # Add exact name
            self._exact[name.lower().strip()] = ticker
            # Add normalized name
            self._exact[_normalize(name)] = ticker
            # Add aliases if ticker is in ALIASES
            for alias in ALIASES.get(ticker, []):
                self._exact[alias.lower().strip()] = ticker
                self._exact[_normalize(alias)] = ticker

        # For fuzzy: keep a list of (normalized_name, ticker) pairs
        seen: dict[str, str] = {}
        for norm, ticker in self._exact.items():
            if norm and norm not in seen:
                seen[norm] = ticker
        self._fuzzy_keys = list(seen.keys())
        self._fuzzy_vals = [seen[k] for k in self._fuzzy_keys]

        logger.info(f"EntityResolver: {len(self._exact)} exact entries from "
                    f"{universe['ticker'].nunique()} universe companies")

    def resolve(self, name: str) -> Optional[str]:
        """
        Map a company name string to a canonical ticker.

        Returns None if no confident match.
        """
        if not name or len(name) < 3:
            return None

        # 1. Exact match
        hit = self._exact.get(name.lower().strip())
        if hit:
            return hit

        # 2. Normalized exact match
        norm = _normalize(name)
        hit = self._exact.get(norm)
        if hit:
            return hit

        # 3. Fuzzy match
        if len(norm) < 4:
            return None
        matches = difflib.get_close_matches(norm, self._fuzzy_keys, n=1, cutoff=_FUZZY_THRESHOLD)
        if matches:
            idx = self._fuzzy_keys.index(matches[0])
            return self._fuzzy_vals[idx]

        return None

    def resolve_many(self, names: list[str]) -> dict[str, Optional[str]]:
        """Batch resolve. Returns {name: ticker_or_None}."""
        return {n: self.resolve(n) for n in names}

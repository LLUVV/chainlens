"""
EDGAR filing downloader with local caching.

For each company CIK, fetches the list of 10-K/20-F filings from EDGAR's
submissions API, then downloads the primary document text for each filing.

Cache layout:
    data/raw/edgar/{cik}/submissions.json   ← filing list
    data/raw/edgar/{cik}/{accession}/       ← filing documents
        primary.txt                         ← extracted plain text
        meta.json                           ← date, form, fiscal year
"""
from __future__ import annotations

import json
import logging
import re
import time
from pathlib import Path
from typing import Optional

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

EDGAR_BASE = "https://data.sec.gov"
EDGAR_ARCHIVES = "https://www.sec.gov/Archives/edgar/data"
_HEADERS = {"User-Agent": "chainlens research jimbo21xc30@gmail.com"}
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
CACHE_DIR = PROJECT_ROOT / "data" / "raw" / "edgar"

_RATE_SLEEP = 0.12   # SEC allows ~10 req/sec; stay conservative


def _get(url: str, **kwargs) -> requests.Response:
    time.sleep(_RATE_SLEEP)
    resp = requests.get(url, headers=_HEADERS, timeout=30, **kwargs)
    resp.raise_for_status()
    return resp


# ── Filing list ────────────────────────────────────────────────────────────

def get_submissions(cik: str) -> dict:
    """Fetch company submissions (filing history) from EDGAR. Cached."""
    cache = CACHE_DIR / cik / "submissions.json"
    if cache.exists():
        with open(cache) as f:
            return json.load(f)
    url = f"{EDGAR_BASE}/submissions/CIK{cik}.json"
    data = _get(url).json()
    cache.parent.mkdir(parents=True, exist_ok=True)
    with open(cache, "w") as f:
        json.dump(data, f)
    return data


def list_filings(cik: str, form: str) -> list[dict]:
    """
    Return all filings of the given form type for this CIK.

    Each entry: {accession, filing_date, primary_doc, fiscal_year_end}
    Sorted by filing_date ascending.
    """
    subs = get_submissions(cik)
    recent = subs.get("filings", {}).get("recent", {})

    forms     = recent.get("form", [])
    dates     = recent.get("filingDate", [])
    accessions= recent.get("accessionNumber", [])
    docs      = recent.get("primaryDocument", [])
    periods   = recent.get("reportDate", [])   # fiscal year end date

    results = []
    for f, d, a, doc, p in zip(forms, dates, accessions, docs, periods):
        if f.upper() == form.upper():
            results.append({
                "accession":     a,
                "filing_date":   d,         # YYYY-MM-DD, when public
                "primary_doc":   doc,
                "fiscal_year":   int(p[:4]) if p else None,
                "form":          f,
            })

    return sorted(results, key=lambda x: x["filing_date"])


# ── Filing text ────────────────────────────────────────────────────────────

def _html_to_text(html: str) -> str:
    """
    Parse HTML/iXBRL to clean plain text preserving newlines between blocks.

    Uses BeautifulSoup for proper parsing (handles modern inline XBRL filings).
    Removes script/style blocks and XBRL metadata tags before extracting text.
    """
    soup = BeautifulSoup(html, "lxml")

    # Remove non-content elements
    for tag in soup.find_all(["script", "style", "head"]):
        tag.decompose()
    # Remove XBRL metadata tags (ix:header, xbrli:xbrl, etc.)
    for tag in soup.find_all(True):
        if tag.name and ':' in tag.name and not tag.name.startswith('ix:'):
            tag.decompose()

    # Extract with newlines between block-level elements
    text = soup.get_text(separator="\n")
    # Collapse multiple blank lines to at most 2
    text = re.sub(r'\n{3,}', '\n\n', text)
    # Collapse horizontal whitespace
    text = re.sub(r'[ \t]+', ' ', text)
    return text.strip()


def _extract_section(text: str, item_num: str, min_content_len: int = 500) -> str:
    """
    Extract a named section from 10-K/20-F plain text.

    Skips table-of-contents hits (too short) and returns the first occurrence
    with substantial content (>= min_content_len characters).

    Handles variants: "ITEM 1A.", "Item 1A.", "ITEM 1A –", "Item 1A\n", etc.
    Returns up to 80,000 characters.
    """
    escaped = re.escape(item_num)
    header_pat = re.compile(
        rf'(?:^|\n)\s*(?:ITEM|Item)\s+{escaped}\b[^\n]{{0,80}}\n',
        re.IGNORECASE | re.MULTILINE
    )
    next_item_pat = re.compile(
        r'(?:^|\n)\s*(?:ITEM|Item)\s+\d+[A-Z]?\b',
        re.IGNORECASE | re.MULTILINE
    )

    # Find all header matches; return the first with enough content (skip TOC)
    pos = 0
    while True:
        m = header_pat.search(text, pos)
        if not m:
            return ""
        start = m.end()
        nm = next_item_pat.search(text, start + 200)
        end = nm.start() if nm else start + 80_000
        content = text[start:end][:80_000]
        if len(content.strip()) >= min_content_len:
            return content
        pos = m.end()  # try next occurrence


def get_filing_text(cik: str, accession: str, primary_doc: str) -> tuple[str, str]:
    """
    Download and cache a filing's primary document as plain text.

    Returns (full_text, item1a_text).
    """
    acc_clean = accession.replace("-", "")
    cache_dir = CACHE_DIR / cik / acc_clean
    text_cache = cache_dir / "primary.txt"
    meta_cache = cache_dir / "meta.json"

    if text_cache.exists():
        return text_cache.read_text(encoding="utf-8", errors="replace"), ""

    # Build URL
    url = f"{EDGAR_ARCHIVES}/{int(cik)}/{acc_clean}/{primary_doc}"
    try:
        resp = _get(url)
        raw = resp.text
    except Exception as e:
        logger.warning(f"Failed to download {url}: {e}")
        return "", ""

    text = _html_to_text(raw)
    cache_dir.mkdir(parents=True, exist_ok=True)
    text_cache.write_text(text, encoding="utf-8")

    return text, ""


def get_filing_sections(cik: str, accession: str, primary_doc: str,
                        form: str = "10-K") -> dict[str, str]:
    """
    Return key sections from a 10-K or 20-F filing.

    10-K sections:  item1 (Business), item1a (Risk Factors), item7 (MD&A)
    20-F sections:  item4 (Information on Company), item3 (Key Info / Risk Factors)

    All forms also return "full" for the complete text and "risk" / "business"
    as normalized aliases so callers don't need to know the form type.
    """
    full_text, _ = get_filing_text(cik, accession, primary_doc)
    if not full_text:
        return {}

    sections: dict[str, str] = {"full": full_text}

    form_upper = form.upper()
    if form_upper == "20-F":
        # 20-F item mapping:
        #   Item 3  = Key Information (includes D. Risk Factors)
        #   Item 4  = Information on the Company (business + customers)
        #   Item 4A = Unresolved Staff Comments
        sections["item3"]    = _extract_section(full_text, "3")
        sections["item4"]    = _extract_section(full_text, "4")
        sections["business"] = sections["item4"]
        sections["risk"]     = sections["item3"]
        sections["item1a"]   = sections["item3"]   # alias for extractor compat
        sections["item1"]    = sections["item4"]   # alias for extractor compat
    else:
        # 10-K item mapping
        sections["item1"]    = _extract_section(full_text, "1")
        sections["item1a"]   = _extract_section(full_text, "1A")
        sections["item7"]    = _extract_section(full_text, "7")
        sections["business"] = sections["item1"]
        sections["risk"]     = sections["item1a"]

    return sections

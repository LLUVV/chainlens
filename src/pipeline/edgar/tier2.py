"""
Tier 2 edge extraction: named (unquantified) supply chain relationships.

Scans Item 1A (Risk Factors) and Item 1 (Business) text for company names
that appear in supply-chain context without a percentage attached.

Returns raw candidates for entity resolution in extractor.py.
"""
from __future__ import annotations

import re
from typing import Optional

# Supply-chain context phrases that must appear near a company name
_SUPPLY_CONTEXT = re.compile(
    r'(?:'
    r'supplier|vendor|manufacturer|foundry|fabricator|assembler|subcontractor|'
    r'contract manufacturer|ODM|OEM|supply chain|sole source|single source|'
    r'outsource|third.party manufacturer|partner|strategic partner|'
    r'procure|procurement|source from|purchased from|contract with'
    r')',
    re.IGNORECASE
)

_CUSTOMER_CONTEXT = re.compile(
    r'(?:'
    r'customer|client|end.customer|OEM customer|reseller|distributor|'
    r'end.market|sell to|sold to|revenue from|purchase our|buy from'
    r')',
    re.IGNORECASE
)

# Window (characters) to search for context around a company name mention
_WINDOW = 200

# Company name pattern: starts with capital, followed by more text
# Intentionally broad — false positives filtered by context check
_COMPANY_NAME = re.compile(
    r'\b([A-Z][A-Za-z0-9]+(?:\s+[A-Z][A-Za-z0-9]+){0,5}'
    r'(?:\s+(?:Inc\.?|Corp\.?|Ltd\.?|Co\.?|LLC|N\.V\.?|plc))?)\b'
)

_MIN_LEN = 4
_MAX_LEN = 60

_STOPWORDS = frozenset({
    "The", "Our", "Their", "Its", "We", "They", "In", "On", "At", "By",
    "For", "To", "Of", "With", "From", "That", "This", "These", "Those",
    "Company", "Business", "Products", "Services", "Operations", "Results",
    "Revenue", "Sales", "Income", "Loss", "Fiscal", "Quarter", "Year",
    "United", "States", "North", "South", "East", "West", "Asia", "China",
    "Taiwan", "Japan", "Korea", "Europe", "March", "December", "January",
    "Management", "Discussion", "Analysis", "Financial", "Statements",
    "Form", "Item", "Part", "Section", "Exhibit", "Note",
    "Risk", "Factor", "Forward", "Looking", "Statement",
})


def extract_tier2_candidates(item1_text: str, item1a_text: str) -> list[dict]:
    """
    Scan business description and risk factors for supply chain company mentions.

    Returns list of dicts:
        company_name: str       raw extracted name
        direction:    str       "names_supplier" | "names_customer"
        snippet:      str       surrounding context
        source:       str       "item1" | "item1a"
    """
    results = []
    seen = set()

    def scan(text: str, source: str):
        for m in _COMPANY_NAME.finditer(text):
            name = m.group(1).strip()
            if (len(name) < _MIN_LEN or len(name) > _MAX_LEN
                    or name.split()[0] in _STOPWORDS
                    or name in _STOPWORDS):
                continue

            start = max(0, m.start() - _WINDOW)
            end   = min(len(text), m.end() + _WINDOW)
            ctx   = text[start:end]

            is_supplier_ctx = bool(_SUPPLY_CONTEXT.search(ctx))
            is_customer_ctx = bool(_CUSTOMER_CONTEXT.search(ctx))

            if not (is_supplier_ctx or is_customer_ctx):
                continue

            direction = ("names_supplier" if is_supplier_ctx
                         else "names_customer")
            key = (name.lower(), direction)
            if key in seen:
                continue
            seen.add(key)

            snippet = ctx[:150].replace('\n', ' ')
            results.append({
                "company_name": name,
                "direction":    direction,
                "snippet":      snippet,
                "source":       source,
            })

    scan(item1_text,  "item1")
    scan(item1a_text, "item1a")

    return results

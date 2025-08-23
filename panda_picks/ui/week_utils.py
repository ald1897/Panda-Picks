from __future__ import annotations
from typing import Optional
import re

_WEEK_PATTERN = re.compile(r"(?i)^(?:WEEK|WK)?\s*0*(\d+)$")


def extract_week_number(week: str | None) -> Optional[int]:
    """Extract integer week number from various label forms.
    Accepts forms like 'WEEK1', 'Week 01', 'wk3', '3'. Returns None if not parseable.
    """
    if not week:
        return None
    w = str(week).strip().upper().replace(' ', '')
    m = _WEEK_PATTERN.match(w)
    if not m:
        return None
    try:
        return int(m.group(1))
    except ValueError:
        return None


def format_week_standard(week: str | None, zero_pad: bool = True) -> str:
    """Return canonical week label: WEEK## (zero padded if requested) or original string if unparseable."""
    n = extract_week_number(week)
    if n is None:
        return week or ''
    return f"WEEK{n:02d}" if zero_pad else f"WEEK{n}"


def week_sort_key(week: str) -> int:
    """Key function for sorting week labels robustly."""
    n = extract_week_number(week)
    return n if n is not None else 0


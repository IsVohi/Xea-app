"""
Xea Governance Oracle - Utility Functions

Common utilities used across the application.
"""

import hashlib
import json
import re
from datetime import datetime
from typing import Any, Optional


def generate_job_id() -> str:
    """Generate a unique job ID."""
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    import secrets
    suffix = secrets.token_hex(4)
    return f"job_{timestamp}_{suffix}"


def generate_claim_id(index: int) -> str:
    """Generate a claim ID for a given index."""
    return f"claim_{index:03d}"


def sha256_hash(data: str) -> str:
    """Compute SHA-256 hash of string data."""
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def json_serialize(obj: Any) -> str:
    """Serialize object to canonical JSON string."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


def extract_paragraphs(text: str) -> list[str]:
    """Split text into paragraphs."""
    paragraphs = re.split(r"\n\s*\n", text.strip())
    return [p.strip() for p in paragraphs if p.strip()]


def find_char_range(text: str, substring: str) -> Optional[tuple[int, int]]:
    """Find character range of substring in text."""
    start = text.find(substring)
    if start == -1:
        return None
    return (start, start + len(substring))


def clamp(value: float, min_val: float = 0.0, max_val: float = 1.0) -> float:
    """Clamp a value to a range."""
    return max(min_val, min(max_val, value))


def format_timestamp(dt: Optional[datetime] = None) -> str:
    """Format datetime to ISO string."""
    if dt is None:
        dt = datetime.utcnow()
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")

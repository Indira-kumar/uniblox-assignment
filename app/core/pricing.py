"""Pure integer-cent calculations shared by carts and checkout."""

import hashlib
import json
from collections.abc import Sequence

MAX_MONEY_CENTS = 2**63 - 1


def line_total_cents(quantity: int, unit_price_cents: int) -> int:
    return quantity * unit_price_cents


def make_quote_token(version: int, lines: Sequence[tuple[int, str, int, int]]) -> str:
    """Fingerprint the cart version and its current product details."""
    payload = {"version": version, "lines": sorted(lines)}
    encoded = json.dumps(payload, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()

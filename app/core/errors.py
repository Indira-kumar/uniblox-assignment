"""Business errors with a stable HTTP representation."""

from dataclasses import dataclass, field
from typing import Any


@dataclass(eq=False)
class DomainError(Exception):
    code: str
    message: str
    status_code: int
    details: dict[str, Any] = field(default_factory=dict)

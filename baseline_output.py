"""Minimal output contract for the binary retouching baseline."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping


SCHEMA_VERSION = "1.0.0"


def _confidence(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("confidence must be a number between 0 and 1")
    value = float(value)
    if not 0.0 <= value <= 1.0:
        raise ValueError("confidence must be between 0 and 1")
    return value


@dataclass(frozen=True)
class BaselineOutput:
    """Answer only whether an image was retouched."""

    is_retouched: bool
    confidence: float
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not isinstance(self.is_retouched, bool):
            raise ValueError("is_retouched must be a boolean")
        object.__setattr__(self, "confidence", _confidence(self.confidence))
        if self.schema_version != SCHEMA_VERSION:
            raise ValueError(f"schema_version must be {SCHEMA_VERSION}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "is_retouched": self.is_retouched,
            "confidence": self.confidence,
        }

    def to_json(self, *, indent: int | None = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "BaselineOutput":
        if not isinstance(data, Mapping):
            raise ValueError("baseline output must be an object")
        required = {"schema_version", "is_retouched", "confidence"}
        unknown = set(data) - required
        if unknown:
            raise ValueError(
                "baseline output contains unknown field(s): "
                + ", ".join(sorted(unknown))
            )
        missing = required - set(data)
        if missing:
            raise ValueError("baseline output is missing: " + ", ".join(sorted(missing)))
        return cls(
            schema_version=data["schema_version"],
            is_retouched=data["is_retouched"],
            confidence=data["confidence"],
        )

    @classmethod
    def from_json(cls, value: str) -> "BaselineOutput":
        try:
            data = json.loads(value)
        except json.JSONDecodeError as exc:
            raise ValueError("baseline output is not valid JSON") from exc
        return cls.from_dict(data)


def load_json_schema() -> dict[str, Any]:
    schema_path = Path(__file__).with_name("docs") / "baseline-output.schema.json"
    return json.loads(schema_path.read_text(encoding="utf-8"))

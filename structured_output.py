"""Detailed, versioned output contract for AIGC/filter detection.

This is the extended target format. The smaller binary baseline lives in
``baseline_output.py``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum, IntEnum
from pathlib import Path
from typing import Any, Mapping, Sequence


SCHEMA_VERSION = "1.0.0"


class Prediction(str, Enum):
    REAL = "real"
    FAKE = "fake"
    FILTER_PROCESSED = "filter_processed"


class RetouchingType(str, Enum):
    EYE_ENLARGING = "eye_enlarging"
    FACE_LIFTING = "face_lifting"
    SKIN_SMOOTHING = "skin_smoothing"
    FACE_WHITENING = "face_whitening"


class RetouchingLevel(IntEnum):
    OFF = 0
    SLIGHT = 30
    MEDIUM = 60
    HEAVY = 90


def _confidence(value: Any, field: str = "confidence") -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be a number between 0 and 1")
    value = float(value)
    if not 0.0 <= value <= 1.0:
        raise ValueError(f"{field} must be between 0 and 1")
    return value


def _strict_keys(data: Mapping[str, Any], allowed: set[str], field: str) -> None:
    unknown = set(data) - allowed
    if unknown:
        raise ValueError(f"{field} contains unknown field(s): {', '.join(sorted(unknown))}")


@dataclass(frozen=True)
class OperationResult:
    level: RetouchingLevel
    confidence: float

    def __post_init__(self) -> None:
        try:
            object.__setattr__(self, "level", RetouchingLevel(self.level))
        except (TypeError, ValueError) as exc:
            raise ValueError("level must be one of 0, 30, 60, or 90") from exc
        object.__setattr__(self, "confidence", _confidence(self.confidence))

    @property
    def level_name(self) -> str:
        return self.level.name.lower()

    def to_dict(self) -> dict[str, Any]:
        return {
            "level": int(self.level),
            "level_name": self.level_name,
            "confidence": self.confidence,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "OperationResult":
        if not isinstance(data, Mapping):
            raise ValueError("operation result must be an object")
        _strict_keys(data, {"level", "level_name", "confidence"}, "operation result")
        try:
            result = cls(level=data["level"], confidence=data["confidence"])
        except KeyError as exc:
            raise ValueError(f"operation result is missing {exc.args[0]}") from exc
        if data.get("level_name", result.level_name) != result.level_name:
            raise ValueError("level_name does not match level")
        return result


@dataclass(frozen=True)
class SuspiciousRegion:
    region: str
    confidence: float

    def __post_init__(self) -> None:
        if not isinstance(self.region, str) or not self.region.strip():
            raise ValueError("region must be a non-empty string")
        object.__setattr__(self, "confidence", _confidence(self.confidence))

    def to_dict(self) -> dict[str, Any]:
        return {"region": self.region, "confidence": self.confidence}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "SuspiciousRegion":
        if not isinstance(data, Mapping):
            raise ValueError("suspicious region must be an object")
        _strict_keys(data, {"region", "confidence"}, "suspicious region")
        try:
            return cls(region=data["region"], confidence=data["confidence"])
        except KeyError as exc:
            raise ValueError(f"suspicious region is missing {exc.args[0]}") from exc


@dataclass(frozen=True)
class DetectionOutput:
    prediction: Prediction
    confidence: float
    retouching: Mapping[RetouchingType, OperationResult]
    suspicious_regions: Sequence[SuspiciousRegion]
    explanation: str
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        try:
            object.__setattr__(self, "prediction", Prediction(self.prediction))
        except (TypeError, ValueError) as exc:
            raise ValueError("prediction must be real, fake, or filter_processed") from exc
        object.__setattr__(self, "confidence", _confidence(self.confidence))
        if self.schema_version != SCHEMA_VERSION:
            raise ValueError(f"schema_version must be {SCHEMA_VERSION}")
        if not isinstance(self.explanation, str) or not self.explanation.strip():
            raise ValueError("explanation must be a non-empty string")

        try:
            normalized = {
                RetouchingType(key): value
                if isinstance(value, OperationResult)
                else OperationResult.from_dict(value)
                for key, value in self.retouching.items()
            }
        except (AttributeError, TypeError, ValueError) as exc:
            raise ValueError("retouching must map each canonical operation to a result") from exc

        expected = set(RetouchingType)
        if set(normalized) != expected:
            missing = sorted(item.value for item in expected - set(normalized))
            raise ValueError(
                "retouching must contain exactly four operations"
                + (f" (missing: {', '.join(missing)})" if missing else "")
            )

        regions = tuple(
            item if isinstance(item, SuspiciousRegion) else SuspiciousRegion.from_dict(item)
            for item in self.suspicious_regions
        )
        object.__setattr__(self, "retouching", normalized)
        object.__setattr__(self, "suspicious_regions", regions)

    @property
    def artifact_types(self) -> list[str]:
        return [kind.value for kind, result in self.retouching.items() if result.level]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "prediction": self.prediction.value,
            "confidence": self.confidence,
            "retouching": {
                kind.value: self.retouching[kind].to_dict() for kind in RetouchingType
            },
            "suspicious_regions": [region.to_dict() for region in self.suspicious_regions],
            "artifact_types": self.artifact_types,
            "explanation": self.explanation,
        }

    def to_json(self, *, indent: int | None = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "DetectionOutput":
        if not isinstance(data, Mapping):
            raise ValueError("detection output must be an object")
        required = {
            "schema_version", "prediction", "confidence", "retouching",
            "suspicious_regions", "artifact_types", "explanation",
        }
        _strict_keys(data, required, "detection output")
        missing = required - set(data)
        if missing:
            raise ValueError(f"detection output is missing: {', '.join(sorted(missing))}")
        result = cls(
            schema_version=data["schema_version"],
            prediction=data["prediction"],
            confidence=data["confidence"],
            retouching=data["retouching"],
            suspicious_regions=data["suspicious_regions"],
            explanation=data["explanation"],
        )
        if data["artifact_types"] != result.artifact_types:
            raise ValueError("artifact_types does not match the non-zero retouching levels")
        return result

    @classmethod
    def from_json(cls, value: str) -> "DetectionOutput":
        try:
            data = json.loads(value)
        except json.JSONDecodeError as exc:
            raise ValueError("detection output is not valid JSON") from exc
        return cls.from_dict(data)


def load_json_schema() -> dict[str, Any]:
    schema_path = Path(__file__).with_name("docs") / "structured-output.schema.json"
    return json.loads(schema_path.read_text(encoding="utf-8"))

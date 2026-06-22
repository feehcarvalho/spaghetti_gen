"""Analysis consolidation, validation and improvement helpers.

Imports are resolved lazily to avoid circular imports between AI schemas and
analysis consolidation modules.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any


__all__ = [
    "assert_analysis_can_generate_excel",
    "consolidate_window_analyses",
    "detect_generic_or_repeated_analysis",
    "generate_improvements_from_waste",
    "validate_sps_analysis",
]


def __getattr__(name: str) -> Any:
    if name == "consolidate_window_analyses":
        return getattr(import_module("app.analysis.consolidator"), name)
    if name == "generate_improvements_from_waste":
        return getattr(import_module("app.analysis.improvements"), name)
    if name in {
        "assert_analysis_can_generate_excel",
        "detect_generic_or_repeated_analysis",
        "validate_sps_analysis",
    }:
        return getattr(import_module("app.analysis.sps_validator"), name)
    raise AttributeError(name)

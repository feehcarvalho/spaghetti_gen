"""Providers e utilitarios de analise por IA.

Exports are lazy to keep window-analysis schemas importable without pulling the
full OpenAI provider and its analysis consolidation dependencies.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any


__all__ = [
    "AnalysisProvider",
    "AnalysisProviderError",
    "AnalysisRequest",
    "MockAnalysisProvider",
    "OpenAIAnalysisProvider",
    "VideoOverview",
    "WindowAnalysis",
    "WindowMicroStep",
    "build_analysis_prompt",
    "analyze_video_overview",
    "analyze_window_sps",
]


def __getattr__(name: str) -> Any:
    if name in {
        "AnalysisProvider",
        "AnalysisProviderError",
        "AnalysisRequest",
        "MockAnalysisProvider",
        "OpenAIAnalysisProvider",
    }:
        return getattr(import_module("app.ai.analyzer"), name)
    if name == "build_analysis_prompt":
        return getattr(import_module("app.ai.prompt_builder"), name)
    if name in {"VideoOverview", "analyze_video_overview"}:
        return getattr(import_module("app.ai.video_overview"), name)
    if name in {"WindowAnalysis", "WindowMicroStep", "analyze_window_sps"}:
        return getattr(import_module("app.ai.window_analyzer"), name)
    raise AttributeError(name)

"""Runtime data models for Azure Speech-to-Text integration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .sensor import AzureSTTSensor
    from .stt import AzureSpeechSTTEntity


@dataclass
class AzureSTTRuntimeData:
    """Runtime data shared between STT entity and sensor entities."""

    entity: AzureSpeechSTTEntity | None = None
    sensors: list[AzureSTTSensor] = field(default_factory=list)


@dataclass
class TranscriptionStats:
    """Statistics emitted after each transcription attempt."""

    success: bool
    api_error: bool
    correction_applied: bool
    duration_ms: float = 0.0
    audio_bytes: int = 0
    audio_seconds: float = 0.0
    language: str = ""
    api_used: str = ""
    raw_text: str | None = None
    corrected_text: str | None = None
    avg_duration_ms: float | None = None

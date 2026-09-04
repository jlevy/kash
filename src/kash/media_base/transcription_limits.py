from __future__ import annotations

from dataclasses import dataclass, replace

DEFAULT_TIMEOUT_FLOOR_S = 500.0
"""Minimum request budget, and what short files use. Matches the historical fixed value."""

DEFAULT_TIMEOUT_PER_HOUR_S = 900.0
"""Additional budget per hour of audio."""

DEFAULT_TIMEOUT_CEILING_S = 7200.0
"""Upper bound, so an implausible duration cannot hang a run indefinitely."""


@dataclass(frozen=True)
class TranscriptionLimits:
    """
    Transport policy for a transcription request: how long to wait, not what to produce.

    Deliberately separate from `TranscriptionSettings`, which affects the transcript and
    is hashed into the cache key. Waiting longer must never invalidate a cached
    transcript, so these knobs live here instead.

    A provider transcribes in roughly linear time, so a single fixed timeout either
    starves long audio or wastes a caller's time on short audio. The default budget is
    therefore a floor plus an allowance per hour, bounded by a ceiling. Callers who know
    their provider or their patience can override any part, or pin `timeout_s` outright.
    """

    timeout_s: float | None = None
    """Explicit budget in seconds. When set, it wins and no scaling is applied."""

    timeout_floor_s: float = DEFAULT_TIMEOUT_FLOOR_S
    """Minimum budget, used as-is when the audio duration is unknown."""

    timeout_per_hour_s: float = DEFAULT_TIMEOUT_PER_HOUR_S
    """Budget added per hour of audio."""

    timeout_ceiling_s: float = DEFAULT_TIMEOUT_CEILING_S
    """Maximum budget, however long the audio is."""

    def timeout_for(self, audio_duration_s: float | None) -> float:
        """
        Request budget for audio of the given duration.

        Falls back to the floor when the duration is unknown, so a caller that cannot
        probe its audio behaves exactly as a fixed-timeout caller always did.
        """
        if self.timeout_s is not None:
            return self.timeout_s
        if not audio_duration_s or audio_duration_s <= 0:
            return self.timeout_floor_s
        budget = self.timeout_floor_s + (audio_duration_s / 3600.0) * self.timeout_per_hour_s
        return min(budget, self.timeout_ceiling_s)

    def with_timeout(self, timeout_s: float | None) -> TranscriptionLimits:
        """A copy pinned to an explicit budget."""
        return replace(self, timeout_s=timeout_s)


DEFAULT_LIMITS = TranscriptionLimits()
"""Used whenever a caller passes no limits, so every existing call site keeps working."""


## Tests


def test_timeout_scales_with_duration_and_respects_bounds() -> None:
    limits = TranscriptionLimits()

    # Unknown duration behaves exactly like the historical fixed timeout.
    assert limits.timeout_for(None) == DEFAULT_TIMEOUT_FLOOR_S
    assert limits.timeout_for(0) == DEFAULT_TIMEOUT_FLOOR_S

    # Short audio stays near the floor; long audio gets real room.
    assert limits.timeout_for(240) == DEFAULT_TIMEOUT_FLOOR_S + 60.0
    assert limits.timeout_for(3600) == DEFAULT_TIMEOUT_FLOOR_S + DEFAULT_TIMEOUT_PER_HOUR_S

    # A six-hour podcast gets far more than the old fixed budget, under the ceiling.
    six_hours = limits.timeout_for(6 * 3600)
    assert six_hours > 5000
    assert six_hours <= DEFAULT_TIMEOUT_CEILING_S

    # The ceiling binds for implausible durations.
    assert limits.timeout_for(1_000_000) == DEFAULT_TIMEOUT_CEILING_S


def test_explicit_timeout_wins_over_scaling() -> None:
    pinned = TranscriptionLimits(timeout_s=42.0)

    assert pinned.timeout_for(None) == 42.0
    assert pinned.timeout_for(6 * 3600) == 42.0
    assert TranscriptionLimits().with_timeout(90.0).timeout_for(3600) == 90.0


def test_callers_can_tune_each_knob() -> None:
    patient = TranscriptionLimits(timeout_floor_s=60.0, timeout_per_hour_s=1800.0)

    assert patient.timeout_for(None) == 60.0
    assert patient.timeout_for(3600) == 1860.0

"""AI disclosure for synthetic voices and presenters (``docs/GROWTH.md`` §6).

A render carries a synthetic element when it mixes a generated voiceover or shows a generated
presenter. ``render_video`` records that on the content item; ``publish_video`` reads the stored
state (it never re-derives it, so a later publish to a second platform discloses the same
thing), sets the platform's AI-content flag where the publishing API has one, and — always,
on every platform — appends the disclosure line to the caption.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from .state import ContentItem

VOICE_LINE = "Voiceover generated with AI."
PRESENTER_LINE = "Presenter generated with AI."
BOTH_LINE = "Voiceover and presenter generated with AI."


class Disclosure(BaseModel):
    """What is synthetic in a render and how it must be disclosed."""

    synthetic_voice: bool = False
    synthetic_presenter: bool = False
    line: str | None = Field(
        default=None, description="Caption line appended on every platform when synthetic"
    )

    @property
    def is_synthetic(self) -> bool:
        return self.synthetic_voice or self.synthetic_presenter


def disclosure_for(*, has_voiceover: bool, presenter: str) -> Disclosure:
    voice = bool(has_voiceover)
    presenter_synthetic = presenter == "avatar_clip"
    if voice and presenter_synthetic:
        line = BOTH_LINE
    elif voice:
        line = VOICE_LINE
    elif presenter_synthetic:
        line = PRESENTER_LINE
    else:
        line = None
    return Disclosure(synthetic_voice=voice, synthetic_presenter=presenter_synthetic, line=line)


def stored_disclosure(item: ContentItem) -> Disclosure:
    """The disclosure recorded at render time; an unrendered item discloses nothing."""
    data: dict[str, Any] = item.disclosure or {}
    return Disclosure.model_validate(data) if data else Disclosure()

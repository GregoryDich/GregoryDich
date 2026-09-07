"""Stem scoring: documented components and the overall ranking."""

from __future__ import annotations

from mcp_server.scoring import (
    choose_stem,
    density_score,
    loudness_score,
    pitch_range_score,
    score_stems,
)
from mcp_server.snapplay import JobResult
from tests.conftest import make_job_result


def test_density_component_shape() -> None:
    assert density_score(0) == 0
    assert density_score(1) == 0.5
    assert density_score(2) == 1
    assert density_score(6) == 1
    assert 0 < density_score(10) < 1
    assert density_score(16) == 0


def test_pitch_range_component_shape() -> None:
    assert pitch_range_score(0) == 0
    assert pitch_range_score(6) == 0.5
    assert pitch_range_score(12) == 1
    assert pitch_range_score(36) == 1
    assert pitch_range_score(60) == 0


def test_loudness_component_shape() -> None:
    assert loudness_score(None) == 0
    assert loudness_score(-45) == 0
    assert loudness_score(-30) == 0.5
    assert loudness_score(-15) == 1
    assert loudness_score(0) == 1


def test_bass_wins_over_noisy_and_silent_stems() -> None:
    result = JobResult.model_validate(make_job_result())
    ranked = score_stems(result)
    assert ranked[0].name == "bass"
    by_name = {s.name: s for s in ranked}
    assert by_name["drums"].score == 0  # no transcribed notes → unusable
    assert by_name["drums"].note_count == 0
    assert by_name["other"].score < by_name["bass"].score  # 10 notes/s over 4 octaves
    assert by_name["vocals"].components["loudness"] == 0  # -60 dBFS
    assert choose_stem(result).name == "bass"
    assert set(by_name["bass"].components) == {"density", "pitch_range", "loudness"}


def test_tie_breaks_follow_stem_preference() -> None:
    data = make_job_result()
    data["midi"]["tracks"] = [
        {"name": "other", "channel": 0, "notes": data["midi"]["tracks"][0]["notes"]},
        {"name": "bass", "channel": 1, "notes": data["midi"]["tracks"][0]["notes"]},
    ]
    for stem in data["stems"]:
        stem["rms_db"] = -18.0
    ranked = score_stems(JobResult.model_validate(data))
    assert ranked[0].name == "bass"
    assert ranked[0].score == ranked[1].score
    assert ranked[1].name == "other"

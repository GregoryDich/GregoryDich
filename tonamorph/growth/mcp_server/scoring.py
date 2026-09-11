"""Pick the most usable stem for a short from the JobResult fields alone.

Score = 0.4 * density + 0.3 * pitch_range + 0.3 * loudness, each component in [0, 1]:

* density (notes per second of the stem): a hook needs visible key activity but not a
  smear. 0 notes/s scores 0, 2 notes/s scores 1, the plateau holds to 6 notes/s, and the score
  decays linearly to 0 at 16 notes/s (dense transcriptions are usually harmonic noise).
* pitch_range (max pitch - min pitch in semitones): a single repeated pitch scores 0, one
  octave scores 1, the plateau holds to three octaves, then decays to 0 at five octaves
  (very wide ranges indicate octave errors from the transcriber).
* loudness (stem ``rms_db``): -45 dBFS scores 0, -15 dBFS scores 1, linear between.

A stem with no transcribed notes is unusable and scores 0 regardless of loudness. Ties are
broken by ``STEM_PREFERENCE`` (bass reads best on a piano roll, drums worst).
"""

from __future__ import annotations

from pydantic import BaseModel

from .tonamorph import JobResult

STEM_PREFERENCE: tuple[str, ...] = ("bass", "other", "vocals", "drums")
WEIGHTS = {"density": 0.4, "pitch_range": 0.3, "loudness": 0.3}


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def density_score(notes_per_second: float) -> float:
    if notes_per_second <= 0:
        return 0.0
    if notes_per_second <= 2.0:
        return notes_per_second / 2.0
    if notes_per_second <= 6.0:
        return 1.0
    return _clamp(1.0 - (notes_per_second - 6.0) / 10.0)


def pitch_range_score(semitones: int) -> float:
    if semitones <= 0:
        return 0.0
    if semitones <= 12:
        return semitones / 12.0
    if semitones <= 36:
        return 1.0
    return _clamp(1.0 - (semitones - 36) / 24.0)


def loudness_score(rms_db: float | None) -> float:
    if rms_db is None:
        return 0.0
    return _clamp((rms_db + 45.0) / 30.0)


class StemScore(BaseModel):
    name: str
    score: float
    note_count: int
    notes_per_second: float
    pitch_range_semitones: int
    rms_db: float | None
    components: dict[str, float]


def score_stems(result: JobResult) -> list[StemScore]:
    """Score every stem of a JobResult, best first."""
    scored: list[StemScore] = []
    for stem in result.stems:
        track = result.track_for(stem.name)
        notes = track.notes if track else []
        duration = stem.duration_seconds or result.input.duration_seconds or 0.0
        nps = len(notes) / duration if duration > 0 else 0.0
        pitches = [n.pitch for n in notes]
        pitch_range = (max(pitches) - min(pitches)) if pitches else 0
        components = {
            "density": density_score(nps),
            "pitch_range": pitch_range_score(pitch_range),
            "loudness": loudness_score(stem.rms_db),
        }
        total = sum(WEIGHTS[k] * v for k, v in components.items()) if notes else 0.0
        scored.append(
            StemScore(
                name=stem.name,
                score=round(total, 4),
                note_count=len(notes),
                notes_per_second=round(nps, 3),
                pitch_range_semitones=pitch_range,
                rms_db=stem.rms_db,
                components={k: round(v, 4) for k, v in components.items()},
            )
        )

    def rank(s: StemScore) -> tuple[float, int]:
        pref = STEM_PREFERENCE.index(s.name) if s.name in STEM_PREFERENCE else len(STEM_PREFERENCE)
        return (-s.score, pref)

    return sorted(scored, key=rank)


def choose_stem(result: JobResult) -> StemScore:
    ranked = score_stems(result)
    if not ranked:
        raise ValueError("job result contains no stems")
    return ranked[0]

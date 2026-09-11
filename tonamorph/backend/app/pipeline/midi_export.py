"""Standard MIDI File output shared by every backend (contract §9: type 1, PPQ 480,
tempo and 4/4 time-signature meta events, one track per transcribed stem)."""

from __future__ import annotations

import io

import mido

from app.pipeline.analysis import Note
from app.schemas import MidiInfo, MidiNote, MidiTrack

PPQ = 480
DRUM_CHANNEL = 9
TIME_SIGNATURE = (4, 4)


def ticks(seconds: float, bpm: float, ppq: int = PPQ) -> int:
    return int(round(seconds * bpm / 60.0 * ppq))


def to_midi_note(note: Note, bpm: float, ppq: int = PPQ) -> MidiNote:
    return MidiNote(
        start_seconds=round(note.start_seconds, 3),
        duration_seconds=round(note.duration_seconds, 3),
        start_ticks=ticks(note.start_seconds, bpm, ppq),
        duration_ticks=max(1, ticks(note.duration_seconds, bpm, ppq)),
        pitch=note.pitch,
        velocity=note.velocity,
    )


def build_tracks(
    notes_by_stem: dict[str, list[Note]], order: list[str], bpm: float, ppq: int = PPQ
) -> list[MidiTrack]:
    """One track per stem in ``order`` (stems missing from ``notes_by_stem`` are skipped);
    drums go to channel 9, melodic stems to 0, 1, 2… in order."""
    tracks: list[MidiTrack] = []
    melodic = 0
    for name in order:
        if name not in notes_by_stem:
            continue
        if name == "drums":
            channel = DRUM_CHANNEL
        else:
            channel = min(melodic, 15)
            melodic += 1
        notes = [to_midi_note(n, bpm, ppq) for n in notes_by_stem[name]]
        tracks.append(MidiTrack(name=name, channel=channel, notes=notes))
    return tracks


def smf_bytes(bpm: float, tracks: list[MidiTrack], ppq: int = PPQ) -> bytes:
    mf = mido.MidiFile(type=1, ticks_per_beat=ppq)
    meta = mido.MidiTrack()
    meta.append(mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(bpm), time=0))
    meta.append(
        mido.MetaMessage(
            "time_signature", numerator=TIME_SIGNATURE[0], denominator=TIME_SIGNATURE[1], time=0
        )
    )
    meta.append(mido.MetaMessage("end_of_track", time=0))
    mf.tracks.append(meta)
    for track in tracks:
        events: list[tuple[int, int, str, int, int]] = []
        for note in track.notes:
            events.append((note.start_ticks, 1, "note_on", note.pitch, note.velocity))
            events.append((note.start_ticks + note.duration_ticks, 0, "note_off", note.pitch, 0))
        events.sort()
        mt = mido.MidiTrack()
        mt.append(mido.MetaMessage("track_name", name=track.name, time=0))
        last = 0
        for tick, _, kind, pitch, velocity in events:
            mt.append(
                mido.Message(
                    kind, note=pitch, velocity=velocity, channel=track.channel, time=tick - last
                )
            )
            last = tick
        mt.append(mido.MetaMessage("end_of_track", time=0))
        mf.tracks.append(mt)
    buf = io.BytesIO()
    mf.save(file=buf)
    return buf.getvalue()


def build_midi(
    notes_by_stem: dict[str, list[Note]], order: list[str], bpm: float, ppq: int = PPQ
) -> MidiInfo:
    """The contract ``midi`` block with ``smf_bytes`` populated."""
    tracks = build_tracks(notes_by_stem, order, bpm, ppq)
    return MidiInfo(ppq=ppq, bpm=bpm, tracks=tracks, smf_bytes=smf_bytes(bpm, tracks, ppq))


__all__ = [
    "DRUM_CHANNEL",
    "PPQ",
    "build_midi",
    "build_tracks",
    "smf_bytes",
    "ticks",
    "to_midi_note",
]

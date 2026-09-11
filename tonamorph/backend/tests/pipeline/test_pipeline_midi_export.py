import io

import mido

from app.pipeline.analysis import Note
from app.pipeline.midi_export import build_midi, smf_bytes, ticks


def test_ticks_at_ppq_480() -> None:
    assert ticks(0.5, 120.0) == 480
    assert ticks(1.0, 90.0) == 720


def test_build_midi_round_trip() -> None:
    notes = {
        "bass": [Note(0.0, 0.5, 41, 100), Note(0.5, 0.25, 43, 90)],
        "drums": [Note(0.0, 0.1, 36, 100), Note(0.25, 0.1, 37, 100)],
    }
    midi = build_midi(notes, ["bass", "drums", "vocals"], 120.0)
    assert midi.ppq == 480 and midi.bpm == 120.0
    assert [(t.name, t.channel) for t in midi.tracks] == [("bass", 0), ("drums", 9)]
    first, second = midi.tracks[0].notes
    assert (first.start_ticks, first.duration_ticks) == (0, 480)
    assert (second.start_ticks, second.duration_ticks) == (480, 240)

    parsed = mido.MidiFile(file=io.BytesIO(midi.smf_bytes))
    assert parsed.type == 1 and parsed.ticks_per_beat == 480
    meta = {m.type: m for m in parsed.tracks[0]}
    assert meta["set_tempo"].tempo == 500000
    assert (meta["time_signature"].numerator, meta["time_signature"].denominator) == (4, 4)

    bass_track = parsed.tracks[1]
    assert bass_track[0].type == "track_name" and bass_track[0].name == "bass"
    absolute = 0
    events = []
    for message in bass_track:
        absolute += message.time
        if message.type in {"note_on", "note_off"}:
            events.append((absolute, message.type, message.note, message.channel))
    assert events == [
        (0, "note_on", 41, 0),
        (480, "note_off", 41, 0),
        (480, "note_on", 43, 0),
        (720, "note_off", 43, 0),
    ]
    drum_channels = {m.channel for m in parsed.tracks[2] if m.type == "note_on"}
    assert drum_channels == {9}


def test_smf_without_tracks_is_valid() -> None:
    parsed = mido.MidiFile(file=io.BytesIO(smf_bytes(100.0, [])))
    assert len(parsed.tracks) == 1 and parsed.tracks[0][0].type == "set_tempo"

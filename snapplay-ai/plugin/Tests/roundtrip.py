#!/usr/bin/env python3
"""Validates the export samples written by snapplay_core_tests.

Usage:
    SNAPPLAY_TEST_OUT=<dir> ./snapplay_core_tests && python3 roundtrip.py <dir>

The test binary writes sample.mid, sample.fsc and fixture.json (the notes it serialised).
This script re-reads the .mid with mido and the .fsc with pyflp's event parser (plus a
byte-level reader of the FLhd/FLdt chunks) and checks that every field round-trips.
"""

from __future__ import annotations

import json
import math
import struct
import sys
from pathlib import Path
from typing import Any

FL_VERSION_EVENT = 199
PATTERN_NOTES_EVENT = 224
NOTE_RECORD = struct.Struct("<IHHIHHBBBBBBBB")  # pyflp.pattern.NotesEvent.STRUCT
NOTE_FIELDS = (
    "position", "flags", "rack_channel", "length", "key", "group", "fine_pitch", "u1",
    "release", "midi_channel", "pan", "velocity", "mod_x", "mod_y",
)
NOTE_DEFAULTS = {"flags": 0x4000, "group": 0, "fine_pitch": 120, "u1": 0, "release": 64,
                 "pan": 64, "mod_x": 128, "mod_y": 128}


def lround(value: float) -> int:
    """Round half away from zero for non-negative values, like std::lround."""
    return int(math.floor(value + 0.5))


def seconds_to_ticks(seconds: float, bpm: float, ppq: int) -> int:
    return 0 if seconds <= 0 else lround(seconds * bpm / 60 * ppq)


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


# --------------------------------------------------------------------------- .mid

def expected_midi_events(track: dict[str, Any], bpm: float, ppq: int) -> list[tuple[int, int, int, int]]:
    """(tick, order, pitch, velocity) with order 0 = note-off, 1 = note-on, sorted like the writer."""
    events: list[tuple[int, int, int, int]] = []
    for note in track["notes"]:
        if note["duration_ticks"] > 0:
            start, duration = max(0, note["start_ticks"]), note["duration_ticks"]
        else:
            start = seconds_to_ticks(note["start_seconds"], bpm, ppq)
            duration = seconds_to_ticks(note["duration_seconds"], bpm, ppq)
        end = start + max(1, duration)
        events.append((start, 1, note["pitch"], note["velocity"]))
        events.append((end, 0, note["pitch"], 64))
    return sorted(events, key=lambda e: (e[0], e[1]))


def check_midi(path: Path, fixture: dict[str, Any]) -> int:
    import mido

    bpm, ppq = fixture["bpm"], fixture["midi_ppq"]
    midi = mido.MidiFile(path)
    check(midi.type == 1, f"expected SMF type 1, got {midi.type}")
    check(midi.ticks_per_beat == ppq, f"expected PPQ {ppq}, got {midi.ticks_per_beat}")
    check(len(midi.tracks) == 1 + len(fixture["tracks"]),
          f"expected {1 + len(fixture['tracks'])} tracks, got {len(midi.tracks)}")

    tempo_track = midi.tracks[0]
    tempos = [m for m in tempo_track if m.type == "set_tempo"]
    check(len(tempos) == 1 and tempos[0].tempo == lround(60_000_000 / bpm),
          f"tempo meta mismatch: {tempos}")
    signatures = [m for m in tempo_track if m.type == "time_signature"]
    check(len(signatures) == 1 and (signatures[0].numerator, signatures[0].denominator) == (4, 4),
          f"time signature mismatch: {signatures}")
    check(tempo_track[-1].type == "end_of_track", "tempo track lacks end_of_track")

    total_notes = 0
    for index, track_fixture in enumerate(fixture["tracks"]):
        track = midi.tracks[index + 1]
        names = [m.name for m in track if m.type == "track_name"]
        check(names == [track_fixture["name"]], f"track {index}: name {names}")
        check(track[-1].type == "end_of_track", f"track {index}: missing end_of_track")

        actual: list[tuple[int, int, int, int]] = []
        tick = 0
        for message in track:
            tick += message.time
            if message.type in ("note_on", "note_off"):
                check(message.channel == track_fixture["channel"],
                      f"track {index}: channel {message.channel} != {track_fixture['channel']}")
                actual.append((tick, 1 if message.type == "note_on" else 0, message.note, message.velocity))

        expected = expected_midi_events(track_fixture, bpm, ppq)
        check(actual == expected, f"track {index}: events differ\n  got      {actual}\n  expected {expected}")
        for earlier, later in zip(actual, actual[1:]):
            if earlier[0] == later[0]:
                check(earlier[1] <= later[1], f"track {index}: note-on before note-off at tick {earlier[0]}")
        total_notes += len(track_fixture["notes"])

    return total_notes


# --------------------------------------------------------------------------- .fsc

def read_fsc_raw(data: bytes) -> tuple[int, int, int, list[tuple[int, bytes]]]:
    """Byte-level reader mirroring pyflp.parse(): header, chunk sizes and event framing."""
    magic, header_size, fmt, channel_count, ppq = struct.unpack_from("<4sIhHH", data, 0)
    check(magic == b"FLhd", f"bad header magic {magic!r}")
    check(header_size == 6, f"bad header size {header_size}")
    check(data[14:18] == b"FLdt", "missing FLdt chunk")
    (events_size,) = struct.unpack_from("<I", data, 18)
    check(len(data) == events_size + 22, f"FLdt size {events_size} does not match file size {len(data)}")

    events: list[tuple[int, bytes]] = []
    pos = 22
    while pos < len(data):
        event_id = data[pos]
        pos += 1
        if event_id < 64:
            size = 1
        elif event_id < 128:
            size = 2
        elif event_id < 192:
            size = 4
        else:
            size, shift = 0, 0
            while True:
                byte = data[pos]
                pos += 1
                size |= (byte & 0x7F) << shift
                shift += 7
                if not byte & 0x80:
                    break
        events.append((event_id, data[pos:pos + size]))
        pos += size
    check(pos == len(data), "event stream overran the file")
    return fmt, channel_count, ppq, events


def expected_fsc_records(fixture: dict[str, Any]) -> list[dict[str, int]]:
    bpm, ppq = fixture["bpm"], fixture["fsc_ppq"]
    records: list[dict[str, int]] = []
    for rack_channel, track in enumerate(fixture["tracks"]):
        for note in track["notes"]:
            record = dict(NOTE_DEFAULTS)
            record.update(
                position=seconds_to_ticks(note["start_seconds"], bpm, ppq),
                length=max(1, seconds_to_ticks(note["duration_seconds"], bpm, ppq)),
                rack_channel=rack_channel,
                key=note["pitch"],
                midi_channel=track["channel"],
                velocity=note["velocity"],
            )
            records.append(record)
    return sorted(records, key=lambda r: r["position"])  # sorted() is stable, like std::stable_sort


def check_fsc(path: Path, fixture: dict[str, Any]) -> tuple[int, str]:
    data = path.read_bytes()
    fmt, channel_count, ppq, events = read_fsc_raw(data)
    check(fmt == 0x10, f"format {fmt:#x} != 0x10 (Score)")
    check(channel_count == len(fixture["tracks"]), f"channel count {channel_count}")
    check(ppq == fixture["fsc_ppq"], f"ppq {ppq}")
    check([e[0] for e in events] == [FL_VERSION_EVENT, PATTERN_NOTES_EVENT], f"event ids {[e[0] for e in events]}")
    check(events[0][1] == fixture["fl_version"].encode("ascii") + b"\0", f"version payload {events[0][1]!r}")

    payload = events[1][1]
    check(len(payload) % NOTE_RECORD.size == 0, f"notes payload {len(payload)} not a multiple of 24")
    raw_records = [dict(zip(NOTE_FIELDS, values)) for values in NOTE_RECORD.iter_unpack(payload)]
    expected = expected_fsc_records(fixture)
    check(raw_records == expected, f"note records differ\n  got      {raw_records}\n  expected {expected}")

    parser = "raw reader"
    try:
        import pyflp
        from pyflp.pattern import PatternID
        from pyflp.project import FileFormat
    except ImportError:
        return len(raw_records), parser

    try:
        project = pyflp.parse(path)
    except Exception as exc:  # noqa: BLE001 - a rejected bare score falls back to the raw reader
        print(f"  pyflp rejected the score ({type(exc).__name__}: {exc}); raw reader result stands")
        return len(raw_records), parser

    parser = f"pyflp {getattr(pyflp, '__version__', '?')}"
    check(project.format == FileFormat.Score, f"pyflp format {project.format!r}")
    check(project.ppq == fixture["fsc_ppq"], f"pyflp ppq {project.ppq}")
    check(project.channel_count == len(fixture["tracks"]), f"pyflp channel_count {project.channel_count}")
    version = tuple(project.version)
    check(version == tuple(int(p) for p in fixture["fl_version"].split(".")), f"pyflp version {version}")

    note_events = [ie.e for ie in project.events.lst if ie.e.id == PatternID.Notes]
    check(len(note_events) == 1, f"pyflp found {len(note_events)} PatternNotes events")
    pyflp_records = [{field: int(item[field if field != "u1" else "_u1"]) for field in NOTE_FIELDS}
                     for item in note_events[0]]
    check(pyflp_records == expected, f"pyflp note records differ\n  got      {pyflp_records}\n  expected {expected}")
    return len(raw_records), parser


# --------------------------------------------------------------------------- main

def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 2

    directory = Path(argv[1])
    fixture = json.loads((directory / "fixture.json").read_text(encoding="utf-8"))

    midi_notes = check_midi(directory / "sample.mid", fixture)
    print(f"sample.mid: OK ({midi_notes} notes over {len(fixture['tracks'])} tracks, "
          f"PPQ {fixture['midi_ppq']}, {fixture['bpm']} BPM)")

    fsc_notes, parser = check_fsc(directory / "sample.fsc", fixture)
    print(f"sample.fsc: OK ({fsc_notes} note records, PPQ {fixture['fsc_ppq']}, verified with {parser})")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv))
    except AssertionError as failure:
        print(f"ROUNDTRIP FAILED: {failure}")
        sys.exit(1)

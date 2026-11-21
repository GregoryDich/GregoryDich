#!/usr/bin/env python3
"""Launches the clips of a page through Atlas Cloud, all at once, and saves them.

It reads the page's requests.json:
  "frames": {"K0": "<url>", ...}             the ready stills (first and last frames of the clips)
  "launch": {"T1": ["K0", "K1"], ...}        which clip goes from which frame to which
  "clips":  {"T1": {"prompt": "..."}, ...}   the text of each clip
  "clip_resolution": "720p", "clip_seconds": 5   (defaults: 720p, 5)

usage: atlas-clips.py <requests.json> <clips dir> [label ...]     no labels = every clip of "launch"
THIS SPENDS MONEY: each clip is paid. Launch only after the owner's ok on the page's sheet of stills
(the money rule of 21/11), and name the price first. Results: <clips dir>/<label>.mp4 and one line per
clip in <clips dir>/atlas-jobs.jsonl (the prediction id, the status, the address).
"""
import json
import os
import subprocess
import sys

TOOL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "atlas.py")


def main(argv):
    if len(argv) < 2:
        sys.exit(__doc__)
    requests_path, clips_dir, labels = argv[0], argv[1], argv[2:]
    page = json.load(open(requests_path, encoding="utf-8"))
    frames, launch, clips = page["frames"], page["launch"], page["clips"]
    resolution, seconds = page.get("clip_resolution", "720p"), str(page.get("clip_seconds", 5))
    labels = labels or list(launch)
    os.makedirs(clips_dir, exist_ok=True)
    balance = lambda: json.loads(subprocess.run([sys.executable, TOOL, "balance"], capture_output=True,
                                                text=True).stdout or "{}").get("balance")
    before = balance()
    running = {}
    for label in labels:
        first, last = launch[label]
        prompt_file = os.path.join(clips_dir, label + ".prompt.txt")
        with open(prompt_file, "w", encoding="utf-8") as target:
            target.write(clips[label]["prompt"].strip() + "\n")
        command = [sys.executable, TOOL, "video", os.path.join(clips_dir, label + ".mp4"), prompt_file,
                   resolution, seconds, frames[first], frames[last]]
        running[label] = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    failed = 0
    with open(os.path.join(clips_dir, "atlas-jobs.jsonl"), "a", encoding="utf-8") as log:
        for label, process in running.items():
            output = process.communicate()[0].strip().splitlines()
            line = output[-1] if output else "{}"
            try:
                result = json.loads(line)
            except ValueError:
                result = {"status": "error", "error": line[:300]}
            log.write(json.dumps({"label": label, "from_to": launch[label], "result": result}) + "\n")
            good = bool(result.get("saved"))
            failed += 0 if good else 1
            print("%-4s %s  %s  %s" % (label, result.get("status"), result.get("id"),
                                         "saved" if good else (result.get("error") or "NOT saved")))
    after = balance()
    if before is not None and after is not None:
        print("spent %.3f USD on %d clips; balance %.3f" % (before - after, len(labels), after))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

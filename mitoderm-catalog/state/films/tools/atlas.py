#!/usr/bin/env python3
"""Atlas Cloud from the command line: stills, clips, uploads, balance.

The key is read from the environment variable ATLASCLOUD_API_KEY or from the file ~/.atlas_key.
It is never printed and never written anywhere by this tool.

usage:
  atlas.py balance
  atlas.py image <out file> <prompt file> <size> <quality> <image url>...
  atlas.py video <out file> <prompt file> <resolution> <seconds> <first image url> [last image url]
  atlas.py upload <file>                      -> prints the url Atlas gives the file
  atlas.py get <prediction id> <out file>     -> waits for an earlier job and downloads its result

Each run prints one JSON line: the prediction id, the status, the result url, the seconds waited and
the balance before and after, so the price of every job is known at once.
Models: openai/gpt-image-2.6-sunburst/edit and kwaivgi/kling-v4.0/image-to-video; the environment
variables ATLAS_IMAGE_MODEL and ATLAS_VIDEO_MODEL choose others.
"""
import json
import mimetypes
import os
import sys
import time
import urllib.error
import urllib.request
import uuid

API = "https://api.atlascloud.ai/api/v1"
PUBLIC = "https://api.atlascloud.ai/public/v1"
IMAGE_MODEL = os.environ.get("ATLAS_IMAGE_MODEL", "openai/gpt-image-2.6-sunburst/edit")
VIDEO_MODEL = os.environ.get("ATLAS_VIDEO_MODEL", "kwaivgi/kling-v4.0/image-to-video")
DONE = {"completed", "succeeded", "success", "failed", "error", "canceled", "cancelled"}


def key():
    value = os.environ.get("ATLASCLOUD_API_KEY", "").strip()
    if not value:
        try:
            value = open(os.path.expanduser("~/.atlas_key")).read().strip()
        except OSError:
            value = ""
    if not value:
        sys.exit("no Atlas key: set ATLASCLOUD_API_KEY or put it into ~/.atlas_key")
    return value


def call(method, url, body=None, headers=None, timeout=60):
    data = body if isinstance(body, (bytes, type(None))) else json.dumps(body).encode()
    request = urllib.request.Request(url, data=data, method=method)
    request.add_header("Authorization", "Bearer " + key())
    request.add_header("User-Agent", "atlas-cli/1.0")  # the default Python client name is refused (error 1010)
    if body is not None and not isinstance(body, bytes):
        request.add_header("Content-Type", "application/json")
    for name, value in (headers or {}).items():
        request.add_header(name, value)
    for attempt in range(4):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return json.loads(response.read().decode())
        except urllib.error.HTTPError as error:
            text = error.read().decode(errors="replace")[:400]
            if error.code in (429, 500, 502, 503, 504) and attempt < 3:
                time.sleep(2 ** attempt * 2)
                continue
            sys.exit("Atlas answered %d: %s" % (error.code, text))
        except (urllib.error.URLError, TimeoutError) as error:
            if attempt < 3:
                time.sleep(2 ** attempt * 2)
                continue
            sys.exit("Atlas is not reachable: %s" % error)


def balance():
    try:
        return float(call("GET", PUBLIC + "/balance")["available"]["value"])
    except (KeyError, TypeError, ValueError):
        return None


def wait(prediction, out, started, before):
    status, outputs, info = "", [], {}
    for _ in range(400):
        info = call("GET", API + "/model/prediction/" + prediction).get("data") or {}
        status = str(info.get("status", "")).lower()
        if status in DONE:
            break
        time.sleep(4)
    outputs = info.get("outputs") or info.get("output") or []
    if isinstance(outputs, str):
        outputs = [outputs]
    url = outputs[0] if outputs else None
    saved = False
    if url and out and status in ("completed", "succeeded", "success"):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "curl/8"})
            with urllib.request.urlopen(request, timeout=300) as response, open(out, "wb") as target:
                target.write(response.read())
            saved = True
        except Exception as error:  # the download host may not be allowed yet
            print("download failed: %s" % error, file=sys.stderr)
    after = balance()
    print(json.dumps({
        "id": prediction, "status": status, "url": url, "saved": out if saved else None,
        "seconds": round(time.time() - started), "error": info.get("error") or None,
        "balance_before": before, "balance_after": after,
        "cost": round(before - after, 4) if before is not None and after is not None else None,
    }))
    return 0 if saved else 1


def submit(endpoint, body, out):
    before, started = balance(), time.time()
    answer = call("POST", API + endpoint, body)
    prediction = (answer.get("data") or {}).get("id")
    if not prediction:
        sys.exit("no prediction id in the answer: %s" % json.dumps(answer)[:400])
    print(json.dumps({"submitted": prediction, "model": body["model"]}), flush=True)
    return wait(prediction, out, started, before)


def upload(path):
    boundary = uuid.uuid4().hex
    kind = mimetypes.guess_type(path)[0] or "application/octet-stream"
    head = ("--%s\r\nContent-Disposition: form-data; name=\"file\"; filename=\"%s\"\r\nContent-Type: %s\r\n\r\n"
            % (boundary, os.path.basename(path), kind)).encode()
    body = head + open(path, "rb").read() + ("\r\n--%s--\r\n" % boundary).encode()
    answer = call("POST", API + "/model/uploadMedia", body,
                  {"Content-Type": "multipart/form-data; boundary=" + boundary}, timeout=300)
    data = answer.get("data") or {}
    url = data.get("download_url") or data.get("url") or data.get("file_url")
    print(json.dumps({"uploaded": os.path.basename(path), "url": url, "answer_keys": sorted(data) if not url else None}))
    return 0 if url else 1


def main(argv):
    if len(argv) >= 1 and argv[0] == "balance":
        print(json.dumps({"balance": balance()}))
        return 0
    if len(argv) >= 6 and argv[0] == "image":
        out, prompt, size, quality, images = argv[1], open(argv[2], encoding="utf-8").read().strip(), argv[3], argv[4], argv[5:]
        return submit("/model/generateImage", {
            "model": IMAGE_MODEL, "prompt": prompt, "images": images, "size": size, "quality": quality,
            "n": 1, "output_format": "png"}, out)
    if len(argv) >= 6 and argv[0] == "video":
        out, prompt, resolution, seconds, first = argv[1], open(argv[2], encoding="utf-8").read().strip(), argv[3], int(argv[4]), argv[5]
        body = {"model": VIDEO_MODEL, "prompt": prompt, "image": first, "duration": seconds, "resolution": resolution}
        if len(argv) > 6:
            body["last_image"] = argv[6]
        return submit("/model/generateVideo", body, out)
    if len(argv) == 2 and argv[0] == "upload":
        return upload(argv[1])
    if len(argv) == 3 and argv[0] == "get":
        return wait(argv[1], argv[2], time.time(), balance())
    sys.exit(__doc__)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

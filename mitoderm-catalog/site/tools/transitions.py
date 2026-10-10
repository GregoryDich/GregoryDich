#!/usr/bin/env python3
"""Make a scroll transition for the Story Scroll pages: Kling start/end-frame clip via Atlas Cloud,
then a WebP frame sequence the prototype draws on canvas (site/proto/exocell-template.html).

Usage:
  ATLASCLOUD_API_KEY=... python3 transitions.py start.jpg end.jpg "camera prompt" out/01-open [--seconds 5] [--frames 72]
Needs: network access to api.atlascloud.ai, ffmpeg on PATH. Nothing is submitted without --go (dry run prints the request and the price).
Price (Atlas page, 10/10/2026): kwaivgi/kling-v2.1-i2v-pro/start-end-frame ≈ $0.083/s → 5 s ≈ $0.42; kling v3 turbo i2v ≈ $0.095/s.
"""
import argparse, base64, json, os, subprocess, sys, time, urllib.request

API = 'https://api.atlascloud.ai/api/v1/model'
MODEL = 'kwaivgi/kling-v2.1-i2v-pro/start-end-frame'
PRICE_PER_SEC = 0.083

def req(path, payload=None, key=None):
    data = json.dumps(payload).encode() if payload is not None else None
    r = urllib.request.Request(API + path, data=data, method='POST' if data else 'GET')
    r.add_header('Authorization', 'Bearer ' + key); r.add_header('Content-Type', 'application/json')
    with urllib.request.urlopen(r, timeout=60) as resp: return json.load(resp)

def data_url(path):
    mime = 'image/png' if path.lower().endswith('.png') else 'image/jpeg'
    return f'data:{mime};base64,' + base64.b64encode(open(path, 'rb').read()).decode()

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('start'); ap.add_argument('end'); ap.add_argument('prompt'); ap.add_argument('out')
    ap.add_argument('--seconds', type=int, default=5, choices=[5, 10]); ap.add_argument('--frames', type=int, default=72); ap.add_argument('--go', action='store_true')
    a = ap.parse_args()
    key = os.environ.get('ATLASCLOUD_API_KEY')
    payload = {'model': MODEL, 'prompt': a.prompt, 'negative_prompt': 'text, logo, watermark, cut, extra objects', 'image': data_url(a.start), 'end_image': data_url(a.end), 'guidance_scale': 0.5, 'duration': a.seconds}
    print(f'{MODEL} {a.seconds}s ≈ ${PRICE_PER_SEC * a.seconds:.2f}; frames {a.frames} → {a.out}/0001.webp…')
    if not a.go: print('dry run (add --go to submit)'); return
    if not key: sys.exit('ATLASCLOUD_API_KEY is not set')
    job = req('/generateVideo', payload, key); pid = job['data']['id']; print('prediction', pid)
    while True:
        time.sleep(8); st = req('/prediction/' + pid, key=key); s = st['data'].get('status'); print(' ', s)
        if s in ('completed', 'succeeded'): break
        if s == 'failed': sys.exit(json.dumps(st)[:500])
    outs = st['data'].get('outputs') or st['data'].get('output') or []
    url = outs[0] if isinstance(outs, list) else outs
    os.makedirs(a.out, exist_ok=True); mp4 = os.path.join(a.out, 'clip.mp4')
    urllib.request.urlretrieve(url, mp4); print('clip', mp4)
    # frame sequence for the canvas scrubber: N evenly spaced frames, 1600 px wide, WebP q80
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', mp4, '-vf', f'fps={a.frames}/{a.seconds},scale=1600:-2', '-c:v', 'libwebp', '-q:v', '80', os.path.join(a.out, '%04d.webp')], check=True)
    n = len([f for f in os.listdir(a.out) if f.endswith('.webp')]); print('frames', n)

if __name__ == '__main__': main()

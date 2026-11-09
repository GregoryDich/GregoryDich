"""Build the V5 continuous film in the Higgsfield sandbox.

Extends assemble-vtech-continuity.py's verified bidirectional DIS method.
Run with --config pointing to confirmed source/result URLs. No signed upload
URLs belong in this recipe or the manifest. The invoking sandbox command must
upload the completed files to preallocated media_upload destinations.
"""
import argparse
import json
import subprocess
import urllib.request
from pathlib import Path

import cv2
import numpy as np

cv2.setNumThreads(2)
parser = argparse.ArgumentParser()
parser.add_argument('--config', required=True)
parser.add_argument('--root', default='/home/user/vtech-v5-render')
parser.add_argument('--variant', choices=['desktop', 'mobile', 'both'], default='both')
parser.add_argument('--reuse-normalized', action='store_true',
                    help='Reuse unchanged normalized clips after a bounded transition correction')
args = parser.parse_args()
root = Path(args.root)
root.mkdir(parents=True, exist_ok=True)
config_document = json.loads(Path(args.config).read_text())
config = config_document.get('assembly_config', config_document)


def run(argv):
    subprocess.run(argv, check=True, stdout=subprocess.DEVNULL)


def encode(out, crf):
    return ['-an', '-c:v', 'libx264', '-preset', 'fast', '-crf', str(crf),
            '-threads', '2', '-g', '6', '-keyint_min', '6', '-sc_threshold', '0',
            '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(out)]


def probe(path):
    return json.loads(subprocess.check_output([
        'ffprobe', '-v', 'error', '-show_entries',
        'stream=index,codec_type,codec_name,width,height,r_frame_rate,nb_frames,duration:format=duration,size',
        '-of', 'json', str(path)]))


def video_stream(path):
    return next(s for s in probe(path)['streams'] if s['codec_type'] == 'video')


def frame(path, last=False):
    cap = cv2.VideoCapture(str(path))
    if last:
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) - 1)
    ok, image = cap.read()
    cap.release()
    if not ok:
        raise RuntimeError(f'Missing {"last" if last else "first"} frame: {path}')
    return image


def source(variant, name):
    staged = config.get('local_sources', {}).get(variant, {}).get(name)
    if staged and Path(staged).is_file() and Path(staged).stat().st_size:
        return Path(staged)
    target = root / 'sources' / f'{name}-{variant}.mp4'
    target.parent.mkdir(exist_ok=True)
    if not target.exists() or target.stat().st_size == 0:
        urllib.request.urlretrieve(config['variants'][variant][name], target)
    return target


def registered_portrait_bridge(source_path, output, w, h, crf, registration):
    """Reframe the clean landscape transition using endpoint face registration.

    Sample every second source frame for the two-second transition. Warp the
    full landscape source, not an already cropped portrait, so horizontal
    repositioning reveals real image content instead of stretched borders.
    """
    cap = cv2.VideoCapture(str(source_path))
    count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    first = np.asarray(registration['start'], dtype=np.float32)
    last = np.asarray(registration['end'], dtype=np.float32)
    process = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo',
        '-pixel_format', 'bgr24', '-video_size', f'{w}x{h}', '-framerate', '24',
        '-i', 'pipe:0', *encode(output, crf)], stdin=subprocess.PIPE)
    for index in range(count):
        ok, current = cap.read()
        if not ok:
            raise RuntimeError('Incomplete clean landscape transition')
        if index % 2:
            continue
        full_width = round(current.shape[1] * h / current.shape[0])
        full = cv2.resize(current, (full_width, h), interpolation=cv2.INTER_CUBIC)
        t = index / max(count-1, 1)
        ease = t*t*(3-2*t)
        matrix = first*(1-ease) + last*ease
        matrix = matrix.copy()
        matrix[:, 2] -= matrix[:, 0] * ((full_width-w)/2)
        portrait = cv2.warpAffine(full, matrix, (w, h), flags=cv2.INTER_CUBIC,
                                  borderMode=cv2.BORDER_REPLICATE)
        process.stdin.write(portrait.tobytes())
    cap.release()
    process.stdin.close()
    if process.wait() != 0:
        raise RuntimeError('Registered portrait transition encoding failed')


def join(previous, following, directory, name, w, h, crf):
    a, b = frame(previous, True), frame(following)
    raw_delta = float(cv2.absdiff(a, b).mean())
    if raw_delta < .6:
        return None, {'name': name, 'frames': 0, 'raw_mae': raw_delta,
                      'reason': 'Adjacent frames already practically identical'}
    directory.mkdir(exist_ok=True)
    small = (w // 2, h // 2)
    ga = cv2.cvtColor(cv2.resize(a, small), cv2.COLOR_BGR2GRAY)
    gb = cv2.cvtColor(cv2.resize(b, small), cv2.COLOR_BGR2GRAY)
    dis = cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_MEDIUM)
    ab = cv2.resize(dis.calc(ga, gb, None), (w, h)) * 2
    ba = cv2.resize(dis.calc(gb, ga, None), (w, h)) * 2
    x, y = np.meshgrid(np.arange(w, dtype=np.float32), np.arange(h, dtype=np.float32))
    samples, last = [], a
    for k in range(1, 7):
        t = k / 7
        wa = cv2.remap(a, x - t * ab[:, :, 0], y - t * ab[:, :, 1],
                       cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
        wb = cv2.remap(b, x - (1-t) * ba[:, :, 0], y - (1-t) * ba[:, :, 1],
                       cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
        current = cv2.addWeighted(wa, 1-t, wb, t, 0)
        cv2.imwrite(str(directory / f'{k:02d}.png'), current)
        samples.append({'t': round(t, 4),
                        'mae_from_A': round(float(cv2.absdiff(current, a).mean()), 3),
                        'mae_from_B': round(float(cv2.absdiff(current, b).mean()), 3),
                        'step_mae': round(float(cv2.absdiff(current, last).mean()), 3)})
        last = current
        if k == 3:
            pw = 640 if w > h else 320
            cv2.imwrite(str(directory / 'midpoint.jpg'),
                        cv2.resize(current, (pw, round(pw*h/w))),
                        [cv2.IMWRITE_JPEG_QUALITY, 86])
    if samples[0]['mae_from_A'] >= samples[-1]['mae_from_A'] or samples[0]['mae_from_B'] <= samples[-1]['mae_from_B']:
        raise RuntimeError(f'Join {name} does not progress from A to B')
    if max(s['step_mae'] for s in samples) < .02:
        raise RuntimeError(f'Join {name} is not moving')
    output = directory / 'join.mp4'
    run(['ffmpeg', '-v', 'error', '-y', '-framerate', '24', '-start_number', '1',
         '-i', str(directory / '%02d.png'), '-frames:v', '6', *encode(output, crf)])
    return output, {'name': name, 'frames': 6, 'raw_mae': round(raw_delta, 3),
                    'samples': samples, 'midpoint': str(directory / 'midpoint.jpg')}


all_metadata = []
for variant, w, h, crf in [('desktop', 1912, 1080, 21), ('mobile', 812, 1440, 22)]:
    if args.variant != 'both' and variant != args.variant:
        continue
    directory = root / variant
    directory.mkdir(exist_ok=True)
    specification = [('camera', 'camera', 1, .5, False),
                     ('pen', 'pen', 1, .6, False),
                     ('to_serum', 'pen_to_serum', .5, .5, False),
                     ('serum', 'serum', 1, .4, False),
                     ('to_mask', 'serum_to_mask', .5, .5, False),
                     ('mask', 'mask', 1, .67, False),
                     ('to_wide', 'mask_to_wide', 1, .5, False),
                     ('pack_zoom', 'intro', 1, .5, True)]
    normalized = []
    for name, source_name, speed, focal, reverse in specification:
        output = directory / f'{name}.mp4'
        registration = config.get('portrait_p2s_alignment')
        if variant == 'mobile' and name == 'to_serum' and registration:
            registered_portrait_bridge(source(variant, source_name), output,
                                       w, h, crf, registration)
            normalized.append((name, output))
            continue
        if args.reuse_normalized and output.is_file() and output.stat().st_size:
            normalized.append((name, output))
            continue
        filter_chain = f'scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}:(iw-{w})*{focal if variant == "mobile" else .5}:(ih-{h})/2,setsar=1'
        if reverse:
            filter_chain += ',reverse'
        filter_chain += f',setpts={speed}*(PTS-STARTPTS),fps=24'
        run(['ffmpeg', '-v', 'error', '-y', '-i', str(source(variant, source_name)),
             '-vf', filter_chain, *encode(output, crf)])
        normalized.append((name, output))
    sequence, segments, joins, cursor = [], [], [], 0
    for index, (name, path) in enumerate(normalized):
        if index:
            previous_name, previous_path = normalized[index-1]
            join_name = f'{previous_name}-to-{name}'
            joined, meta = join(previous_path, path, directory / join_name,
                                join_name, w, h, crf)
            meta.update({'start_frame': cursor, 'start_seconds': cursor / 24})
            if joined:
                sequence.append(joined)
                cursor += meta['frames']
            meta['end_seconds'] = cursor / 24
            joins.append(meta)
        count = int(video_stream(path)['nb_frames'])
        segments.append({'name': name, 'frames': count, 'start_frame': cursor,
                         'end_frame': cursor + count,
                         'start_seconds': cursor / 24, 'end_seconds': (cursor + count) / 24})
        sequence.append(path)
        cursor += count
    listing = directory / 'concat.txt'
    listing.write_text(''.join(f"file '{p.absolute()}'\n" for p in sequence))
    output = root / f'full-story-{variant}.mp4'
    run(['ffmpeg', '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', str(listing),
         '-c', 'copy', '-movflags', '+faststart', str(output)])
    final_probe = probe(output)
    final_stream = next(s for s in final_probe['streams'] if s['codec_type'] == 'video')
    if int(final_stream['nb_frames']) != cursor:
        raise RuntimeError('Concatenation changed the number of frames')
    if any(s['codec_type'] == 'audio' for s in final_probe['streams']):
        raise RuntimeError('Unexpected audio')
    terminal = root / f'full-story-{variant}-terminal.webp'
    run(['ffmpeg', '-v', 'error', '-y', '-i', str(output),
         '-vf', f'select=eq(n\\,{cursor-1})', '-frames:v', '1', '-quality', '94', str(terminal)])
    # An independent pixel-shape check: final image must have the same framing
    # as the original intro first frame, since the final clip is that intro reversed.
    original_first = frame(directory / 'pack_zoom.mp4', True)
    terminal_mae = float(cv2.absdiff(original_first, frame(output, True)).mean())
    if terminal_mae > 2:
        raise RuntimeError('Terminal geometry changed during concatenation')
    frames = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-select_streams', 'v:0',
        '-show_entries', 'frame=key_frame', '-of', 'json', str(output)]))['frames']
    keyframes = [i for i, f in enumerate(frames) if f['key_frame']]
    max_keyframe_gap = max((b-a for a,b in zip(keyframes, keyframes[1:])), default=0)
    if max_keyframe_gap > 6:
        raise RuntimeError('Seek keyframe gap exceeds six frames')
    with output.open('rb') as stream:
        atoms = []
        while True:
            header = stream.read(8)
            if len(header) != 8:
                break
            size, kind = int.from_bytes(header[:4], 'big'), header[4:].decode('latin1')
            atoms.append(kind)
            if size < 8:
                break
            stream.seek(size-8, 1)
    faststart = 'moov' in atoms and 'mdat' in atoms and atoms.index('moov') < atoms.index('mdat')
    if not faststart:
        raise RuntimeError('Missing faststart')
    all_metadata.append({'variant': variant, 'output': str(output), 'terminal_poster': str(terminal),
        'width': w, 'height': h, 'fps': 24, 'frames': cursor, 'duration_seconds': cursor / 24,
        'size_bytes': output.stat().st_size, 'segments': segments, 'joins': joins,
        'pack_zoom_start_seconds': next(s['start_seconds'] for s in segments if s['name'] == 'pack_zoom'),
        'pack_locked_at_seconds': (cursor-1) / 24, 'terminal_mae_after_concat': terminal_mae,
        'max_keyframe_gap': max_keyframe_gap, 'faststart': faststart, 'audio_streams': 0})
metadata_path = root / 'metadata.json'
if args.variant != 'both' and metadata_path.exists():
    old_metadata = json.loads(metadata_path.read_text())
    all_metadata = [m for m in old_metadata if m['variant'] != args.variant] + all_metadata
    all_metadata.sort(key=lambda m: m['variant'])
metadata_path.write_text(json.dumps(all_metadata, indent=2))
print(json.dumps(all_metadata))

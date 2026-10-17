# scene.js = video scene (template + generated geometry + placements) + the old photo scene as AQUARIUM_SCENE_PHOTO
import json, sys, re, importlib.util
import os
W2 = os.getcwd() + '/'                 # рабочая папка (frames/ out/ final/ tpl/); шаблон и раскладка — из tpl/ этой папки
spec = importlib.util.spec_from_file_location('pl', W2 + 'tpl/placements.py'); pl = importlib.util.module_from_spec(spec); spec.loader.exec_module(pl)
g = json.load(open(W2 + 'out/geom.json')); meta = json.load(open(W2 + 'final/masks_meta.json'))
tpl = open(W2 + 'tpl/scene_video_tpl.js').read()
grid = g['grid']; R = len(grid); C = len(grid[0])
def js(v):
    if v is None: return 'null'
    if isinstance(v, bool): return 'true' if v else 'false'
    if isinstance(v, (int,)): return str(v)
    if isinstance(v, float): return (f'{v:.4f}'.rstrip('0').rstrip('.') if abs(v) < 100 else str(round(v, 2))) if v != int(v) or abs(v) < 1 else f'{v:.1f}' if False else (str(int(v)) if v == int(v) else str(v))
    if isinstance(v, str): return json.dumps(v, ensure_ascii=False)
    if isinstance(v, list): return '[' + ', '.join(js(x) for x in v) + ']'
    if isinstance(v, dict): return '{ ' + ', '.join(f'{k}: {js(x)}' for k, x in v.items()) + ' }'
    raise TypeError(v)
rows = []
for r in range(R):
    by0, by1 = r / R, (r + 1) / R
    rows.append('      ' + ','.join(f'{x:.2f}' for x in grid[r]) + (',' if r < R - 1 else ' ') + f' // r{r}  by {by0:.3f}–{by1:.3f}')
floor = '    ' + ', '.join(f'[{a:.3f}, {b:.3f}]' for a, b in pl.FLOOR) + ','
occ_info = [('pillar_left', 'left', 1.85, 2.40, 'левая колонна целиком (с огненным кораллом-кружевом на кромке у каньона)'),
            ('pillar_right', 'right', 1.83, 2.40, 'правая колонна целиком (валуны вверху, «шпора» над каньоном, нижние кораллы)'),
            ('far_reef', 'far', 2.30, 2.60, 'дальний риф в каньоне: рыба, ушедшая вглубь каньона (z > 2.3), скрывается за ним; основание — по границе тёмного рифа и светлого щебня')]
occ = []
for oid, k, z, zb, note in occ_info:
    m = meta[k]
    occ.append(f'    // {note}')
    occ.append(f'    {{ id: "{oid}", kind: "mask", mask: "scene/mask_{k}.png", bx: {m["bx"]:.9f}, by: {m["by"]:.9f}, bw: {m["bw"]:.9f}, bh: {m["bh"]:.9f}, px: {js(m["px"])}, z: {z:.2f}, zBack: {zb:.2f},')
    occ.append(f'      profile: {{ step: {m["profile"]["step"]}, topHi: {js(m["profile"]["topHi"])},')
    occ.append(f'                 topLo: {js(m["profile"]["topLo"])} }},')
    occ.append(f'      grid: {js(m["grid"])} }},')
def items(lst, keyorder=None):
    out = []
    for d in lst:
        d = dict(d); note = d.pop('note', None)
        if note: out.append(f'    // {note}')
        out.append('    ' + js(d) + ',')
    return '\n'.join(out)
grids = json.load(open(W2 + 'tpl/prop_grids.json'))
for pr in pl.PROPS:
    gi = grids.get(pr['id'])
    if gi and 'grid' not in pr:
        # same PNG as in the photo scene: its 16x16 alpha occupancy grid (engine hit tests), inserted after src
        items_ = list(pr.items()); k = [i for i, (kk, _) in enumerate(items_) if kk == 'src'][0]
        items_.insert(k + 1, ('grid', gi['grid'])); pr.clear(); pr.update(items_)
        if gi.get('frontGrid') and pr.get('layers'): pr['layers']['frontGrid'] = gi['frontGrid']
s = tpl.replace('@COLS@', str(C)).replace('@ROWS@', str(R)).replace('@NCELLS@', str(R * C))
s = s.replace('@DEPTHGRID@', '\n'.join(rows)).replace('@FLOOR@', floor).replace('@OCCLUDERS@', '\n'.join(occ))
s = s.replace('@CORALS@', items(pl.CORALS)).replace('@PROPS@', items(pl.PROPS)).replace('@SPOTS@', items(pl.SPOTS))
s = s.replace('@LANES@', items(pl.LANES)).replace('@BUBBLES@', items(pl.BUBBLES))
# old photo scene -> fallback entry
ph = open(W2 + 'tpl/scene_photo_orig.js').read()
head_end = ph.index('window.AQUARIUM_SCENE = {')
body = ph[head_end:].replace('window.AQUARIUM_SCENE = {', 'window.AQUARIUM_SCENE_PHOTO = {', 1)
body = body.replace('  surface: { bandH: 0.075, mirrorRows: 0.14 },', '  // V2: поверхности воды нет нигде (владелец) — полоса выключена и у запасной фото-сцены\n  surface: { bandH: 0, mirrorRows: 0 },', 1)
assert 'bandH: 0, mirrorRows: 0 }' in body
s = s + '/* ============================================================\n   ЗАПАСНАЯ СЦЕНА — фото рифового аквариума assets/reef_bg.jpg (бывшая основная, этапы A0–A2, A1, E4).\n   Движок берёт её, только если видео и постеры не загрузились и задник — это фото. Без изменений,\n   кроме выключенной полосы поверхности. Описание полей — SPEC §3 и комментарии ниже.\n   ============================================================ */\n' + body
open(sys.argv[1], 'w').write(s)
print('written', sys.argv[1], len(s))

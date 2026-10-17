# consistency: open-water spots/lanes/bubbles/props in front of the reef surface; hidden spots inside the mask
import json, sys
sys.path.insert(0, 'scripts')
from probe import depthAtB, alpha
sc = json.load(open(sys.argv[1])); occ = {o['id']: o for o in sc['occluders']}
key = {'pillar_left': 'left', 'pillar_right': 'right', 'far_reef': 'far'}
bad = 0
for s in sc['spots']:
    g = depthAtB(s['bx'], s['by'])
    if s['behind']:
        o = occ[s['behind']]; a = alpha(s['bx'], s['by'])[key[s['behind']]]
        ok = o['z'] < s['z'] < o['zBack'] and a > 0.9
        msg = f"hidden z {s['z']} in ({o['z']},{o['zBack']}) mask {a}"
    else:
        ok = s['z'] < g - 0.05 or s['type'] == 'home'
        msg = f"z {s['z']} grid {g:.2f}"
    if not ok: bad += 1
    print('OK ' if ok else 'BAD', 'spot', s['id'], msg)
for l in sc['lanes']:
    for p in l['pts']:
        g = depthAtB(p[0], p[1]); ok = p[2] < g - 0.05
        if not ok: bad += 1
        print('OK ' if ok else 'BAD', 'lane', l['id'], p, f'grid {g:.2f}')
for b in sc['bubbles']:
    g = depthAtB(b['bx'], b['by']); ok = b['z'] < g + 0.01
    if not ok: bad += 1
    print('OK ' if ok else 'BAD', 'bubble', b['id'], b['z'], f'grid {g:.2f}')
print('violations', bad)

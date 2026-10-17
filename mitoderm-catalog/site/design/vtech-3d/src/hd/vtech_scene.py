"""V-TECH SYSTEM path-traced in Blender Cycles: the scroll story of the live page (owner 17/10) and its key frames.
Everything is built in three.js coordinates (Y up) under a root empty turned 90° about X; Blender Euler 'ZYX' equals
three.js 'XYZ'. Print maps: prep_tex.py (carton, sachet) and prep_label.py (the clear ampoule label).
usage: <python with bpy 4.2> vtech_scene.py <tex dir> <out.png|.webp> <shot> [width=2880] [samples=256] [part]
   or: Blender -b --factory-startup -P vtech_scene.py -- <same arguments>   (VT_DEVICE=METAL: the GPU, see render_mac.sh)
shots: v1-meet v2-why v3-inside v4-feel v5-protocol v6-kit; a transition frame is 'A>B@t' (t 0..1), e.g.
'v2-why>v3-inside@0.4' (render_seq.py renders the whole run).
part (box|vials|pouches) renders that layer alone, every other object a holdout, for the Figma layers.
The page's copy sits in the right half, so the 3D lives in the left: the world is mirrored (VT_MIRROR=0 renders the
original) and the print flipped back, so every frame mirrors the approved light and foil while the print still reads.
Shots are authored in fractions of the final frame (scr()).
The frame is rendered on a transparent film; the page lays it over the line's smoke and its exosome-cell layer."""
import bpy, bmesh, math, os, sys
from mathutils import Euler, Matrix, Vector

ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:]   # bpy module, or the Blender app: blender -b -P vtech_scene.py -- …
TEX, OUT, SHOT = ARGS[0:3]
WIDTH = int(ARGS[3]) if len(ARGS) > 3 else 2880
SAMPLES = int(ARGS[4]) if len(ARGS) > 4 else 256
PART = ARGS[5] if len(ARGS) > 5 else None
MIRROR = os.environ.get('VT_MIRROR', '1') != '0'   # owner 17/10: copy on the right, the 3D on the left

DESK = dict(aspect=1.6, cam=(0, 0, 7), look=(0.9, 0, 0), exposure=-0.8)
TH = math.tan(math.radians(35) / 2)   # half the vertical field of view
BOX_H, VIAL_H, SACHET_W = 2.31, 0.756, 1.0   # carton height, ampoule height with its cap, sachet width (scale 1)


def scr(sx, sy, d, cam=DESK):
    """The point at fractions (sx from the left, sy from the top) of the FINAL frame, d units in front of the camera
    along its axis; the mirror is undone here, so a shot reads as it will be seen."""
    if MIRROR: sx = 1 - sx
    C = Vector(cam['cam']); F = (Vector(cam['look']) - C).normalized(); X = F.cross(Vector((0, 1, 0))).normalized(); U = X.cross(F)
    return tuple(C + d * (F + X * (sx - 0.5) * 2 * TH * cam['aspect'] + U * (0.5 - sy) * 2 * TH))


def fit(h, d, size): return h * 2 * TH * d / size   # scale making an object of height `size` fill `h` of the frame height at depth d
def facing(p, wall=(-2.8, 0.0, 5.6), cam=DESK):
    """The turn (about y) that makes a carton front at p mirror the camera into the banded light wall, as the approved
    S1 does (its front mirrors the wall at x -2.8): a front turned anywhere else mirrors the dark room and reads as
    matte card."""
    n = (Vector(cam['cam']) - Vector(p)).normalized() + (Vector(wall) - Vector(p)).normalized()
    return math.atan2(n.x, n.z)


def box(sx, sy, d, h, turn=0.0, tilt=0.05, dim=1.0):   # turn: extra turn from the mirror-the-wall pose (radians)
    p = scr(sx, sy, d); return dict(p=p, r=(tilt, facing(p) + turn, 0.0), s=fit(h, d, BOX_H), dim=dim)
def vial(sx, sy, d, h, r=(0.06, -0.18, 0.0)):   # sx, sy: the centre of the ampoule (its origin is at the base)
    k = fit(h, d, VIAL_H); x, y, z = scr(sx, sy, d); return [x, y - VIAL_H / 2 * k, z, *r, k]
def sachet(sx, sy, d, w, r=(0.14, -0.28, 0.05)): return [*scr(sx, sy, d), *r, fit(w * DESK['aspect'], d, SACHET_W)]   # w: of the frame width


# The story (owner 17/10): one carton, nearly locked camera; it recedes, comes close, recedes, and the contents slide
# out from behind it one by one — the ampoule (S3), the gel-mask sachet (S4), the pair (S5), then the rest of the kit
# (S6, the picture of the single «מה באריזה» card). Nothing stands on anything; the exosome cells live on the page.
# the kit as a triangle: the carton at the back with its print clear, the ampoules in an arc low on its right, the sachet
# fan low on its left (the fan over the carton hid «V-TECH SYSTEM», and its first spout left the frame)
KIT_VIALS = [vial(0.335 + 0.034 * i, 0.66 - 0.035 * math.sin(math.pi * i / 4), 6.2 - 0.08 * i, 0.17, (0.05, -0.12 - 0.05 * i, 0.03 - 0.015 * i)) for i in range(5)]
KIT_SACHETS = [sachet(0.13 + 0.026 * i, 0.78 - 0.04 * i, 6.0 + 0.15 * i, 0.14, (0.24 - 0.02 * i, -0.46 + 0.05 * i, 0.2 - 0.07 * i)) for i in range(5)]
SHOTS = {
    'v1-meet': dict(DESK, box=dict(p=(1.8, -0.05, 0.2), r=(0.06, -0.48, 0.0), s=1)),   # approved (16/10); mirrored as a whole
    # S2: the carton far and small, still gold, turned further (on the way a highlight crosses the foil)
    'v2-why': dict(DESK, box=box(0.26, 0.42, 9.0, 0.30, turn=-0.08, dim=0.85)),
    # S3: the ampoule is the hero, in focus; the carton back, soft
    'v3-inside': dict(DESK, box=box(0.13, 0.32, 9.5, 0.40, turn=0.06, dim=0.7), vials=[vial(0.33, 0.56, 4.6, 0.46)],
                      focus=scr(0.33, 0.56, 4.6), fstop=1.4),
    # S4: the gel-mask sachet is the hero; the ampoule small aside, the carton far
    'v4-feel': dict(DESK, box=box(0.21, 0.27, 11.0, 0.30, dim=0.6), vials=[vial(0.11, 0.40, 6.5, 0.22)],
                    pouches=[sachet(0.30, 0.57, 4.4, 0.36)], focus=scr(0.30, 0.57, 4.4), fstop=1.4),
    # S5: the pair, read right to left as the steps: the ampoule (01) next to the copy, the sachet (02) outside
    'v5-protocol': dict(DESK, box=box(0.27, 0.30, 10.0, 0.36, dim=0.55), vials=[vial(0.39, 0.50, 5.5, 0.30)],
                        pouches=[sachet(0.19, 0.55, 5.5, 0.22)], focus=scr(0.27, 0.52, 5.5), fstop=2.5),
    # S6: the kit, closed carton at the back, 5 ampoules in an arc and 5 sachets in a fan, all in the air
    'v6-kit': dict(DESK, box=box(0.24, 0.36, 7.5, 0.50), vials=KIT_VIALS, pouches=KIT_SACHETS),
}
# per run: the carton's closest point on the way (via), and how each new item comes out: (side, start, clear, end) —
# side ±1 along the carton's own x (+1 is the outer edge, away from the copy), the run fractions where it starts behind
# the carton, is clear of its edge, and arrives
TRANS = {
    ('v2-why', 'v3-inside'): dict(via=dict(box(0.30, 0.50, 5.2, 0.62), t=0.5), vials=[(1, 0.5, 0.68, 0.97)]),
    ('v3-inside', 'v4-feel'): dict(pouches=[(-1, 0.08, 0.32, 0.96)]),   # a long arrival: the big sachet swings in slowly
    ('v5-protocol', 'v6-kit'): dict(vials=[(-1, 0.18 + 0.13 * j, 0.30 + 0.13 * j, 0.52 + 0.13 * j) for j in range(4)],
                                    pouches=[(1, 0.25 + 0.13 * j, 0.37 + 0.13 * j, 0.59 + 0.13 * j) for j in range(4)]),
}


def ease(t): return t * t * (3 - 2 * t)
def lerp(a, b, t): return tuple(x + (y - x) * t for x, y in zip(a, b))
def clamp01(v): return min(1.0, max(0.0, v))
def win(t, w): return ease(clamp01((t - w[0]) / (w[1] - w[0])))   # 0 → 1 over the window w of the run


def pose(a, b, e):  # the carton in both screens: position, turn, size and dimming along the ease
    return dict(b, p=lerp(a['p'], b['p'], e), r=lerp(a['r'], b['r'], e), s=a['s'] + (b['s'] - a['s']) * e,
                dim=a.get('dim', 1) + (b.get('dim', 1) - a.get('dim', 1)) * e)


def emerge(bx, final, side, t, w, half, flat=False):
    """An item only screen B has: hidden behind the carton bx (and smaller), it slides sideways out from behind its edge
    (side ±1 along the carton's x), then comes forward to its place, turning to it and growing to its size; a sachet
    travels edge-on until it is clear. w = (start, clear, end) of the run; half = the item's half width at full size."""
    M = Euler(bx['r'], 'ZYX').to_matrix(); s = bx['s']; B = Vector(bx['p']); z = -(0.2 * s + 0.3)   # behind the back face
    P0 = B + M @ Vector((0, -0.2 * s, z)); P1 = B + M @ Vector((side * (0.475 * s + 0.6 * half + 0.08), -0.2 * s, z))
    k1, k2 = win(t, w[:2]), win(t, w[1:])
    p = P0 + (P1 - P0) * k1 + (Vector(final[:3]) - P1) * k2
    r0 = Vector(bx['r']) + Vector((0, side * math.pi / 2 if flat else 0, 0)); r = r0 + (Vector(final[3:6]) - r0) * k2
    return [*p, *r, final[6] * (0.6 + 0.4 * k2)]


def blend(ka, kb, t):
    """The pose between screens ka and kb at t (0..1), for the scroll sequences: camera, exposure and focus along a
    smoothstep, the carton along its path (through its closest point if the run has one), items in both screens move
    to their new places, new items come out from behind the carton (emerge). t = 0 and 1 are the key frames."""
    A, B, T = SHOTS[ka], SHOTS[kb], TRANS.get((ka, kb), {})
    if t <= 0 or t >= 1: return dict(B if t >= 1 else A)
    e = ease(t); S = {k: v for k, v in B.items() if k not in ('box', 'vials', 'pouches', 'focus', 'fstop')}
    S['cam'], S['look'] = lerp(A['cam'], B['cam'], e), lerp(A['look'], B['look'], e)
    S['exposure'] = A.get('exposure', 0) + (B.get('exposure', 0) - A.get('exposure', 0)) * e
    if A.get('fstop') or B.get('fstop'):   # focus pull: aperture (1/f-stop) and focus point along the same ease
        ap = (1 / A['fstop'] if A.get('fstop') else 0) * (1 - e) + (1 / B['fstop'] if B.get('fstop') else 0) * e
        fa, fb = A.get('focus', A['box']['p']), B.get('focus', B['box']['p'])
        S['fstop'], S['focus'] = (1 / ap if ap > 0.02 else None), lerp(fa, fb, e)
    V = T.get('via')
    if V: S['box'] = pose(A['box'], V, ease(t / V['t'])) if t < V['t'] else pose(V, B['box'], ease((t - V['t']) / (1 - V['t'])))
    else: S['box'] = pose(A['box'], B['box'], e)
    for kind, half in (('vials', 0.17), ('pouches', 0.3)):
        a, b = A.get(kind, []), B.get(kind, [])
        out = [list(lerp(x, y, e)) for x, y in zip(a, b)]
        for j, y in enumerate(b[len(a):]):
            side, *w = T.get(kind, [])[j] if j < len(T.get(kind, [])) else (1, 0.3, 0.5, 0.9)
            out.append(emerge(S['box'], y, side, t, w, half * y[6], kind == 'pouches'))
        if out: S[kind] = out
    sa, sb = (float(len(X['pouches']) == 1) if X.get('pouches') else None for X in (A, B))
    if sa is not None or sb is not None: S['solo'] = sb if sa is None else sa if sb is None else sa + (sb - sa) * e
    return S


if '>' in SHOT:   # 'v2-why>v3-inside@0.35': a frame of the transition
    a, rest = SHOT.split('>'); b, t = rest.split('@'); S = blend(a, b, float(t))
else:
    S = SHOTS[SHOT]

bpy.ops.wm.read_factory_settings(use_empty=True)
scn = bpy.context.scene
root = bpy.data.objects.new('root', None); scn.collection.objects.link(root); root.rotation_euler = (math.pi / 2, 0, 0)
if MIRROR: root.scale = (-1, 1, 1)   # three.js x and Blender x are the same axis; the camera is placed apart (below)


def obj(name, data=None, mats=(), parent=root, p=(0, 0, 0), r=(0, 0, 0), s=1):
    ob = bpy.data.objects.new(name, data); scn.collection.objects.link(ob)
    for m in mats: ob.data.materials.append(m)
    ob.parent = parent; ob.location = p; ob.rotation_mode = 'ZYX'; ob.rotation_euler = r; ob.scale = (s, s, s)
    return ob


def tag(ob, part):  # the Figma layer an object belongs to (box, vials, pouches)
    for o in [ob] + list(ob.children_recursive): o['part'] = part
    return ob


def to_mesh(bm, name, smooth=True, sharp=35):
    if sharp:  # crisp folds and rims, smooth curved glass
        for e in bm.edges:
            if len(e.link_faces) == 2 and e.calc_face_angle(0) > math.radians(sharp): e.smooth = False
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    me.polygons.foreach_set('use_smooth', [smooth] * len(me.polygons))
    return me


def bevel(ob, w, seg=2):
    m = ob.modifiers.new('bevel', 'BEVEL'); m.width = w; m.segments = seg; m.limit_method = 'ANGLE'; return m


def look_matrix(pos, target):  # three.js lookAt: local -Z towards the target, +Y up
    z = (Vector(pos) - Vector(target)).normalized(); x = Vector((0, 1, 0)).cross(z).normalized(); y = z.cross(x)
    return Matrix.Translation(pos) @ Matrix((x, y, z)).transposed().to_4x4()

# ---------- materials ----------
def mat(name, **kw):
    m = bpy.data.materials.new(name); m.use_nodes = True; b = m.node_tree.nodes['Principled BSDF']
    for k, v in kw.items(): b.inputs[k].default_value = v
    return m, m.node_tree, b


def image(nt, file, data=False):
    n = nt.nodes.new('ShaderNodeTexImage'); n.image = bpy.data.images.load(f'{TEX}/{file}'); n.interpolation = 'Cubic'
    n.image.colorspace_settings.name = 'Non-Color' if data else 'sRGB'
    if MIRROR:   # in the mirrored world the print would read backwards: flip it back along u
        uv, mp = nt.nodes.new('ShaderNodeUVMap'), nt.nodes.new('ShaderNodeMapping')
        mp.inputs['Scale'].default_value = (-1, 1, 1); mp.inputs['Location'].default_value = (1, 0, 0)
        nt.links.new(uv.outputs['UV'], mp.inputs['Vector']); nt.links.new(mp.outputs['Vector'], n.inputs['Vector'])
    return n


def relief(nt, b, layers):
    """Surface relief in object space: layers of (mapping scale, noise size, detail, height in scene units), bump on bump."""
    tc, prev = nt.nodes.new('ShaderNodeTexCoord'), None
    for scale, size, detail, height in layers:
        mp, nz, bp = (nt.nodes.new(t) for t in ('ShaderNodeMapping', 'ShaderNodeTexNoise', 'ShaderNodeBump'))
        mp.inputs['Scale'].default_value = scale; nz.inputs['Scale'].default_value = size; nz.inputs['Detail'].default_value = detail
        bp.inputs['Strength'].default_value = 1.0; bp.inputs['Distance'].default_value = height
        nt.links.new(tc.outputs['Object'], mp.inputs['Vector']); nt.links.new(mp.outputs['Vector'], nz.inputs['Vector'])
        nt.links.new(nz.outputs['Fac'], bp.inputs['Height'])
        if prev: nt.links.new(prev.outputs['Normal'], bp.inputs['Normal'])
        prev = bp
    nt.links.new(prev.outputs['Normal'], b.inputs['Normal'])


def printed(name, key, layers, dim=1.0):
    """Foil with the real print: metal from the mask; the ink is a rough black dielectric that stays black in any reflection.
    dim < 1 darkens the foil (a carton that is only the background of a screen)."""
    m, nt, b = mat(name)
    alb = image(nt, f'{key}-albedo.png').outputs['Color']
    if dim != 1:
        dm = nt.nodes.new('ShaderNodeMixRGB'); dm.blend_type = 'MULTIPLY'; dm.inputs['Fac'].default_value = 1
        dm.inputs['Color2'].default_value = (dim, dim, dim, 1); nt.links.new(alb, dm.inputs['Color1']); alb = dm.outputs['Color']
    nt.links.new(alb, b.inputs['Base Color'])
    metal = image(nt, f'{key}-metal.png', True); nt.links.new(metal.outputs['Color'], b.inputs['Metallic'])
    sp = nt.nodes.new('ShaderNodeMapRange'); sp.inputs['To Min'].default_value = 0.05; sp.inputs['To Max'].default_value = 0.5  # ink barely reflects
    nt.links.new(metal.outputs['Color'], sp.inputs['Value']); nt.links.new(sp.outputs['Result'], b.inputs['Specular IOR Level'])
    # satin, not a mirror (owner 17/10: the sleeve is glossy dense paper): roughness at least SATIN softens the dark gaps of
    # the reflection into gradients and keeps the highlights; 0.22 already reads as flat yellow card
    rr = nt.nodes.new('ShaderNodeMath'); rr.operation = 'MAXIMUM'; rr.inputs[1].default_value = SATIN
    nt.links.new(image(nt, f'{key}-rough.png', True).outputs['Color'], rr.inputs[0]); nt.links.new(rr.outputs[0], b.inputs['Roughness'])
    relief(nt, b, layers)
    return m


SATIN = 0.12
GOLD = (0.87, 0.57, 0.18, 1)  # linear of the packshot foil (sRGB 0.94, 0.78, 0.46)
# carton: a few broad vertical bows in the sleeve (crisp light/dark bands in the mirror) + a faint fine crinkle
FOIL = (((1.0, 0.15, 1.0), 1.3, 0.0, 0.035), ((1.0, 0.5, 1.0), 0.9, 0.0, 0.008))  # broad bows + a few soft wrinkles, nothing fine
DIM = S.get('box', {}).get('dim', 1.0)
box_front = printed('box-front', 'box-front', FOIL, DIM)
box_side = printed('box-side', 'box-side', FOIL, DIM)
box_back, nt, b = mat('box-back', **{'Base Color': tuple(c * DIM for c in GOLD[:3]) + (1,), 'Metallic': 1.0, 'Roughness': SATIN}); relief(nt, b, FOIL)
box_end = mat('box-end', **{'Base Color': (0.015, 0.015, 0.016, 1), 'Roughness': 0.3, 'Specular IOR Level': 0.5})[0]
# sachet: glossy foil with two or three soft dents and a fine crinkle, no stretched streaks
SACHET = (((1.4, 1.4, 1.4), 1.8, 0.0, 0.02), ((1, 1, 1), 26.0, 0.0, 0.0002))
sachet_front = printed('sachet-front', 'sachet', SACHET)
# the plain back shows only at the rims: a paler, satin gold, so the edges do not read orange
sachet_back, nt, b = mat('sachet-back', **{'Base Color': (0.85, 0.66, 0.36, 1), 'Metallic': 1.0, 'Roughness': 0.2}); relief(nt, b, SACHET)
nozzle = mat('nozzle', **{'Base Color': (0.9, 0.9, 0.88, 1), 'Roughness': 0.35, 'Subsurface Weight': 0.4, 'Subsurface Scale': 0.01})[0]  # milky PP
# the ampoule as on the photos: dark amber clear glass, a clear serum (the colour is the glass), a satin silver
# aluminium cap with its flip-off button, a transparent label film with white print
alu, nt, b = mat('aluminium', **{'Base Color': (0.9, 0.9, 0.91, 1), 'Metallic': 1.0, 'Roughness': 0.2})
relief(nt, b, (((1, 0.04, 1), 60.0, 2.0, 0.0006),))   # fine vertical drawing streaks of the crimped skirt
glass = mat('amber-glass', **{'Base Color': (0.31, 0.175, 0.095, 1), 'Transmission Weight': 1.0, 'Roughness': 0.02, 'IOR': 1.5})[0]   # per wall: brown, not orange
serum = mat('serum', **{'Base Color': (1, 1, 1, 1), 'Transmission Weight': 1.0, 'Roughness': 0.0, 'IOR': 1.34})[0]
label, nt, ink = mat('label', **{'Base Color': (0.86, 0.86, 0.84, 1), 'Roughness': 0.35})   # white ink
lab = image(nt, 'label.png'); fr, gl, tr, film, mx = (nt.nodes.new(t) for t in ('ShaderNodeFresnel', 'ShaderNodeBsdfGlossy', 'ShaderNodeBsdfTransparent', 'ShaderNodeMixShader', 'ShaderNodeMixShader'))
fr.inputs['IOR'].default_value = 1.45; gl.inputs['Roughness'].default_value = 0.05   # a thin clear film: see-through, glossy at grazing angles
nt.links.new(fr.outputs[0], film.inputs['Fac']); nt.links.new(tr.outputs[0], film.inputs[1]); nt.links.new(gl.outputs[0], film.inputs[2])
nt.links.new(lab.outputs['Alpha'], mx.inputs['Fac']); nt.links.new(film.outputs[0], mx.inputs[1]); nt.links.new(ink.outputs[0], mx.inputs[2])
nt.links.new(mx.outputs[0], nt.nodes['Material Output'].inputs['Surface'])

# ---------- carton 0.95 x 2.31 x 0.40: front +z, sides ±x, black ends ±y, plain gold back ----------
def make_box(p, r, s):
    W, H, D = 0.95 / 2, 2.31 / 2, 0.40 / 2
    bm = bmesh.new(); uv = bm.loops.layers.uv.new('UVMap'); V = {}
    def v(sx, sy, sz):
        k = (sx, sy, sz)
        if k not in V: V[k] = bm.verts.new((sx * W, sy * H, sz * D))
        return V[k]
    faces = [  # corners bottom-left, bottom-right, top-right, top-left as seen from outside; material
        ([(-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1)], 0), ([(1, -1, -1), (-1, -1, -1), (-1, 1, -1), (1, 1, -1)], 3),
        ([(1, -1, 1), (1, -1, -1), (1, 1, -1), (1, 1, 1)], 1), ([(-1, -1, -1), (-1, -1, 1), (-1, 1, 1), (-1, 1, -1)], 1),
        ([(-1, 1, 1), (1, 1, 1), (1, 1, -1), (-1, 1, -1)], 2), ([(-1, -1, -1), (1, -1, -1), (1, -1, 1), (-1, -1, 1)], 2)]
    for corners, mi in faces:
        f = bm.faces.new([v(*c) for c in corners]); f.material_index = mi
        for loop, t in zip(f.loops, ((0, 0), (1, 0), (1, 1), (0, 1))): loop[uv].uv = t
    ob = obj('box', to_mesh(bm, 'box', smooth=False, sharp=0), (box_front, box_side, box_end, box_back), p=p, r=r, s=s)
    bevel(ob, 0.006, 3)
    return ob

# ---------- vial: amber glass shell with thickness, serum inside, white print, aluminium crimp, white flip-off top ----------
def lathe(profile, seg=96, name='lathe', smooth=True, sharp=35):
    bm = bmesh.new(); rings = []
    for rr, y in profile:
        rings.append([bm.verts.new((0, y, 0))] if rr < 1e-6 else
                     [bm.verts.new((rr * math.sin(2 * math.pi * k / seg), y, rr * math.cos(2 * math.pi * k / seg))) for k in range(seg)])
    for a, c in zip(rings, rings[1:]):
        for k in range(seg):
            q = [a[k % len(a)], a[(k + 1) % len(a)], c[(k + 1) % len(c)], c[k % len(c)]]
            q = [x for i, x in enumerate(q) if x not in q[:i]]
            if len(q) >= 3: bm.faces.new(q)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return to_mesh(bm, name, smooth, sharp)


# the real proportions (photos): body ~1.6× taller than wide, a cap almost as wide as the body
OUTER = [(0, 0), (0.15, 0), (0.16, 0.015), (0.16, 0.56), (0.152, 0.592), (0.124, 0.622), (0.094, 0.640), (0.087, 0.652), (0.087, 0.672)]
INNER = [(0.075, 0.672), (0.075, 0.652), (0.082, 0.642), (0.114, 0.620), (0.140, 0.594), (0.148, 0.56), (0.148, 0.027), (0.138, 0.012), (0, 0.012)]
SERUM = [(0, 0.014), (0.137, 0.014), (0.146, 0.028), (0.146, 0.50), (0.14, 0.503), (0, 0.503)]   # clear, to just under the label top
CAP = [(0.084, 0.628), (0.118, 0.632), (0.146, 0.646), (0.156, 0.660), (0.157, 0.725), (0.153, 0.736), (0.143, 0.741),   # crimped skirt
       (0.084, 0.741), (0.080, 0.744), (0.078, 0.752), (0.074, 0.756), (0, 0.756)]                                            # flip-off button
LABEL_Y = (0.05, 0.43)   # prep_label.py
vial_meshes = dict(glass=lathe(OUTER + INNER, name='glass', sharp=60), serum=lathe(SERUM, name='serum', sharp=60), cap=lathe(CAP, name='cap', sharp=50))
bm = bmesh.new(); uvl = bm.loops.layers.uv.new('UVMap'); N = 128; ring = []
for j, y in enumerate(LABEL_Y):  # label sleeve over the body, u = 0 at the back; the print block (u = 0.5) faces +z
    ring.append([bm.verts.new((0.1615 * math.sin(math.pi + 2 * math.pi * k / N), y, 0.1615 * math.cos(math.pi + 2 * math.pi * k / N))) for k in range(N + 1)])
for k in range(N):
    f = bm.faces.new((ring[0][k], ring[0][k + 1], ring[1][k + 1], ring[1][k]))
    for loop, t in zip(f.loops, ((k / N, 0), ((k + 1) / N, 0), ((k + 1) / N, 1), (k / N, 1))): loop[uvl].uv = t
bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
vial_meshes['label'] = to_mesh(bm, 'label', sharp=0)


def make_vial(a, parent=root):
    g = obj('vial', parent=parent, p=a[:3], r=a[3:6], s=a[6])
    parts = [obj('glass', vial_meshes['glass'], (glass,), g), obj('serum', vial_meshes['serum'], (serum,), g),
             obj('label', vial_meshes['label'], (label,), g), obj('cap', vial_meshes['cap'], (alu,), g)]
    bevel(parts[3], 0.004, 3)
    for o in parts: o.visible_glossy = False  # the carton and the sachets do not mirror the ampoules (ghost vials in the foil)
    return g

# ---------- gel-mask sachet: gold foil pillow with the real print, flat sealed rim, white nozzle on the left ----------
def pillow_mesh(w=1.0, h=0.58, depth=0.018, nx=120, ny=70):  # a flat sachet, a slight puff in the middle
    bm = bmesh.new(); uv = bm.loops.layers.uv.new('UVMap'); F, B = {}, {}
    for i in range(nx + 1):
        for j in range(ny + 1):
            x, y = i / nx * 2 - 1, j / ny * 2 - 1
            seal = abs(x) > 0.95 or abs(y) > 0.89
            z = 0 if seal else depth * (1 - abs(x / 0.95) ** 4) * (1 - abs(y / 0.89) ** 4)
            F[i, j] = bm.verts.new((x * w / 2, y * h / 2, z + 0.0006))
            B[i, j] = bm.verts.new((x * w / 2, y * h / 2, -z - 0.0006))
    for i in range(nx):
        for j in range(ny):
            ids = ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))
            f = bm.faces.new([F[k] for k in ids]); f.material_index = 0
            for loop, k in zip(f.loops, ids): loop[uv].uv = (k[0] / nx, k[1] / ny)
            f = bm.faces.new([B[k] for k in reversed(ids)]); f.material_index = 1
            for loop, k in zip(f.loops, reversed(ids)): loop[uv].uv = (1 - k[0] / nx, k[1] / ny)
    return to_mesh(bm, 'pillow', sharp=0)


PILLOW = pillow_mesh()
SPOUT = lathe([(0, -0.045), (0.034, -0.045), (0.028, 0.045), (0, 0.045)], 48, 'spout')
CAP = lathe([(0, -0.04), (0.048, -0.04), (0.048, 0.04), (0, 0.04)], 48, 'cap')


def make_pouch(a, parent=root):
    g = obj('pouch', parent=parent, p=a[:3], r=a[3:6], s=a[6])
    obj('pillow', PILLOW, (sachet_front, sachet_back), g)
    m = -1 if MIRROR else 1   # the spout stays on the screen's left (owner 17/10: the sachet as now), whatever the mirror
    sp = obj('spout', SPOUT, (nozzle,), g, p=(-0.54 * m, 0, 0), r=(0, 0, math.pi / 2 * m))
    cp = obj('cap', CAP, (nozzle,), g, p=(-0.62 * m, 0, 0), r=(0, 0, math.pi / 2 * m)); bevel(cp, 0.008, 2)
    for o in g.children: o.visible_glossy = False  # the foil of the carton (and of the next sachet) never mirrors a sachet's dark back
    return g

# ---------- light: dark room, white softbox left, warm gold right, gold strip above, warm fills in front ----------
def panel(color, strength, x, y, z, w, h, ry, rx=0, soft=0.3, round_=False):
    """Softbox card seen only in reflections: even light, the outer `soft` part of each half-side fades out
    (round_: an elliptic spot fading from the centre instead, for glints with no corners)."""
    m, nt, _ = mat('panel')
    em = nt.nodes.new('ShaderNodeEmission'); em.inputs['Color'].default_value = (*color, 1)
    tc, mp, sep, mt = (nt.nodes.new(t) for t in ('ShaderNodeTexCoord', 'ShaderNodeMapping', 'ShaderNodeSeparateXYZ', 'ShaderNodeMath'))
    mp.inputs['Scale'].default_value = (2 / w, 2 / h, 1); mt.operation = 'MULTIPLY'
    nt.links.new(tc.outputs['Object'], mp.inputs['Vector']); nt.links.new(mp.outputs['Vector'], sep.inputs['Vector'])
    edges = []
    for axis in (() if round_ else ('X', 'Y')):
        ab, fr = nt.nodes.new('ShaderNodeMath'), nt.nodes.new('ShaderNodeMapRange'); ab.operation = 'ABSOLUTE'
        fr.inputs['From Min'].default_value = 1 - soft; fr.inputs['From Max'].default_value = 1.0
        fr.inputs['To Min'].default_value = 1.0; fr.inputs['To Max'].default_value = 0.0; fr.interpolation_type = 'SMOOTHSTEP'
        nt.links.new(sep.outputs[axis], ab.inputs[0]); nt.links.new(ab.outputs[0], fr.inputs['Value']); edges.append(fr)
    if round_:
        ln, fr = nt.nodes.new('ShaderNodeVectorMath'), nt.nodes.new('ShaderNodeMapRange'); ln.operation = 'LENGTH'
        fr.inputs['From Min'].default_value = 1 - soft; fr.inputs['From Max'].default_value = 1.0
        fr.inputs['To Min'].default_value = 1.0; fr.inputs['To Max'].default_value = 0.0; fr.interpolation_type = 'SMOOTHSTEP'
        nt.links.new(mp.outputs['Vector'], ln.inputs[0]); nt.links.new(ln.outputs['Value'], fr.inputs['Value']); edges = [fr, fr]
    nt.links.new(edges[0].outputs['Result'], mt.inputs[0]); nt.links.new(edges[1].outputs['Result'], mt.inputs[1])
    st = nt.nodes.new('ShaderNodeMath'); st.operation = 'MULTIPLY'; st.inputs[1].default_value = strength
    nt.links.new(mt.outputs[0], st.inputs[0]); nt.links.new(st.outputs[0], em.inputs['Strength'])
    nt.links.new(em.outputs[0], nt.nodes['Material Output'].inputs['Surface'])
    bm = bmesh.new(); bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=0.5)
    for v in bm.verts: v.co = Vector((v.co.x * w, v.co.y * h, 0))
    ob = obj('panel', to_mesh(bm, 'panel', sharp=0), (m,), p=(x, y, z), r=(rx, ry, 0))
    ob.visible_camera = False; ob.visible_shadow = False
    return ob


def srgb(hexv):
    c = [((hexv >> s) & 255) / 255 for s in (16, 8, 0)]
    return tuple(v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in c)


def area(name, color, power, pos, target, size):  # lamps light the scene but are not mirrored: the cards shape the reflections
    li = bpy.data.lights.new(name, 'AREA'); li.energy = power; li.color = color; li.size = size
    ob = obj(name, li); ob.matrix_basis = look_matrix(pos, target); ob.visible_glossy = False
    return ob


def only_on(emitter, *receivers):  # light linking: this lamp or card lights (and is mirrored by) these objects alone
    c = bpy.data.collections.new(f'{emitter.name}-receivers')
    for o in receivers: c.objects.link(o)
    emitter.light_linking.receiver_collection = c


def mirror_dir(p, r):  # where a flat face at p, turned by r, mirrors the camera
    n = Euler(r, 'ZYX').to_matrix() @ Vector((0, 0, 1)); v = (Vector(S['cam']) - Vector(p)).normalized()
    return 2 * v.dot(n) * n - v


def card_at(color, strength, p, r, dist, w, h, soft, round_=False):  # a soft card on the mirror ray of a face, turned to face it
    c = Vector(p) + dist * mirror_dir(p, r); ob = panel(color, strength, *c, w, h, 0, soft=soft, round_=round_)
    ob.matrix_basis = look_matrix(tuple(c), tuple(p)); return ob


def fill_card(a, pouch, g=1.0):  # a sachet alone on a screen: a card on its mirror ray keeps the print on light, and a low warm
    # card under it lights the lower bulge (it mirrored the black void: a dark band under GEL MASK), both for the sachet
    # alone; g < 1 while a kit takes over (S5→S6): the cards turn transparent (fadeable()), not dark, or the fan
    # mirrors black cards until the key frame and brightens at once
    meshes = [o for o in pouch.children_recursive if o.type == 'MESH']
    cards = [card_at(srgb(0xfff3e0), 2.5, a[:3], a[3:6], 3.0, 1.8, 1.2, 0.4)]
    for off, k, w, h in (((0, -2.2, 1.3), 1.6, 3.6, 2.0), ((0, 2.0, 1.6), 1.4, 3.0, 1.4)):   # under and above: no black frame in the bulge
        c = Vector(a[:3]) + Vector(off); cd = panel(srgb(0xf3dcb0), k, *c, w, h, 0, soft=0.6)
        cd.matrix_basis = look_matrix(tuple(c), tuple(a[:3])); cards.append(cd)
    for cd in cards: only_on(cd, *meshes); cd.color[3] = g


# near-white cards (the foil itself gives the gold), with a dark gap in front so the mirror shows bands, as in the packshot
panel(srgb(0xffffff), 3.0, -4.5, 0.6, 2.5, 6, 6, math.pi / 2)  # tall, and long towards the viewer: a carton turning from S1 to S2 never mirrors a dark gap
# (bars with gaps here put a dark band over the S1 wordmark: the foil's bows send part of the front's mirror into this card)
panel(srgb(0xf3dcb0), 2.0, 4.8, 0.4, -0.5, 1.2, 4, -math.pi / 2, soft=0.45)  # a streak, not a flat glow, on the side face
panel(srgb(0xe8d6a8), 1.5, 0, 3.8, -2, 7, 1.2, 0, math.pi / 2)
# the carton front mirrors x -3.6..-1.7 of this wall in S1 and x -2.4..-0.5 in the kit: light bars with narrow dark gaps,
# so the foil shows bands as in the packshot while the print stays on light; tall enough for the print low on the carton
WX, WY = S.get('wall', (0, 0))  # a shot whose carton faces elsewhere (phone) moves the whole wall into its mirror
for x, w, k in ((-3.45, 1.9, 1.5), (-1.85, 0.8, 1.6), (-0.9, 0.5, 1.6), (0.3, 1.0, 1.8)):
    panel(srgb(0xfff3e0), k, x + WX, WY, 5.6, w, 6.6, math.pi, soft=0.15)
for x in (-3.0, -1.75):  # two narrow hot strips in front of the cards: the clipped white streaks of the real foil
    panel(srgb(0xffffff), 9.0, x + WX, WY, 5.5, 0.16, 6.6, math.pi, soft=0.4)
panel(srgb(0xf3dcb0), 1.8, 5.0, 0.5, -3.8, 2, 5, -0.675)  # back-right strip: a gold edge on the carton's right side
area('key', (1, 1, 1), 800, (4.5, 4.5, 4.5), (2.0, 0, 0), 2.5)  # upper right, where the smoke is brightest
area('fill', srgb(0xfff3e0), 320, (-3, 2, 5), (1.5, 0, 0), 3.0)
area('rim', srgb(0xf3dcb0), 400, (4.6, 1.6, 1.0), (2.0, 0, -0.5), 1.2)
world = bpy.data.worlds.new('room'); scn.world = world; world.use_nodes = True
world.node_tree.nodes['Background'].inputs['Color'].default_value = (0.006, 0.005, 0.004, 1)

# ---------- shot ----------
def backlight(x, y, z, w, h, ry=0.0, k=1.4, a=1.0):  # seen only through the glass (as in packshot photography): the serum
    # glows orange; a < 1 (a transition): the card turns transparent with its glass, it never blacks out the glass behind
    bl = panel(srgb(0xffe2a6), k, x, y, z, w, h, ry); bl.visible_glossy = False; bl.visible_diffuse = False; bl.color[3] = a


if 'box' in S: tag(make_box(S['box']['p'], S['box']['r'], S['box']['s']), 'box')
for a in S.get('vials', []):   # each floats; backlit from behind as in packshot photography, the amber glows through the clear serum
    v = tag(make_vial(a), 'vials'); k = a[6] / 0.58
    backlight(a[0], a[1] + 0.3 * k, a[2] - 0.7 * k, 0.6 * k, 0.55 * k)
    # the silver top mirrors a soft light above it, as in the photos: a disk lamp, not a card — a card linked to the cap
    # alone is still a black blocker for every other mirror (in the kit 5 of them hid the carton's V in a dark band)
    c = Vector(a[:3]) + Vector((0, 1.3 * k, 0.5 * k)); li = bpy.data.lights.new('top', 'AREA'); li.shape = 'DISK'
    li.size = 0.9 * k; li.color = srgb(0xfff6ea); li.energy = 4.0 * math.pi * (0.45 * k) ** 2   # = the card's strength 4 over its area
    top = obj('top', li); top.matrix_basis = look_matrix(tuple(c), tuple(Vector(a[:3]) + Vector((0, 0.45 * k, 0)))); top.visible_diffuse = False
    only_on(top, *[o for o in v.children if o.name.startswith('cap')])
SOLO = S.get('solo', float(len(S.get('pouches', [])) == 1))   # 1: a sachet alone on its screen, 0: the kit fan, between: S5→S6
for a in S.get('pouches', []):
    pc = tag(make_pouch(a), 'pouches')
    if SOLO > 0:   # a sachet alone: its own fill card, and not mirrored in the far carton (a dark T on the foil)
        fill_card(a, pc, SOLO)
    if SOLO < 1:   # the kit fan: a soft card on each sachet's mirror ray, NOT light-linked (linked cards black out each
        # other's mirrors and the fan went dark); fades in with the kit (fadeable), no jump at the key frame
        card_at(srgb(0xfff3e0), 1.6, a[:3], a[3:6], 3.0, 2.6, 1.4, 0.45).color[3] = 1 - SOLO
if S.get('pouches') and SOLO < 1:  # kit: a low wide card under the camera, so the sachet fan mirrors light, not the dark void
    panel(srgb(0xfff3e0), 1.6, -1.8, -3.0, 4.6, 6.4, 2.4, math.pi, rx=-0.5, soft=0.35).color[3] = 1 - SOLO


def fadeable():  # a transition frame: light cards fade by their object's alpha (fill_card, the kit card), never by strength
    for m in bpy.data.materials:
        nt = m.node_tree; out = nt.nodes['Material Output']; al = nt.nodes.new('ShaderNodeObjectInfo').outputs['Alpha']
        for sock in (out.inputs['Surface'], out.inputs['Volume']):
            if not sock.is_linked: continue
            src = sock.links[0].from_socket; mx = nt.nodes.new('ShaderNodeMixShader'); nt.links.new(al, mx.inputs['Fac'])
            if sock.name == 'Surface': nt.links.new(nt.nodes.new('ShaderNodeBsdfTransparent').outputs[0], mx.inputs[1])
            nt.links.new(src, mx.inputs[2]); nt.links.new(mx.outputs[0], sock)   # a volume mixed with nothing: its density × alpha


if '>' in SHOT: fadeable()
if PART:  # one Figma layer: the other parts stay in the scene for shadows and reflections but the camera does not see them
    for o in scn.objects:
        if o.get('part') and o['part'] != PART: o.visible_camera = False
cam = obj('camera', bpy.data.cameras.new('camera'), parent=None); cam.data.sensor_fit = 'VERTICAL'
cam.data.lens = cam.data.sensor_height / (2 * math.tan(math.radians(S.get('fov', 35)) / 2))
# placed in the world, not under the mirrored root: a camera with a negative scale would undo the mirror; its own x is
# flipped as well, so it stays a proper rotation and the frame comes out as the mirror image
F = Matrix.Diagonal((-1, 1, 1, 1)) if MIRROR else Matrix.Identity(4)
cam.matrix_world = Matrix.Rotation(math.pi / 2, 4, 'X') @ F @ look_matrix(S['cam'], S['look']) @ F
cam.data.clip_start = 0.1; cam.data.clip_end = 80; scn.camera = cam
if S.get('fstop'):   # a shallow focus puts the far carton behind the hero (S3 ampoule, S4 sachet)
    cam.data.dof.use_dof = True; cam.data.dof.aperture_fstop = S['fstop']; cam.data.dof.focus_distance = (Vector(S['focus']) - Vector(S['cam'])).length

r, c = scn.render, scn.cycles
r.engine = 'CYCLES'; c.device = 'CPU'; c.samples = SAMPLES; c.use_adaptive_sampling = True; c.adaptive_threshold = 0.006
if os.environ.get('VT_DEVICE'):   # a GPU backend, e.g. METAL on the owner's M4 Mac (render_mac.sh); the default is the CPU
    pr = bpy.context.preferences.addons['cycles'].preferences; pr.compute_device_type = os.environ['VT_DEVICE']; pr.get_devices()
    for d in pr.devices: d.use = d.type != 'CPU'
    c.device = 'GPU'
c.use_denoising = True; c.denoiser = 'OPENIMAGEDENOISE'
c.max_bounces = 16; c.diffuse_bounces = 3; c.glossy_bounces = 8; c.transmission_bounces = 16; c.transparent_max_bounces = 16
c.caustics_reflective = False; c.caustics_refractive = False; c.blur_glossy = 0.5; c.sample_clamp_indirect = 5  # no blotches in the glass
r.film_transparent = True; c.film_transparent_glass = True
r.resolution_x = WIDTH; r.resolution_y = round(WIDTH / S['aspect']); r.resolution_percentage = 100
if os.environ.get('VT_BORDER'):   # 'x0,y0,x1,y1' (fractions, y from the top): render only that region at full size, to judge details at 100%
    x0, y0, x1, y1 = (float(v) for v in os.environ['VT_BORDER'].split(','))
    r.use_border = r.use_crop_to_border = True; r.border_min_x, r.border_max_x, r.border_min_y, r.border_max_y = x0, x1, 1 - y1, 1 - y0
scn.view_settings.view_transform = 'Filmic'; scn.view_settings.look = 'Medium High Contrast'  # Filmic keeps the foil yellow; AgX turns it peach
scn.view_settings.exposure = S.get('exposure', 0)
if OUT.endswith('.webp'):   # straight from Blender (the Mac has no PIL): 8-bit RGBA, VT_WEBP_Q 86 as the live page's frames, 100 = lossless
    r.image_settings.file_format = 'WEBP'; r.image_settings.color_mode = 'RGBA'; r.image_settings.quality = int(os.environ.get('VT_WEBP_Q', 86))
else:
    r.image_settings.file_format = 'PNG'; r.image_settings.color_mode = 'RGBA'; r.image_settings.color_depth = '16'
r.filepath = OUT
bpy.ops.render.render(write_still=True)

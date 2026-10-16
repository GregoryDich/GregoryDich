"""V-TECH SYSTEM path-traced in Blender Cycles (PLAN §8, stage 1: the HD series).
Same shots and poses as ../render-vtech.html (story: site/story3d.json, stories[0]), with the kit at true scale.
Everything is built in three.js coordinates (Y up) under a root empty turned 90° about X; Blender Euler 'ZYX' equals
three.js 'XYZ'. Print maps come from prep_tex.py (albedo/metal/rough).
usage: <python with bpy 4.2> vtech_scene.py <tex dir> <out.png> <shot> [width=2880] [samples=256] [part]
shots: v1-meet v2-why v3-inside v4-feel v5-protocol v6-kit kit-hd (desktop), m1-meet m4-feel (phone 390x844);
a transition frame is 'A>B@t' (t 0..1), e.g. 'v1-meet>v2-why@0.4' (render_seq.py renders the whole run).
part (box|skin|tray|vials|drops|pouches) renders that layer alone, every other object a holdout, for the Figma layers.
The frame is rendered on a transparent film; compose.py lays it over layers/vt-bg-wide.jpg (phone: a portrait slice of it)."""
import bpy, bmesh, math, os, sys
from mathutils import Euler, Matrix, Vector

TEX, OUT, SHOT = sys.argv[1:4]
WIDTH = int(sys.argv[4]) if len(sys.argv) > 4 else 2880
SAMPLES = int(sys.argv[5]) if len(sys.argv) > 5 else 256
PART = sys.argv[6] if len(sys.argv) > 6 else None

# kit: the insert at 0.62 so a vial body is ~0.2 of the carton width, as in the packshot; the sachets fan out to the right
# as in the storyboard, about the carton's width, clear of the last vial; the carton leans back a little so it does not
# mirror the vials
POUCHES = [[3.5 + i * 0.1, -0.32 - i * 0.05, -0.85 + i * 0.2, 0.12, -0.62, -0.2 + i * 0.09, 0.88] for i in range(5)]
KIT = dict(box=dict(p=(2.25, 0.55, -1.8), r=(-0.03, -0.32, 0.01), s=0.95), tray=dict(p=(2.3, -0.88, -0.45), r=(0.36, -0.36, 0), s=0.62), pouches=POUCHES)
DESK = dict(aspect=1.6, cam=(0, 0, 7), look=(0.9, 0, 0), exposure=-0.8)
PHONE = dict(aspect=390 / 844, fov=44, cam=(0, 0, 7), look=(0, 0.9, 0), exposure=-0.8)
SHOTS = {
    'v1-meet': dict(DESK, box=dict(p=(1.8, -0.05, 0.2), r=(0.06, -0.48, 0.0), s=1)),
    # S2: the carton stays behind in 3/4, dimmed, turned so its front mirrors the banded front wall as in S1 (at -0.72
    # it mirrored the plain left card and read as matte cream card); below right a plane of abstract skin (right half
    # only, the copy keeps the left), microchannels flash in rows of gold points
    'v2-why': dict(DESK, focus=(2.4, -1.2, 0.5), fstop=0.5, box=dict(p=(2.85, 0.55, -2.2), r=(0.04, -0.5, 0.02), s=0.9, dim=0.45),
                   skin=dict(p=(2.4, -1.2, 0.5), r=(-1.12, 0, 0.1), w=3.4, h=2.4, dots=1.0)),
    # S3: the insert with the vials, the centre vial lifted clear of the row towards the viewer, a clear drop with pearl
    # spheres above it
    'v3-inside': dict(DESK, box=dict(p=(4.0, 0.6, -2.4), r=(0.04, -0.42, 0.01), s=0.95),  # aside, so the drop is seen on the dark
                      tray=dict(p=(2.2, -0.95, -0.3), r=(0.38, -0.36, 0), s=0.65, lift=2),
                      vials=[[1.456, -0.728, 2.2, 0.02, -0.12, 0, 0.58]]),  # in front of the empty centre well; the drop is out for now
                      # (the owner, 16/10: it looks unnatural; a drop of blue liquid with gold exosomes goes to a separate sample)
    # S4: sachet no. 1 in front, clear of the carton far behind; a thin wet gel film on part of the skin (relief smoothed
    # under it, edge = before/after)
    'v4-feel': dict(DESK, gain=1.15, focus=(1.6, -0.7, 1.0), fstop=1.0,   # focus between the sachet and the gel
                    box=dict(p=(5.0, 1.4, -3.6), r=(0.16, -0.56, 0.0), s=0.8, dim=0.4),  # its whole face mirrors the lit wall (no dark T)
                    skin=dict(p=(2.45, -1.3, 0.6), r=(-1.18, 0, 0.08), w=3.6, h=2.4, dots=0.35, gel=True),
                    pouches=[[1.6, -0.1, 1.4, 0.28, -0.32, 0.12, 0.9]]),
    # S5: three stations seated on the gold line (parallel to the screen), right to left: a skin puck with points, the
    # vial with a drop above, the sachet; z follows the line
    # (placed by projection: the line at y 620 of 900, x 770-1320 of 1440, the stations at 880 / 1045 / 1210; the puck
    # stands tilted back 20° with its lowest, back rim on the rod, so its front rim stays above the line on screen)
    'v5-protocol': dict(DESK, skin=dict(p=(3.112, -0.406, 0.645), r=(-0.35, 0, 0), w=0.75, h=0.75, dots=1.0, disk=True),
                        vials=[[2.349, -0.786, 0.6, 0.04, -0.3, 0, 0.75]],
                        pouches=[[1.586, -0.563, 0.537, 0.15, 0.0, 0.0, 0.8]], line=dict(c=(2.349, -0.792, 0.6), L=2.56)),
    'v6-kit': dict(aspect=1.6, cam=(0.4, 0.1, 6.6), look=(1.22, 0.15, 0), **KIT),  # closer than S1 (true-scale kit); group spans 0.54-0.95 of the width
    'kit-hd': dict(aspect=1400 / 1100, fov=29, cam=(3.05, 0.82, 6.0), look=(3.05, 0.22, 0), **KIT),  # centred, even margins
    'm1-meet': dict(PHONE, wall=(-3.5, 5.6), box=dict(p=(0.05, 2.4, 0), r=(0.06, -0.42, 0.04), s=0.85)),  # its front mirrors x≈-6, y≈5.6
    'm4-feel': dict(PHONE, skin=dict(p=(0, 1.45, 0.3), r=(-0.78, 0, 0.05), w=2.4, h=1.6, dots=0.35, gel=True),
                    pouches=[[0.05, 2.45, 0.9, 0.25, -0.3, 0.1, 1.0]]),
}


def ease(t): return t * t * (3 - 2 * t)
def lerp(a, b, t): return tuple(x + (y - x) * t for x, y in zip(a, b))
def clamp01(v): return min(1.0, max(0.0, v))


def blend(A, B, t):
    """The pose between two screens at t (0..1), for the scroll sequences: the carton and the camera move along a
    smoothstep; a skin plane that only B has rises from below the frame at a grazing angle and fades in, then its
    microchannels open in a wave (story3d S1→S2)."""
    e = ease(t); S = dict(B)
    S['cam'], S['look'] = lerp(A['cam'], B['cam'], e), lerp(A['look'], B['look'], e)
    S['exposure'] = A.get('exposure', 0) + (B.get('exposure', 0) - A.get('exposure', 0)) * e
    if A.get('fstop') or B.get('fstop'):   # focus pull: aperture (1/f-stop) and focus point along the same ease
        ap = (1 / A['fstop'] if A.get('fstop') else 0) * (1 - e) + (1 / B['fstop'] if B.get('fstop') else 0) * e
        fa, fb = A.get('focus', A.get('box', {}).get('p', A['look'])), B.get('focus', B.get('box', {}).get('p', B['look']))
        S['fstop'], S['focus'] = (1 / ap if ap > 0.02 else None), lerp(fa, fb, e)
    if 'box' in A and 'box' in B:
        S['box'] = dict(p=lerp(A['box']['p'], B['box']['p'], e), r=lerp(A['box']['r'], B['box']['r'], e),
                        s=A['box']['s'] + (B['box']['s'] - A['box']['s']) * e,
                        dim=A['box'].get('dim', 1) + (B['box'].get('dim', 1) - A['box'].get('dim', 1)) * e)
    if 'skin' in B and 'skin' not in A:
        k = dict(B['skin']); a = ease(clamp01((t - 0.2) / 0.6))
        k['p'] = lerp((k['p'][0], k['p'][1] - 1.4, k['p'][2] + 0.4), k['p'], a)
        k['r'] = lerp((k['r'][0] - 0.3, k['r'][1], k['r'][2]), k['r'], a)
        k['alpha'], k['wave'] = a, clamp01((t - 0.55) / 0.45)
        S['skin'] = k
    return S


if '>' in SHOT:   # 'v1-meet>v2-why@0.35': a frame of the transition
    a, rest = SHOT.split('>'); b, t = rest.split('@'); S = blend(SHOTS[a], SHOTS[b], float(t))
else:
    S = SHOTS[SHOT]

bpy.ops.wm.read_factory_settings(use_empty=True)
scn = bpy.context.scene
root = bpy.data.objects.new('root', None); scn.collection.objects.link(root); root.rotation_euler = (math.pi / 2, 0, 0)


def obj(name, data=None, mats=(), parent=root, p=(0, 0, 0), r=(0, 0, 0), s=1):
    ob = bpy.data.objects.new(name, data); scn.collection.objects.link(ob)
    for m in mats: ob.data.materials.append(m)
    ob.parent = parent; ob.location = p; ob.rotation_mode = 'ZYX'; ob.rotation_euler = r; ob.scale = (s, s, s)
    return ob


def tag(ob, part):  # the Figma layer an object belongs to (box, skin, tray, vials, drops, pouches)
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
    n.image.colorspace_settings.name = 'Non-Color' if data else 'sRGB'; return n


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
    nt.links.new(image(nt, f'{key}-rough.png', True).outputs['Color'], b.inputs['Roughness'])
    relief(nt, b, layers)
    return m


GOLD = (0.87, 0.57, 0.18, 1)  # linear of the packshot foil (sRGB 0.94, 0.78, 0.46)
# carton: a few broad vertical bows in the sleeve (crisp light/dark bands in the mirror) + a faint fine crinkle
FOIL = (((1.0, 0.15, 1.0), 1.3, 0.0, 0.035), ((1.0, 0.5, 1.0), 0.9, 0.0, 0.008))  # broad bows + a few soft wrinkles, nothing fine
DIM = S.get('box', {}).get('dim', 1.0)
box_front = printed('box-front', 'box-front', FOIL, DIM)
box_side = printed('box-side', 'box-side', FOIL, DIM)
box_back, nt, b = mat('box-back', **{'Base Color': tuple(c * DIM for c in GOLD[:3]) + (1,), 'Metallic': 1.0, 'Roughness': 0.06}); relief(nt, b, FOIL)
box_end = mat('box-end', **{'Base Color': (0.015, 0.015, 0.016, 1), 'Roughness': 0.3, 'Specular IOR Level': 0.5})[0]
# sachet: glossy foil with two or three soft dents and a fine crinkle, no stretched streaks
SACHET = (((1.4, 1.4, 1.4), 1.8, 0.0, 0.02), ((1, 1, 1), 26.0, 0.0, 0.0002))
sachet_front = printed('sachet-front', 'sachet', SACHET)
# the plain back shows only at the rims: a paler, satin gold, so the edges do not read orange
sachet_back, nt, b = mat('sachet-back', **{'Base Color': (0.85, 0.66, 0.36, 1), 'Metallic': 1.0, 'Roughness': 0.2}); relief(nt, b, SACHET)
white = mat('white-plastic', **{'Base Color': (0.85, 0.85, 0.83, 1), 'Roughness': 0.28, 'Coat Weight': 0.4, 'Coat Roughness': 0.1})[0]
nozzle = mat('nozzle', **{'Base Color': (0.9, 0.9, 0.88, 1), 'Roughness': 0.35, 'Subsurface Weight': 0.4, 'Subsurface Scale': 0.01})[0]  # milky PP
alu = mat('aluminium', **{'Base Color': (0.92, 0.92, 0.92, 1), 'Metallic': 1.0, 'Roughness': 0.3})[0]
# amber glass, seen at the shoulder and the base; the body is wrapped in the red-orange label as on the real vials
glass = mat('amber-glass', **{'Base Color': (1.0, 0.6, 0.3, 1), 'Transmission Weight': 1.0, 'Roughness': 0.015, 'IOR': 1.5})[0]
serum, nt, b = mat('serum', **{'Base Color': (1, 1, 1, 1), 'Transmission Weight': 1.0, 'Roughness': 0.0, 'IOR': 1.34})
va = nt.nodes.new('ShaderNodeVolumeAbsorption'); va.inputs['Color'].default_value = (0.95, 0.38, 0.06, 1); va.inputs['Density'].default_value = 5  # the shoulder glows, not black
nt.links.new(va.outputs[0], nt.nodes['Material Output'].inputs['Volume'])
# glossy red-orange label film (packshot: hue 20°, saturation 0.96, value 0.76) with the white print on it
label, nt, b = mat('label', **{'Roughness': 0.3, 'Coat Weight': 0.5, 'Coat Roughness': 0.08})
mix, lab = nt.nodes.new('ShaderNodeMixRGB'), image(nt, 'label.png')
mix.inputs['Color1'].default_value = (0.45, 0.062, 0.002, 1); mix.inputs['Color2'].default_value = (0.83, 0.83, 0.81, 1)
nt.links.new(lab.outputs['Alpha'], mix.inputs['Fac']); nt.links.new(mix.outputs['Color'], b.inputs['Base Color'])
tray_mat, nt, b = mat('tray', **{'Base Color': (0.012, 0.012, 0.012, 1), 'Roughness': 0.3, 'Specular IOR Level': 0.5,
                                  'Coat Weight': 0.3, 'Coat Roughness': 0.15})  # glossy neutral black plastic
relief(nt, b, (((1, 1, 1), 400.0, 2.0, 0.0004),))

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


OUTER = [(0, 0), (0.15, 0), (0.16, 0.015), (0.16, 0.43), (0.15, 0.47), (0.1, 0.505), (0.086, 0.53), (0.086, 0.55)]
INNER = [(0.074, 0.55), (0.074, 0.53), (0.088, 0.508), (0.138, 0.472), (0.148, 0.43), (0.148, 0.027), (0.138, 0.012), (0, 0.012)]
SERUM = [(0, 0.014), (0.137, 0.014), (0.146, 0.028), (0.146, 0.425), (0, 0.425)]  # filled to the shoulder
vial_meshes = dict(glass=lathe(OUTER + INNER, name='glass', sharp=60), serum=lathe(SERUM, name='serum', sharp=60),
                   crimp=lathe([(0, 0.505), (0.104, 0.505), (0.104, 0.555), (0, 0.555)], name='crimp'),
                   # flip-off cap: flared skirt ~0.85 of the body width over a short aluminium crimp, flat disc on top
                   top=lathe([(0, 0.545), (0.122, 0.545), (0.132, 0.552), (0.135, 0.62), (0.13, 0.632), (0.12, 0.635), (0.12, 0.645),
                              (0.112, 0.652), (0, 0.652)], name='top'))
bm = bmesh.new(); uvl = bm.loops.layers.uv.new('UVMap'); N = 128; ring = []
for j, y in enumerate((0.035, 0.42)):  # label sleeve over the body, u = 0 at the back; the print block (u = 0.5) faces +z
    ring.append([bm.verts.new((0.1615 * math.sin(math.pi + 2 * math.pi * k / N), y, 0.1615 * math.cos(math.pi + 2 * math.pi * k / N))) for k in range(N + 1)])
for k in range(N):
    f = bm.faces.new((ring[0][k], ring[0][k + 1], ring[1][k + 1], ring[1][k]))
    for loop, t in zip(f.loops, ((k / N, 0), ((k + 1) / N, 0), ((k + 1) / N, 1), (k / N, 1))): loop[uvl].uv = t
bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
vial_meshes['label'] = to_mesh(bm, 'label', sharp=0)


def make_vial(a, parent=root):
    g = obj('vial', parent=parent, p=a[:3], r=a[3:6], s=a[6])
    parts = [obj('glass', vial_meshes['glass'], (glass,), g), obj('serum', vial_meshes['serum'], (serum,), g),
             obj('label', vial_meshes['label'], (label,), g), obj('crimp', vial_meshes['crimp'], (alu,), g), obj('top', vial_meshes['top'], (white,), g)]
    bevel(parts[3], 0.006, 3); bevel(parts[4], 0.003, 2)
    for o in parts: o.visible_glossy = False  # the carton and the sachets do not mirror the amber vials (copper sachets, ghost vials)
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
    sp = obj('spout', SPOUT, (nozzle,), g, p=(-0.54, 0, 0), r=(0, 0, math.pi / 2))
    cp = obj('cap', CAP, (nozzle,), g, p=(-0.62, 0, 0), r=(0, 0, math.pi / 2)); bevel(cp, 0.008, 2)
    sp.visible_glossy = cp.visible_glossy = False  # no ghost nozzles mirrored in the next sachet
    return g

# ---------- black insert: 5 vial wells (real recesses), the vials standing in them ----------
def make_tray(t):
    W, H, D = 2.15, 0.16, 1.0
    g = obj('tray', parent=root, p=t['p'], r=t['r'], s=t['s'])
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts: v.co = Vector((v.co.x * W, v.co.y * H, v.co.z * D))
    slab = obj('slab', to_mesh(bm, 'slab', smooth=False, sharp=0), (tray_mat,), g); bevel(slab, 0.012, 3)
    cutters = bpy.data.collections.new('cutters'); scn.collection.children.link(cutters)
    well = lathe([(0, H / 2 - 0.07), (0.168, H / 2 - 0.07), (0.168, H / 2 + 0.05), (0, H / 2 + 0.05)], 96, 'well')
    for i in range(5):
        c = bpy.data.objects.new('well', well); cutters.objects.link(c); c.parent = g; c.location = (-0.78 + i * 0.39, 0, -0.2); c.hide_render = True
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts: v.co = Vector((v.co.x * 1.6, v.co.y * 0.05 + H / 2, v.co.z * 0.32))
    c = bpy.data.objects.new('bed', to_mesh(bm, 'bed', smooth=False, sharp=0)); cutters.objects.link(c); c.parent = g; c.location = (0, 0, 0.27); c.hide_render = True
    bo = slab.modifiers.new('wells', 'BOOLEAN'); bo.operation = 'DIFFERENCE'; bo.operand_type = 'COLLECTION'; bo.collection = cutters; bo.solver = 'EXACT'
    tag(slab, 'tray')
    for i, jit in enumerate((0.05, -0.04, 0.02, -0.06, 0.04)):  # turned towards the camera, a little unevenly
        if t.get('lift') == i: continue   # this vial came out of its well (S3): the shot places it on its own
        tag(make_vial((-0.78 + i * 0.39, H / 2 - 0.02, -0.2, 0, 0.09 + jit, 0, 0.9), g), 'vials')
    return g

# ---------- shader math helpers ----------
def fx(nt, op, a=None, b=None):
    """Math node: a, b are sockets or numbers; returns the output socket."""
    n = nt.nodes.new('ShaderNodeMath'); n.operation = op
    for i, v in enumerate((a, b)):
        if v is None: continue
        if isinstance(v, (int, float)): n.inputs[i].default_value = v
        else: nt.links.new(v, n.inputs[i])
    return n.outputs[0]


def step(nt, x, a, b):
    """Smoothstep of x from a (0) to b (1); a > b gives the falling edge."""
    n = nt.nodes.new('ShaderNodeMapRange'); n.interpolation_type = 'SMOOTHSTEP'; n.clamp = True
    n.inputs['From Min'].default_value = a; n.inputs['From Max'].default_value = b; nt.links.new(x, n.inputs['Value'])
    return n.outputs['Result']

# ---------- abstract skin: warm dark micro-relief, microchannels as rows of gold points, optional wet gel film ----------
def noise(nt, vec, scale, detail=2.0):
    n = nt.nodes.new('ShaderNodeTexNoise'); n.inputs['Scale'].default_value = scale; n.inputs['Detail'].default_value = detail
    nt.links.new(vec, n.inputs['Vector']); return n.outputs['Fac']


def voronoi(nt, vec, scale, feature='F1', stretch=(1, 1, 1), turn=0.0):
    mp = nt.nodes.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = stretch; mp.inputs['Rotation'].default_value = (0, 0, turn)
    v = nt.nodes.new('ShaderNodeTexVoronoi'); v.feature = feature; v.inputs['Scale'].default_value = scale
    nt.links.new(vec, mp.inputs['Vector']); nt.links.new(mp.outputs['Vector'], v.inputs['Vector']); return v


def add(nt, *terms):  # sum of (socket, weight) pairs
    acc = None
    for s, wgt in terms:
        t = fx(nt, 'MULTIPLY', s, wgt); acc = t if acc is None else fx(nt, 'ADD', acc, t)
    return acc


def make_skin(k):
    """Skin, not a pegboard: the crisscross of fine lines (two scales, a little stretched), pores of two sizes, a slow
    undulation under a low raking lamp (rake()), and the microchannels as sunken pits in loose rows, each jittered,
    sized and lit at random, a few missing, the light at the bottom of the pit. A plane with soft edges, or for the
    protocol a puck of skin with a cut side (epidermis over dermis)."""
    w, h, puck = k['w'], k['h'], k.get('disk')
    m, nt, b = mat('skin', **{'Roughness': 0.6, 'Subsurface Weight': 0.2, 'Subsurface Radius': (1.0, 0.45, 0.25), 'Subsurface Scale': 0.01,
                              'Sheen Weight': 0.1, 'Sheen Tint': (1.0, 0.8, 0.5, 1), 'Sheen Roughness': 0.45,
                              'Emission Color': (1.0, 0.66, 0.28, 1)})
    out = nt.nodes['Material Output']; obc = nt.nodes.new('ShaderNodeTexCoord').outputs['Object']
    so = nt.nodes.new('ShaderNodeSeparateXYZ'); nt.links.new(obc, so.inputs['Vector'])
    nx, ny = fx(nt, 'MULTIPLY', so.outputs['X'], 2 / w), fx(nt, 'MULTIPLY', so.outputs['Y'], 2 / h)   # -1..1 across the plane
    rr = fx(nt, 'SQRT', fx(nt, 'ADD', fx(nt, 'MULTIPLY', nx, nx), fx(nt, 'MULTIPLY', ny, ny)))
    cr = nt.nodes.new('ShaderNodeValToRGB'); nt.links.new(rr, cr.inputs['Fac'])   # warm dark, lighter in the middle
    cr.color_ramp.elements[0].color = (*(c * 0.45 for c in srgb(0x6b4430)), 1); cr.color_ramp.elements[1].color = (*(c * 0.45 for c in srgb(0x2a1a12)), 1)
    if puck: cr.color_ramp.elements[1].color = (*(c * 0.36 for c in srgb(0x6b4430)), 1)   # a small sample: no dark edge (it read as a cookie)
    mot = nt.nodes.new('ShaderNodeValToRGB'); nt.links.new(noise(nt, obc, 2.2, 3), mot.inputs['Fac'])   # slow blotches
    mot.color_ramp.elements[0].position = 0.3; mot.color_ramp.elements[0].color = (0.72, 0.7, 0.68, 1); mot.color_ramp.elements[1].position = 0.7
    col0 = nt.nodes.new('ShaderNodeMixRGB'); col0.blend_type = 'MULTIPLY'; col0.inputs['Fac'].default_value = 1
    nt.links.new(cr.outputs['Color'], col0.inputs['Color1']); nt.links.new(mot.outputs['Color'], col0.inputs['Color2'])
    # fine relief: lines, pores in some cells only, grain
    wv = nt.nodes.new('ShaderNodeVectorMath'); wv.operation = 'MULTIPLY_ADD'; wv.inputs[1].default_value = (0.04, 0.04, 0.04)
    wnz = nt.nodes.new('ShaderNodeTexNoise'); wnz.inputs['Scale'].default_value = 6; nt.links.new(obc, wnz.inputs['Vector'])
    nt.links.new(wnz.outputs['Color'], wv.inputs[0]); nt.links.new(obc, wv.inputs[2]); warp = wv.outputs['Vector']
    # the lines: a crosshatch of shallow grooves in two main directions (rhombuses, as on the back of a hand) and a fainter
    # third, wavering and broken into short dashes; closed random cells (Voronoi edges) read as cracked mud or leather
    def groove(scale, turn, width, mask_scale):
        mp = nt.nodes.new('ShaderNodeMapping'); mp.inputs['Rotation'].default_value = (0, 0, turn); nt.links.new(warp, mp.inputs['Vector'])
        wv = nt.nodes.new('ShaderNodeTexWave'); wv.wave_type = 'BANDS'; wv.bands_direction = 'X'; wv.wave_profile = 'SIN'
        wv.inputs['Scale'].default_value = scale; wv.inputs['Distortion'].default_value = 3.0; wv.inputs['Detail'].default_value = 1.5
        wv.inputs['Detail Scale'].default_value = 1.2; nt.links.new(mp.outputs['Vector'], wv.inputs['Vector'])
        dash = fx(nt, 'MULTIPLY', step(nt, noise(nt, obc, mask_scale), 0.38, 0.62), step(nt, noise(nt, obc, mask_scale * 3.7), 0.3, 0.55))
        return fx(nt, 'MULTIPLY', step(nt, wv.outputs['Fac'], width, 0.0), dash)
    f1 = fx(nt, 'MAXIMUM', groove(22, 0.61, 0.12, 4.2), groove(22, -0.61, 0.12, 5.1))
    f2 = groove(40, 1.57, 0.1, 6.3)
    vp = voronoi(nt, obc, 32); pore = fx(nt, 'MULTIPLY', step(nt, vp.outputs['Distance'], 0.24, 0.0), step(nt, vp.outputs['Color'], 0.45, 0.55))
    pore2 = step(nt, voronoi(nt, obc, 130).outputs['Distance'], 0.25, 0.0)
    # microchannels: loose rows (every other row shifted half a step), each pit jittered, sized and lit at random
    sp = 0.17; X, Y = fx(nt, 'DIVIDE', so.outputs['X'], sp), fx(nt, 'DIVIDE', so.outputs['Y'], sp)
    row = fx(nt, 'FLOOR', Y); xs = fx(nt, 'ADD', X, fx(nt, 'MULTIPLY', fx(nt, 'MODULO', fx(nt, 'ADD', row, 100), 2), 0.5))
    cxyz = nt.nodes.new('ShaderNodeCombineXYZ'); nt.links.new(fx(nt, 'FLOOR', xs), cxyz.inputs['X']); nt.links.new(row, cxyz.inputs['Y'])
    wn = nt.nodes.new('ShaderNodeTexWhiteNoise'); wn.noise_dimensions = '3D'; nt.links.new(cxyz.outputs['Vector'], wn.inputs['Vector'])
    rnd = nt.nodes.new('ShaderNodeSeparateColor'); nt.links.new(wn.outputs['Color'], rnd.inputs['Color'])
    ddx = fx(nt, 'SUBTRACT', fx(nt, 'SUBTRACT', fx(nt, 'FRACT', xs), 0.5), fx(nt, 'MULTIPLY', fx(nt, 'SUBTRACT', rnd.outputs['Red'], 0.5), 0.5))
    ddy = fx(nt, 'SUBTRACT', fx(nt, 'SUBTRACT', fx(nt, 'FRACT', Y), 0.5), fx(nt, 'MULTIPLY', fx(nt, 'SUBTRACT', rnd.outputs['Green'], 0.5), 0.5))
    d = fx(nt, 'DIVIDE', fx(nt, 'SQRT', fx(nt, 'ADD', fx(nt, 'MULTIPLY', ddx, ddx), fx(nt, 'MULTIPLY', ddy, ddy))),
           fx(nt, 'ADD', 0.75, fx(nt, 'MULTIPLY', rnd.outputs['Blue'], 0.5)))
    pass_ = nt.nodes.new('ShaderNodeTexNoise'); pass_.inputs['Scale'].default_value = 0.35; nt.links.new(cxyz.outputs['Vector'], pass_.inputs['Vector'])
    keep = fx(nt, 'MULTIPLY', step(nt, wn.outputs['Value'], 0.08, 0.12), step(nt, pass_.outputs['Fac'], 0.36, 0.42))   # gaps: single pits and short runs
    pit, core = fx(nt, 'MULTIPLY', step(nt, d, 0.06, 0.015), keep), fx(nt, 'MULTIPLY', step(nt, d, 0.035, 0.006), keep)
    halo = fx(nt, 'MULTIPLY', step(nt, d, 0.2, 0.0), keep)
    rim = fx(nt, 'MULTIPLY', step(nt, fx(nt, 'ABSOLUTE', fx(nt, 'SUBTRACT', d, 0.1)), 0.035, 0.0), keep)   # the lip around a pit
    bright = fx(nt, 'ADD', 0.3, fx(nt, 'MULTIPLY', fx(nt, 'FRACT', fx(nt, 'MULTIPLY', wn.outputs['Value'], 7.31)), 0.7))
    glow = fx(nt, 'MULTIPLY', fx(nt, 'ADD', core, fx(nt, 'MULTIPLY', halo, 0.03)), bright)   # a pit lit from inside, not an LED
    if 'wave' in k:   # channels open in a wave across the plane; the front itself flashes
        front = -1.3 + 2.8 * k['wave']
        lit = step(nt, nx, front + 0.05, front - 0.3)
        flash = fx(nt, 'MULTIPLY', step(nt, fx(nt, 'ABSOLUTE', fx(nt, 'SUBTRACT', nx, front)), 0.25, 0.0), 1.5)
        glow = fx(nt, 'MULTIPLY', glow, fx(nt, 'ADD', lit, flash))
    em = fx(nt, 'MULTIPLY', glow, 8.0 * k.get('dots', 0))   # smaller cores: brighter, so the channels still flash
    fine = add(nt, (f1, -0.15), (f2, -0.08), (pore, -0.5), (pore2, -0.25), (noise(nt, obc, 40, 3), 0.3)); pits = add(nt, (pit, -0.9), (rim, 0.2))
    col = nt.nodes.new('ShaderNodeMixRGB'); col.blend_type = 'MULTIPLY'; nt.links.new(col0.outputs['Color'], col.inputs['Color1'])
    nt.links.new(add(nt, (pore, 0.3), (f1, 0.05)), col.inputs['Fac']); col.inputs['Color2'].default_value = (0.55, 0.45, 0.4, 1)
    dk = nt.nodes.new('ShaderNodeMixRGB'); dk.blend_type = 'MULTIPLY'; nt.links.new(col.outputs['Color'], dk.inputs['Color1'])
    dk.inputs['Color2'].default_value = (0.45, 0.4, 0.38, 1); nt.links.new(fx(nt, 'MULTIPLY', rim, 0.6), dk.inputs['Fac'])   # the dark lip of a pit
    col = dk.outputs['Color']
    broad = nt.nodes.new('ShaderNodeBump'); broad.inputs['Distance'].default_value = 0.04; nt.links.new(noise(nt, obc, 1.3, 2), broad.inputs['Height'])
    if k.get('gel'):
        # a thin clear film over the part of the plane left of a wavy line (the owner: a thin wet glossy film with
        # highlights, the relief differs at the edge, before / after): the skin under it keeps its colour and part of
        # its relief, the channels closed; the film's own surface is smooth with a gentle swell, so a soft card gives
        # several soft highlights (a flat film gave one straight stripe and read as tape, a film on the full undulation
        # gave white blobs), and it rises at its edge in a rounded meniscus; outside it the skin stays as it was
        edge = add(nt, (nx, 1.0), (fx(nt, 'SUBTRACT', noise(nt, obc, 2.4, 2), 0.5), 0.55), (fx(nt, 'SUBTRACT', noise(nt, obc, 6), 0.5), 0.12))  # organic
        G, Gs = step(nt, edge, 0.015, -0.015), step(nt, edge, 0.04, -0.04)
        lip = step(nt, fx(nt, 'ABSOLUTE', edge), 0.04, 0.0)
        fine = fx(nt, 'MULTIPLY', fine, fx(nt, 'SUBTRACT', 1.0, fx(nt, 'MULTIPLY', G, 0.65)))   # the relief softened, still there
        pits = fx(nt, 'MULTIPLY', pits, fx(nt, 'SUBTRACT', 1.0, G)); em = fx(nt, 'MULTIPLY', em, fx(nt, 'SUBTRACT', 1.0, G))   # channels closed
        b.inputs['Coat Roughness'].default_value = 0.08; b.inputs['Coat IOR'].default_value = 1.42; nt.links.new(G, b.inputs['Coat Weight'])
        swell = nt.nodes.new('ShaderNodeBump'); swell.inputs['Distance'].default_value = 0.015   # the film follows the skin's slow waves
        nt.links.new(noise(nt, obc, 1.3, 2), swell.inputs['Height'])
        cb = nt.nodes.new('ShaderNodeBump'); cb.inputs['Distance'].default_value = 0.01
        nt.links.new(add(nt, (Gs, 1.0), (lip, 0.6)), cb.inputs['Height']); nt.links.new(swell.outputs['Normal'], cb.inputs['Normal'])
        nt.links.new(cb.outputs['Normal'], b.inputs['Coat Normal'])
        wet = nt.nodes.new('ShaderNodeMixRGB'); wet.blend_type = 'MULTIPLY'; nt.links.new(col, wet.inputs['Color1'])   # the same skin, ~10% deeper
        wet.inputs['Color2'].default_value = (0.9, 0.88, 0.86, 1); nt.links.new(G, wet.inputs['Fac']); col = wet.outputs['Color']
        nt.links.new(fx(nt, 'ADD', 0.2, fx(nt, 'MULTIPLY', G, 0.3)), b.inputs['Subsurface Weight'])
    nt.links.new(col, b.inputs['Base Color']); nt.links.new(em, b.inputs['Emission Strength'])
    bp = nt.nodes.new('ShaderNodeBump'); bp.inputs['Distance'].default_value = 0.004
    nt.links.new(fx(nt, 'ADD', fine, pits), bp.inputs['Height']); nt.links.new(broad.outputs['Normal'], bp.inputs['Normal']); nt.links.new(bp.outputs['Normal'], b.inputs['Normal'])
    # a plane melts into the smoke at its soft edges (rounded rectangle); a puck is a solid object
    alpha = 1.0 if puck else fx(nt, 'MULTIPLY', step(nt, fx(nt, 'ABSOLUTE', nx), 1.0, 0.6), step(nt, fx(nt, 'ABSOLUTE', ny), 1.0, 0.6))
    alpha = fx(nt, 'MULTIPLY', alpha, k.get('alpha', 1.0))   # fade-in during a transition
    mix = nt.nodes.new('ShaderNodeMixShader'); tr = nt.nodes.new('ShaderNodeBsdfTransparent')
    nt.links.new(alpha, mix.inputs['Fac']); nt.links.new(tr.outputs[0], mix.inputs[1]); nt.links.new(b.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs['Surface'])
    bm = bmesh.new()
    if puck:
        t = 0.08; bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=128, radius1=w / 2, radius2=w / 2, depth=t)
        for v in bm.verts: v.co.z -= t / 2
        bm.normal_update()
        for f in bm.faces: f.material_index = 0 if f.normal.z > 0.9 else 1
        side, snt, sb = mat('skin-side', **{'Roughness': 0.5, 'Subsurface Weight': 0.3, 'Subsurface Radius': (1.0, 0.4, 0.2), 'Subsurface Scale': 0.01})
        sz = snt.nodes.new('ShaderNodeSeparateXYZ'); snt.links.new(snt.nodes.new('ShaderNodeTexCoord').outputs['Object'], sz.inputs['Vector'])
        # the cut: a thin dark epidermis line on top, a lighter warm pink-beige dermis below, a slightly wavy boundary
        lay = snt.nodes.new('ShaderNodeMixRGB'); lay.inputs['Color1'].default_value = (0.04, 0.017, 0.009, 1); lay.inputs['Color2'].default_value = (0.16, 0.07, 0.05, 1)
        zw = add(snt, (sz.outputs['Z'], 1.0), (fx(snt, 'SUBTRACT', noise(snt, snt.nodes['Texture Coordinate'].outputs['Object'], 8), 0.5), 0.01))
        snt.links.new(step(snt, zw, -0.008, -0.014), lay.inputs['Fac']); snt.links.new(lay.outputs['Color'], sb.inputs['Base Color'])
        ob = obj('skin', to_mesh(bm, 'skin', sharp=35), (m, side), p=k['p'], r=k['r']); bevel(ob, 0.006, 3)
        return ob
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=0.5)
    for v in bm.verts: v.co = Vector((v.co.x * w, v.co.y * h, 0))
    return obj('skin', to_mesh(bm, 'skin', sharp=0), (m,), p=k['p'], r=k['r'])

# ---------- serum drop: a clear tear with pearl spheres inside (the scheme of synthetic exosomes) ----------
def tear_mesh():  # the classic teardrop (r = sin t·sin(t/2)^1.5): round belly, concave flanks into a sharp tip; the old
    # profile had straight flanks and read as a guitar pick. Height 2.6, widest radius 0.91, belly centre at y -0.55
    prof = [(0 if i in (0, 48) else 1.3 * math.sin(math.pi * i / 48) * math.sin(math.pi * i / 96) ** 1.5, 1.3 * math.cos(math.pi * i / 48)) for i in range(49)]
    return lathe(prof[::-1], 96, 'tear', sharp=0)


TEAR = tear_mesh()
bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=32, v_segments=16, radius=1.0); SPHERE = to_mesh(bm, 'sphere', sharp=0)
# the drop is a clear shell: mirror at the rim (Fresnel), see-through in the middle, so the pearls inside get the light
# (a refractive drop with caustics off left them black and read as chrome)
drop_mat, nt, _ = mat('drop')
fr, gl, tr, mx = (nt.nodes.new(t) for t in ('ShaderNodeFresnel', 'ShaderNodeBsdfGlossy', 'ShaderNodeBsdfTransparent', 'ShaderNodeMixShader'))
fr.inputs['IOR'].default_value = 1.33; gl.inputs['Roughness'].default_value = 0.0
rim, ad = nt.nodes.new('ShaderNodeEmission'), nt.nodes.new('ShaderNodeAddShader')   # the rim glows softly: clear water on the
rim.inputs['Color'].default_value = (1.0, 0.88, 0.716, 1); rim.inputs['Strength'].default_value = 0.1   # dark, not a black outline (more read as grey plastic)
nt.links.new(gl.outputs[0], ad.inputs[0]); nt.links.new(rim.outputs[0], ad.inputs[1])
nt.links.new(fr.outputs[0], mx.inputs['Fac']); nt.links.new(tr.outputs[0], mx.inputs[1]); nt.links.new(ad.outputs[0], mx.inputs[2])
nt.links.new(mx.outputs[0], nt.nodes['Material Output'].inputs['Surface'])
pearl_mat = mat('pearl', **{'Base Color': (0.43, 0.41, 0.44, 1), 'Roughness': 0.12, 'Coat Weight': 1.0, 'Coat Roughness': 0.03, 'Sheen Weight': 0.3, 'Subsurface Weight': 0.3, 'Subsurface Scale': 0.003,
                            'Thin Film Thickness': 380.0, 'Thin Film IOR': 1.5})[0]  # white pearls with an iridescent film


def make_drop(at, size=0.1):
    g = obj('drop', p=at)
    obj('tear', TEAR, (drop_mat,), g, s=size)
    seed = 3
    def rnd():
        nonlocal seed; seed = seed * 16807 % 2147483647; return seed / 2147483647
    for i in range(14):   # suspended through the whole belly (a golden spiral in a ball), mixed sizes, not settled on a floor
        yy = 1 - 2 * (i + 0.5) / 14; rr = math.sqrt(1 - yy * yy) * 0.55 * (0.6 + 0.4 * rnd()); a = i * 2.39996
        obj('pearl', SPHERE, (pearl_mat,), g, p=(math.cos(a) * rr * size, (-0.5 + 0.55 * yy) * size, math.sin(a) * rr * size), s=(0.06 + rnd() * 0.06) * size)
    for o in g.children: o.visible_glossy = False   # no chrome ghost of the drop in the foil
    return tag(g, 'drops')


def make_line(c, L):  # the protocol's gold line, parallel to the screen (along the camera's x axis), centre c, length L
    m, nt, _ = mat('line'); em = nt.nodes.new('ShaderNodeEmission')
    em.inputs['Color'].default_value = (*srgb(0xc9a24b), 1); em.inputs['Strength'].default_value = 3.0
    nt.links.new(em.outputs[0], nt.nodes['Material Output'].inputs['Surface'])
    ob = obj('line', lathe([(0, -L / 2), (0.006, -L / 2), (0.006, L / 2), (0, L / 2)], 16, 'line'), (m,), p=c)
    ob.rotation_mode = 'QUATERNION'; ob.rotation_quaternion = (look_matrix(S['cam'], S['look']).to_3x3() @ Vector((1, 0, 0))).to_track_quat('Y', 'Z')
    return tag(ob, 'skin')

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


def rake(k, skin):
    """A low lamp grazing the skin from the right and behind (11° over the surface), linked to the skin alone: it draws
    the lines, pores and pits without lighting anything else."""
    M = Euler(k['r'], 'ZYX').to_matrix(); n, ux, uy = (M @ Vector(a) for a in ((0, 0, 1), (1, 0, 0), (0, 1, 0)))
    e = math.radians(11); L = (math.cos(e) * (0.8 * ux + 0.6 * uy).normalized() + math.sin(e) * n).normalized()
    li = area('rake', srgb(0xffc78c), 180, tuple(Vector(k['p']) + L * (k['w'] + 5.0)), k['p'], 1.2)   # far: even across the plane
    li.visible_glossy = True; only_on(li, skin)


def gel_card(k, skin):
    """Wet glints on the film: a soft round spot on the mirror ray of the gel half, seen only in reflections and only
    by the skin (a large card gave a white sheet, a rectangle a white sticker) (a card the dry skin or the foil could see would put a milky haze on them)."""
    p = tuple(Vector(k['p']) + Euler(k['r'], 'ZYX').to_matrix() @ Vector((-0.25 * k['w'], 0, 0)))
    card = card_at(srgb(0xfff3e0), 2.5, p, k['r'], 3.5, 1.1, 0.6, 0.85, True); card.visible_diffuse = False; only_on(card, skin)


def drop_glint(d, drop):  # a small hot window up and to the left, for the drop alone: one crisp highlight on the
    # water and a specular dot on each pearl (lit only by the room they read as foam balls)
    p = Vector(d['p']); c = p + Vector((-1.6, 1.8, 2.2)).normalized() * 2.4
    card = panel(srgb(0xffffff), 60.0, *c, 1.4, 0.9, 0, soft=0.3, round_=True); card.matrix_basis = look_matrix(tuple(c), tuple(p))  # specular is ~4%: hot
    card.visible_diffuse = False; only_on(card, *drop.children)


def fill_card(a, pouch):  # a sachet alone on a screen: a card on its mirror ray keeps the print on light, and a low warm
    # card under it lights the lower bulge (it mirrored the black void: a dark band under GEL MASK), both for the sachet alone
    meshes = [o for o in pouch.children_recursive if o.type == 'MESH']
    only_on(card_at(srgb(0xfff3e0), 2.5, a[:3], a[3:6], 3.0, 1.8, 1.2, 0.4), *meshes)
    c = Vector(a[:3]) + Vector((0, -2.2, 1.3)); low = panel(srgb(0xf3dcb0), 1.8, *c, 2.4, 1.0, 0, soft=0.45)
    low.matrix_basis = look_matrix(tuple(c), tuple(a[:3])); only_on(low, *meshes)


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
def backlight(x, y, z, w, h, ry=0.0, k=1.4):  # seen only through the glass (as in packshot photography): the serum glows orange
    bl = panel(srgb(0xffe2a6), k, x, y, z, w, h, ry); bl.visible_glossy = False; bl.visible_diffuse = False


if 'box' in S: tag(make_box(S['box']['p'], S['box']['r'], S['box']['s']), 'box')
if 'tray' in S:
    tray = make_tray(S['tray'])
    backlight(S['tray']['p'][0] + 0.1, S['tray']['p'][1] + 0.4, S['tray']['p'][2] - 0.9, 1.9, 0.9, -0.36, 2.2)   # shoulders glow as the lifted vial's
for a in S.get('vials', []):
    tag(make_vial(a), 'vials'); backlight(a[0], a[1] + 0.25, a[2] - 0.7, 0.6, 0.5)
if 'skin' in S:
    sk = tag(make_skin(S['skin']), 'skin'); rake(S['skin'], sk)
    if S['skin'].get('gel'): gel_card(S['skin'], sk)
if S.get('drop'): drop_glint(S['drop'], make_drop(S['drop']['p'], S['drop']['s']))
if 'line' in S: make_line(S['line']['c'], S['line']['L'])
for a in S.get('pouches', []):
    pc = tag(make_pouch(a), 'pouches')
    if 'tray' not in S:   # a sachet alone: its own fill card, and not mirrored in the far carton (a dark T on the foil)
        fill_card(a, pc)
        for o in pc.children_recursive: o.visible_glossy = False
if 'tray' in S and S.get('pouches'):  # kit: a low wide card under the camera, so the sachet fan mirrors light, not the dark void
    # (not where gel is on the skin: its wet coat would mirror the card as a milky haze)
    panel(srgb(0xfff3e0), 1.6, -1.8, -3.0, 4.6, 6.4, 2.4, math.pi, rx=-0.5, soft=0.35)
if PART:  # one Figma layer: the other parts stay in the scene for shadows and reflections but the camera does not see them
    for o in scn.objects:
        if o.get('part') and o['part'] != PART: o.visible_camera = False
cam = obj('camera', bpy.data.cameras.new('camera')); cam.data.sensor_fit = 'VERTICAL'
cam.data.lens = cam.data.sensor_height / (2 * math.tan(math.radians(S.get('fov', 35)) / 2)); cam.matrix_basis = look_matrix(S['cam'], S['look'])
cam.data.clip_start = 0.1; cam.data.clip_end = 80; scn.camera = cam
if S.get('fstop'):   # a shallow focus puts the far carton behind the subject (S2 skin, S4 sachet and gel)
    cam.data.dof.use_dof = True; cam.data.dof.aperture_fstop = S['fstop']; cam.data.dof.focus_distance = (Vector(S['focus']) - Vector(S['cam'])).length

r, c = scn.render, scn.cycles
r.engine = 'CYCLES'; c.device = 'CPU'; c.samples = SAMPLES; c.use_adaptive_sampling = True; c.adaptive_threshold = 0.006
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
r.image_settings.file_format = 'PNG'; r.image_settings.color_mode = 'RGBA'; r.image_settings.color_depth = '16'
r.filepath = OUT
bpy.ops.render.render(write_still=True)

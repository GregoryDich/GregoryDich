"""V-TECH SYSTEM path-traced in Blender Cycles (PLAN §8, stage 1: the HD sample).
Same shots and poses as ../render-vtech.html. Everything is built in three.js coordinates (Y up) under a root empty
turned 90° about X; Blender Euler 'ZYX' equals three.js 'XYZ'. Print maps come from prep_tex.py (albedo/metal/rough).
usage: <python with bpy 4.2> vtech_scene.py <tex dir> <out.png> <v1-meet|v6-kit|kit-hd> [width=2880] [samples=256]
The frame is rendered on a transparent film; compose.py lays it over layers/vt-bg-wide.jpg."""
import bpy, bmesh, math, sys
from mathutils import Matrix, Vector

TEX, OUT, SHOT = sys.argv[1:4]
WIDTH = int(sys.argv[4]) if len(sys.argv) > 4 else 2880
SAMPLES = int(sys.argv[5]) if len(sys.argv) > 5 else 256

# kit: the insert at 0.62 so a vial body is ~0.2 of the carton width, as in the packshot; the sachets fan out to the right
# as in the storyboard, about the carton's width, clear of the last vial; the carton leans back a little so it does not
# mirror the vials
POUCHES = [[3.42 + i * 0.1, -0.37 - i * 0.05, -0.85 + i * 0.2, 0.12, -0.62, -0.2 + i * 0.09, 0.88] for i in range(5)]
KIT = dict(box=dict(p=(2.25, 0.55, -1.8), r=(-0.03, -0.32, 0.01), s=0.95), tray=dict(p=(2.3, -0.82, -0.45), r=(0.36, -0.36, 0), s=0.62), pouches=POUCHES)
SHOTS = {
    'v1-meet': dict(aspect=1.6, cam=(0, 0, 7), look=(0.9, 0, 0), box=dict(p=(1.8, -0.05, 0.2), r=(0.06, -0.48, 0.0), s=1)),
    'v6-kit': dict(aspect=1.6, cam=(0.4, 0.1, 6.0), look=(1.6, -0.15, 0), **KIT),  # closer than S1: the kit is smaller now, true to scale
    'kit-hd': dict(aspect=1400 / 1100, cam=(2.35, 0.35, 6.0), look=(2.35, -0.25, 0), **KIT),
}
S = SHOTS[SHOT]

bpy.ops.wm.read_factory_settings(use_empty=True)
scn = bpy.context.scene
root = bpy.data.objects.new('root', None); scn.collection.objects.link(root); root.rotation_euler = (math.pi / 2, 0, 0)


def obj(name, data=None, mats=(), parent=root, p=(0, 0, 0), r=(0, 0, 0), s=1):
    ob = bpy.data.objects.new(name, data); scn.collection.objects.link(ob)
    for m in mats: ob.data.materials.append(m)
    ob.parent = parent; ob.location = p; ob.rotation_mode = 'ZYX'; ob.rotation_euler = r; ob.scale = (s, s, s)
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


def printed(name, key, layers):
    """Foil with the real print: metal from the mask; the ink is a rough black dielectric that stays black in any reflection."""
    m, nt, b = mat(name)
    nt.links.new(image(nt, f'{key}-albedo.png').outputs['Color'], b.inputs['Base Color'])
    metal = image(nt, f'{key}-metal.png', True); nt.links.new(metal.outputs['Color'], b.inputs['Metallic'])
    sp = nt.nodes.new('ShaderNodeMapRange'); sp.inputs['To Min'].default_value = 0.25; sp.inputs['To Max'].default_value = 0.5
    nt.links.new(metal.outputs['Color'], sp.inputs['Value']); nt.links.new(sp.outputs['Result'], b.inputs['Specular IOR Level'])
    nt.links.new(image(nt, f'{key}-rough.png', True).outputs['Color'], b.inputs['Roughness'])
    relief(nt, b, layers)
    return m


GOLD = (0.87, 0.60, 0.21, 1)  # linear of the packshot foil (sRGB 0.94, 0.80, 0.50)
# carton: a few broad vertical bows in the sleeve (crisp light/dark bands in the mirror) + a faint fine crinkle
FOIL = (((1.0, 0.15, 1.0), 1.3, 0.0, 0.035),)  # broad bows only: any fine layer read as hammered metal
box_front = printed('box-front', 'box-front', FOIL)
box_side = printed('box-side', 'box-side', FOIL)
box_back, nt, b = mat('box-back', **{'Base Color': GOLD, 'Metallic': 1.0, 'Roughness': 0.06}); relief(nt, b, FOIL)
box_end = mat('box-end', **{'Base Color': (0.015, 0.015, 0.016, 1), 'Roughness': 0.3, 'Specular IOR Level': 0.5})[0]
# sachet: glossy foil with two or three soft dents and a fine crinkle, no stretched streaks
SACHET = (((1.4, 1.4, 1.4), 1.8, 0.0, 0.02), ((1, 1, 1), 26.0, 0.0, 0.0002))
sachet_front = printed('sachet-front', 'sachet', SACHET)
sachet_back, nt, b = mat('sachet-back', **{'Base Color': GOLD, 'Metallic': 1.0, 'Roughness': 0.12}); relief(nt, b, SACHET)
white = mat('white-plastic', **{'Base Color': (0.85, 0.85, 0.83, 1), 'Roughness': 0.35, 'Coat Weight': 0.3})[0]
alu = mat('aluminium', **{'Base Color': (0.92, 0.92, 0.92, 1), 'Metallic': 1.0, 'Roughness': 0.3})[0]
# amber glass up to the cap, as on the real vials; the serum deepens the orange of the body
glass = mat('amber-glass', **{'Base Color': (1.0, 0.52, 0.2, 1), 'Transmission Weight': 1.0, 'Roughness': 0.015, 'IOR': 1.5})[0]
serum, nt, b = mat('serum', **{'Base Color': (1, 1, 1, 1), 'Transmission Weight': 1.0, 'Roughness': 0.0, 'IOR': 1.34})
va = nt.nodes.new('ShaderNodeVolumeAbsorption'); va.inputs['Color'].default_value = (0.95, 0.42, 0.06, 1); va.inputs['Density'].default_value = 10
nt.links.new(va.outputs[0], nt.nodes['Material Output'].inputs['Volume'])
label, nt, b = mat('label', **{'Base Color': (0.86, 0.86, 0.84, 1), 'Roughness': 0.45})
mix, tr, lab = nt.nodes.new('ShaderNodeMixShader'), nt.nodes.new('ShaderNodeBsdfTransparent'), image(nt, 'label.png')
nt.links.new(lab.outputs['Alpha'], mix.inputs['Fac']); nt.links.new(tr.outputs[0], mix.inputs[1]); nt.links.new(b.outputs[0], mix.inputs[2])
nt.links.new(mix.outputs[0], nt.nodes['Material Output'].inputs['Surface'])
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
for j, y in enumerate((0.06, 0.40)):  # open sleeve, u = 0 at the back; the print block (u = 0.5) faces the vial's +z
    ring.append([bm.verts.new((0.1615 * math.sin(math.pi + 2 * math.pi * k / N), y, 0.1615 * math.cos(math.pi + 2 * math.pi * k / N))) for k in range(N + 1)])
for k in range(N):
    f = bm.faces.new((ring[0][k], ring[0][k + 1], ring[1][k + 1], ring[1][k]))
    for loop, t in zip(f.loops, ((k / N, 0), ((k + 1) / N, 0), ((k + 1) / N, 1), (k / N, 1))): loop[uvl].uv = t
bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
vial_meshes['label'] = to_mesh(bm, 'label', sharp=0)


def make_vial(a, parent=root):
    g = obj('vial', parent=parent, p=a[:3], r=a[3:6], s=a[6])
    obj('glass', vial_meshes['glass'], (glass,), g); obj('serum', vial_meshes['serum'], (serum,), g)
    obj('label', vial_meshes['label'], (label,), g)
    bevel(obj('crimp', vial_meshes['crimp'], (alu,), g), 0.006, 3); bevel(obj('top', vial_meshes['top'], (white,), g), 0.003, 2)
    return g

# ---------- gel-mask sachet: gold foil pillow with the real print, flat sealed rim, white nozzle on the left ----------
def pillow_mesh(w=1.0, h=0.58, depth=0.011, nx=120, ny=70):  # a flat sachet, only a slight puff in the middle
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
    obj('spout', SPOUT, (white,), g, p=(-0.54, 0, 0), r=(0, 0, math.pi / 2))
    bevel(obj('cap', CAP, (white,), g, p=(-0.62, 0, 0), r=(0, 0, math.pi / 2)), 0.008, 2)
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
    for i, jit in enumerate((0.05, -0.04, 0.02, -0.06, 0.04)):  # turned towards the camera, a little unevenly
        make_vial((-0.78 + i * 0.39, H / 2 - 0.02, -0.2, 0, 0.09 + jit, 0, 0.9), g)
    return g

# ---------- light: dark room, white softbox left, warm gold right, gold strip above, warm fills in front ----------
def panel(color, strength, x, y, z, w, h, ry, rx=0, soft=0.3):
    """Softbox card seen only in reflections: even light, the outer `soft` part of each half-side fades out."""
    m, nt, _ = mat('panel')
    em = nt.nodes.new('ShaderNodeEmission'); em.inputs['Color'].default_value = (*color, 1)
    tc, mp, sep, mt = (nt.nodes.new(t) for t in ('ShaderNodeTexCoord', 'ShaderNodeMapping', 'ShaderNodeSeparateXYZ', 'ShaderNodeMath'))
    mp.inputs['Scale'].default_value = (2 / w, 2 / h, 1); mt.operation = 'MULTIPLY'
    nt.links.new(tc.outputs['Object'], mp.inputs['Vector']); nt.links.new(mp.outputs['Vector'], sep.inputs['Vector'])
    edges = []
    for axis in ('X', 'Y'):
        ab, fr = nt.nodes.new('ShaderNodeMath'), nt.nodes.new('ShaderNodeMapRange'); ab.operation = 'ABSOLUTE'
        fr.inputs['From Min'].default_value = 1 - soft; fr.inputs['From Max'].default_value = 1.0
        fr.inputs['To Min'].default_value = 1.0; fr.inputs['To Max'].default_value = 0.0; fr.interpolation_type = 'SMOOTHSTEP'
        nt.links.new(sep.outputs[axis], ab.inputs[0]); nt.links.new(ab.outputs[0], fr.inputs['Value']); edges.append(fr)
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


# near-white cards (the foil itself gives the gold), with a dark gap in front so the mirror shows bands, as in the packshot
panel(srgb(0xffffff), 3.0, -4.5, 1.6, 1, 3, 3, math.pi / 2)
panel(srgb(0xf3dcb0), 2.0, 4.8, 0.4, -0.5, 3, 4, -math.pi / 2)
panel(srgb(0xe8d6a8), 1.5, 0, 3.8, -2, 7, 1.2, 0, math.pi / 2)
# the carton front mirrors x -3.6..-1.7 of this wall in S1 and x -2.4..-0.5 in the kit: light bars with narrow dark gaps,
# so the foil shows bands as in the packshot while the print stays on light; tall enough for the print low on the carton
for x, w, k in ((-3.45, 1.9, 1.5), (-1.85, 0.8, 1.6), (-0.9, 0.5, 1.6), (0.3, 1.0, 1.8)):
    panel(srgb(0xfff3e0), k, x, 0.0, 5.6, w, 6.6, math.pi, soft=0.15)
for x in (-3.0, -1.75):  # two narrow hot strips in front of the cards: the clipped white streaks of the real foil
    panel(srgb(0xffffff), 9.0, x, 0.0, 5.5, 0.16, 6.6, math.pi, soft=0.4)
panel(srgb(0xf3dcb0), 1.8, 5.0, 0.5, -3.8, 2, 5, -0.675)  # back-right strip: a gold edge on the carton's right side
area('key', (1, 1, 1), 800, (4.5, 4.5, 4.5), (2.0, 0, 0), 2.5)  # upper right, where the smoke is brightest
area('fill', srgb(0xfff3e0), 320, (-3, 2, 5), (1.5, 0, 0), 3.0)
area('rim', srgb(0xf3dcb0), 400, (4.6, 1.6, 1.0), (2.0, 0, -0.5), 1.2)
world = bpy.data.worlds.new('room'); scn.world = world; world.use_nodes = True
world.node_tree.nodes['Background'].inputs['Color'].default_value = (0.006, 0.005, 0.004, 1)

# ---------- shot ----------
if 'box' in S: make_box(S['box']['p'], S['box']['r'], S['box']['s'])
if 'tray' in S:
    make_tray(S['tray'])
    # backlight seen only through the glass (as in packshot photography), so the serum glows orange instead of going dark
    bl = panel(srgb(0xffe2a6), 1.0, 2.3, -0.5, -1.3, 1.9, 0.6, -0.36)
    bl.visible_glossy = False; bl.visible_diffuse = False
for a in S.get('pouches', []): make_pouch(a)
cam = obj('camera', bpy.data.cameras.new('camera')); cam.data.sensor_fit = 'VERTICAL'
cam.data.lens = cam.data.sensor_height / (2 * math.tan(math.radians(35) / 2)); cam.matrix_basis = look_matrix(S['cam'], S['look'])
cam.data.clip_start = 0.1; cam.data.clip_end = 80; scn.camera = cam

r, c = scn.render, scn.cycles
r.engine = 'CYCLES'; c.device = 'CPU'; c.samples = SAMPLES; c.use_adaptive_sampling = True; c.adaptive_threshold = 0.006
c.use_denoising = True; c.denoiser = 'OPENIMAGEDENOISE'
c.max_bounces = 16; c.diffuse_bounces = 3; c.glossy_bounces = 8; c.transmission_bounces = 16; c.transparent_max_bounces = 16
c.caustics_reflective = False; c.caustics_refractive = False; c.blur_glossy = 0.5; c.sample_clamp_indirect = 5  # no blotches in the glass
r.film_transparent = True; c.film_transparent_glass = True
r.resolution_x = WIDTH; r.resolution_y = round(WIDTH / S['aspect']); r.resolution_percentage = 100
scn.view_settings.view_transform = 'Filmic'; scn.view_settings.look = 'Medium High Contrast'  # Filmic keeps the foil yellow; AgX turns it peach
r.image_settings.file_format = 'PNG'; r.image_settings.color_mode = 'RGBA'; r.image_settings.color_depth = '16'
r.filepath = OUT
bpy.ops.render.render(write_still=True)

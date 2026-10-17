"""PDRN for the V-TECH page (owner 17/10, his pictures of gold polynucleotides and a Firefly DNA clip): one glassy amber-gold
object on a transparent film, for the page's floating layer (with the exosome cells) and the S3 background.
  molecule: a ring of five beads with a sixth on a branch, joined by tapered bonds, like the owner's pictures
  helix:    a DNA double helix, two gold strands and the base-pair rungs between them, lying on a diagonal
usage: <python with bpy> molecules_scene.py <out.png> <molecule|helix> [size=1024] [samples=128] [seed=1] [turn=0]
(turn: the helix's spin about its own axis in turns, for a loop of frames)"""
import bpy, bmesh, math, random, sys
from mathutils import Vector, Matrix

ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:]
OUT, WHAT = ARGS[0], ARGS[1]
SIZE = int(ARGS[2]) if len(ARGS) > 2 else 1024
SPP = int(ARGS[3]) if len(ARGS) > 3 else 128
SEED = int(ARGS[4]) if len(ARGS) > 4 else 1
TURN = float(ARGS[5]) if len(ARGS) > 5 else 0.0
random.seed(SEED)

bpy.ops.wm.read_factory_settings(use_empty=True)
scn = bpy.context.scene
r = scn.render; r.engine = 'CYCLES'; scn.cycles.samples = SPP; scn.cycles.use_denoising = True
r.film_transparent = True; scn.cycles.film_transparent_glass = True
r.resolution_x = r.resolution_y = SIZE
scn.view_settings.view_transform = 'Filmic'; scn.view_settings.look = 'Medium High Contrast'
r.image_settings.file_format = 'PNG'; r.image_settings.color_mode = 'RGBA'; r.filepath = OUT


def mat(name, **kw):
    m = bpy.data.materials.new(name); m.use_nodes = True; b = m.node_tree.nodes['Principled BSDF']
    for k, v in kw.items(): b.inputs[k].default_value = v
    return m


# amber-gold glass, as in the owner's picture: warm, see-through, crisp highlights; the bonds a touch denser
# glass alone refracts the dark room and goes black: amber resin instead, lit from within (subsurface) under a clear coat
AMBER = mat('amber', **{'Base Color': (0.85, 0.40, 0.07, 1), 'Subsurface Weight': 1.0, 'Subsurface Radius': (1.0, 0.45, 0.1),
                         'Subsurface Scale': 0.8, 'Transmission Weight': 0.55, 'Roughness': 0.04, 'IOR': 1.45, 'Coat Weight': 0.8, 'Coat Roughness': 0.02})
BOND = mat('bond', **{'Base Color': (0.8, 0.38, 0.07, 1), 'Subsurface Weight': 1.0, 'Subsurface Radius': (1.0, 0.45, 0.1),
                      'Subsurface Scale': 0.5, 'Transmission Weight': 0.5, 'Roughness': 0.05, 'Coat Weight': 0.7})
GOLD = mat('gold', **{'Base Color': (0.92, 0.66, 0.28, 1), 'Metallic': 1.0, 'Roughness': 0.12})
RUNG = mat('rung', **{'Base Color': (0.95, 0.7, 0.35, 1), 'Emission Color': (1.0, 0.65, 0.25, 1), 'Emission Strength': 0.35, 'Roughness': 0.25})


ROOT = bpy.data.objects.new('root', None); scn.collection.objects.link(ROOT)   # everything hangs on it; it takes the tilt


def obj(name, me, m):
    o = bpy.data.objects.new(name, me); scn.collection.objects.link(o); me.materials.append(m); o.parent = ROOT
    for p in me.polygons: p.use_smooth = True
    return o


def sphere(c, rad, m):
    bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=64, v_segments=32, radius=rad)
    me = bpy.data.meshes.new('s'); bm.to_mesh(me); bm.free(); o = obj('bead', me, m); o.location = c; return o


def tube(a, b, ra, rb, m, seg=32):   # a tapered bond from a to b (radius ra at a, rb at b)
    a, b = Vector(a), Vector(b); d = b - a
    bm = bmesh.new(); bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=ra, radius2=rb, depth=d.length)
    me = bpy.data.meshes.new('t'); bm.to_mesh(me); bm.free(); o = obj('bond', me, m)
    o.location = (a + b) / 2; o.rotation_mode = 'QUATERNION'; o.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(d)
    return o


if WHAT == 'molecule':   # five beads on a slightly irregular ring, a sixth on a branch, a gentle tilt in depth
    ring = []
    for k in range(5):
        a = math.pi / 2 + 2 * math.pi * k / 5 + random.uniform(-0.12, 0.12)
        ring.append((Vector((math.cos(a) * 1.15, math.sin(a) * 1.15, random.uniform(-0.25, 0.25))), random.uniform(0.34, 0.46)))
    tip = ring[0][0] + Vector((0.95, 0.75, 0.1)); beads = ring + [(tip, 0.45)]
    for c, rad in beads: sphere(c, rad, AMBER)
    for (c1, r1), (c2, r2) in [(ring[k], ring[(k + 1) % 5]) for k in range(5)] + [(ring[0], (tip, 0.45))]:
        d = (c2 - c1).normalized(); tube(c1 + d * r1 * 0.8, c2 - d * r2 * 0.8, 0.13, 0.13, BOND)
    ROOT.matrix_world = Matrix.Rotation(random.uniform(-0.5, 0.5), 4, 'X') @ Matrix.Rotation(random.uniform(-0.6, 0.6), 4, 'Y')
    cam_d, ortho = 7.0, 4.6
else:   # helix: 2.5 turns along x, two strands of beads 180° apart, rungs between, spun by TURN
    N, L, R = 64, 7.0, 0.9
    for k in range(N):
        t = k / (N - 1); x = (t - 0.5) * L; a = 2 * math.pi * (2.5 * t + TURN)
        p1, p2 = Vector((x, R * math.cos(a), R * math.sin(a))), Vector((x, -R * math.cos(a), -R * math.sin(a)))
        sphere(p1, 0.17, GOLD); sphere(p2, 0.17, GOLD)
        if k % 3 == 0: tube(p1, p2, 0.045, 0.045, RUNG)
        if k: tube(prev1, p1, 0.09, 0.09, GOLD); tube(prev2, p2, 0.09, 0.09, GOLD)
        prev1, prev2 = p1, p2
    ROOT.matrix_world = Matrix.Rotation(math.radians(28), 4, 'Z')   # the diagonal of the owner's clip
    cam_d, ortho = 9.0, 8.4

cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); scn.collection.objects.link(cam); scn.camera = cam
cam.data.type = 'ORTHO'; cam.data.ortho_scale = ortho; cam.location = (0, 0, cam_d)


def area(name, power, pos, size, color=(1, 1, 1)):
    li = bpy.data.lights.new(name, 'AREA'); li.energy = power; li.size = size; li.color = color; li.shape = 'DISK'   # round highlights
    o = bpy.data.objects.new(name, li); scn.collection.objects.link(o); o.location = pos
    o.rotation_euler = (Vector((0, 0, 0)) - Vector(pos)).to_track_quat('-Z', 'Y').to_euler()


area('key', 900, (-4, 5, 6), 3)                       # soft key upper left: the round highlight on each bead
area('rim', 700, (5, -2, -3), 2, (1.0, 0.8, 0.55))    # warm rim from behind right: the glow through the glass
area('fill', 150, (3, 3, 6), 4, (1.0, 0.9, 0.8))
world = bpy.data.worlds.new('w'); scn.world = world; world.use_nodes = True
world.node_tree.nodes['Background'].inputs['Color'].default_value = (0.05, 0.03, 0.012, 1)   # what the glass refracts: warm dark
bpy.ops.render.render(write_still=True)
print('rendered', OUT)

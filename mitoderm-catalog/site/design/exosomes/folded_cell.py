"""Folded exosome (owner 22/10, ref-folded-2210.webp): a matte cream-gold sphere covered in soft, rounded lobes that
wind like a brain's, with narrow grooves between them; the rims glow warm, the grooves fall to honey-brown. A second
kind of cell next to the glassy ones of 17/10 (vtech-3d/src/hd/cells_scene.py); one cell per render, path-traced in
Cycles on a transparent film, so it can be laid over the plate as a sprite or used as a texture in a three.js scene.

The lobes are a Turing pattern: Gray-Scott reaction-diffusion run on the vertices of a dense icosphere (graph
Laplacian) settles into a labyrinth of even, winding stripes with rounded ends. A groove runs along the middle of each
stripe of the second substance, only in its core (w / w_max > core), so the lobes are wide and the grooves thin:
height = clamp((1 − w) / (1 − core))^round · (1 − dome + dome·(1 − w)^0.7), a cushion that drops steeply into the
groove and is rounded on top (a flat plateau with a soft trough, tried before, read as tiles). Plain noise (tried first) gave lobes of every size
and creases where two noises meet, which read as crumpled foil, not as the reference's soft wax.

  render (Python with bpy 4.2, numpy, scipy):  folded_cell.py <out.png> <seed> [size=1024] [samples=128] [key=value …]
keys (each one drawn from the seed when not given): feed, kill (Gray-Scott: 0.037/0.060 a labyrinth, a higher kill
breaks it into shorter lobes), scale (stripe width; 3 gives ~13 lobes across), vary (how much it drifts), round (the cushion: lower is
steeper at the groove and fuller on top), core (groove width: higher is thinner), dome (how round a lobe's top), depth
(groove depth, radius units), squash (an egg, 1 a sphere), tilt (turn, radians)."""
import math, os, random, sys


def params(seed, kv):
    R = random.Random(seed)
    P = dict(feed=0.037, kill=R.uniform(0.0598, 0.0608), scale=R.uniform(3.4, 4.0), vary=R.uniform(0.35, 0.5),
             round=R.uniform(0.45, 0.6), core=R.uniform(0.45, 0.55), dome=0.35,
             depth=R.uniform(0.055, 0.065), squash=R.uniform(0.95, 1.0), tilt=R.uniform(0, 6.28))
    for a in kv:
        k, v = a.split('='); assert k in P, k; P[k] = float(v)
    return P


def labyrinth(V, E, seed, P, steps=6000):
    """Gray-Scott on the mesh graph: returns the second substance per vertex, 0…1, and the neighbour-mean operator."""
    import numpy as np, scipy.sparse as sp
    n = len(V)
    A = sp.coo_matrix((np.ones(2 * len(E)), (np.r_[E[:, 0], E[:, 1]], np.r_[E[:, 1], E[:, 0]])), shape=(n, n)).tocsr()
    M = sp.diags(1 / np.asarray(A.sum(1)).ravel()) @ A
    R = np.random.default_rng(seed); U, W = np.ones(n), np.zeros(n)
    s = R.random(n) < 0.02; U[s], W[s] = 0.5, 0.5; W += R.random(n) * 0.02
    from mathutils import Vector, noise   # the stripe width drifts over the sphere: lobes of different sizes
    D = P['scale'] * (1 + P['vary'] * np.array([noise.noise(Vector(p) * 1.3 + Vector((seed, 0, 0))) for p in V]))
    Du, Dv, F, k = 0.16 * D, 0.08 * D, P['feed'], P['kill']
    for _ in range(steps):
        uvv = U * W * W
        U += Du * (M @ U - U) - uvv + F * (1 - U)
        W += Dv * (M @ W - W) + uvv - (F + k) * W
    return np.clip(W / W.max(), 0, 1), M


def render(argv):
    import bpy, bmesh
    import numpy as np
    from mathutils import Vector

    OUT, SEED = os.path.abspath(argv[0]), int(argv[1])
    SIZE = int(argv[2]) if len(argv) > 2 else 1024
    SAMPLES = int(argv[3]) if len(argv) > 3 else 128
    P = params(SEED, argv[4:])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene

    # the cell: an icosphere (164k vertices) sunk along the grooves, then subdivided twice at render time
    bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=7, radius=1.0); bm.verts.ensure_lookup_table()
    V = np.array([v.co[:] for v in bm.verts]); E = np.array([[e.verts[0].index, e.verts[1].index] for e in bm.edges])
    W, M = labyrinth(V, E, SEED, P)
    h = np.clip((1 - W) / (1 - P['core']), 0, 1) ** P['round'] * (1 - P['dome'] + P['dome'] * (1 - W) ** 0.7)
    h = 0.6 * h + 0.4 * (M @ h)        # one pass: the groove's floor, not the lobes
    for v, hv in zip(bm.verts, h): v.co = v.co.normalized() * (1 - P['depth'] * (1 - hv))
    me = bpy.data.meshes.new('cell'); bm.to_mesh(me); bm.free()
    for f in me.polygons: f.use_smooth = True
    at = me.attributes.new('h', 'FLOAT', 'POINT'); at.data.foreach_set('value', h.astype(np.float32))
    ob = bpy.data.objects.new('cell', me); sc.collection.objects.link(ob)
    sub = ob.modifiers.new('sub', 'SUBSURF'); sub.levels = 0; sub.render_levels = 2
    ob.scale = (1, 1, P['squash']); ob.rotation_euler = (P['tilt'] * 0.3, P['tilt'], 0)

    # cream-gold wax: soft subsurface, matte with a faint sheen; the grooves darken to honey-brown
    mat = bpy.data.materials.new('wax'); mat.use_nodes = True; nt = mat.node_tree; N = nt.nodes; L = nt.links.new
    bsdf = N['Principled BSDF']
    attr = N.new('ShaderNodeAttribute'); attr.attribute_name = 'h'
    ramp = N.new('ShaderNodeValToRGB'); ramp.color_ramp.interpolation = 'EASE'
    ramp.color_ramp.elements[0].position, ramp.color_ramp.elements[0].color = 0.2, (0.09, 0.04, 0.01, 1)
    ramp.color_ramp.elements[1].position, ramp.color_ramp.elements[1].color = 0.6, (0.78, 0.57, 0.28, 1)
    L(attr.outputs['Fac'], ramp.inputs['Fac']); L(ramp.outputs['Color'], bsdf.inputs['Base Color'])
    bsdf.inputs['Roughness'].default_value = 0.62; bsdf.inputs['Specular IOR Level'].default_value = 0.3
    bsdf.inputs['Subsurface Weight'].default_value = 0.3
    bsdf.inputs['Subsurface Radius'].default_value = (0.09, 0.05, 0.025)
    bsdf.inputs['Subsurface Scale'].default_value = 0.04
    bsdf.inputs['Sheen Weight'].default_value = 0.15
    bsdf.inputs['Sheen Tint'].default_value = (1.0, 0.85, 0.6, 1)
    ob.data.materials.append(mat)

    # light: a broad warm key from the top left, a fill from the right, two rims from behind (the glowing edge)
    def area(name, loc, size, energy, color):
        Lt = bpy.data.lights.new(name, 'AREA'); Lt.size = size; Lt.energy = energy; Lt.color = color
        o = bpy.data.objects.new(name, Lt); o.location = loc; sc.collection.objects.link(o)
        o.rotation_euler = (Vector((0, 0, 0)) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    area('key', (-3.2, -4.0, 3.6), 4.0, 380, (1.0, 0.92, 0.80))
    area('fill', (4.2, -3.0, 0.4), 5.0, 70, (1.0, 0.94, 0.86))
    area('rimL', (-3.5, 3.5, 1.2), 3.0, 1200, (1.0, 0.86, 0.62))
    area('rimR', (3.5, 3.2, -1.5), 3.0, 1100, (1.0, 0.84, 0.58))
    world = bpy.data.worlds.new('w'); sc.world = world; world.use_nodes = True
    world.node_tree.nodes['Background'].inputs['Color'].default_value = (0.20, 0.17, 0.13, 1)
    world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.35

    cam = bpy.data.cameras.new('cam'); cam.type = 'ORTHO'; cam.ortho_scale = 2.28
    co = bpy.data.objects.new('cam', cam); co.location = (0, -6, 0); co.rotation_euler = (math.pi / 2, 0, 0)
    sc.collection.objects.link(co); sc.camera = co

    sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = SAMPLES; sc.cycles.use_denoising = True
    sc.render.film_transparent = True; sc.render.resolution_x = sc.render.resolution_y = SIZE
    sc.render.image_settings.file_format = 'PNG'; sc.render.image_settings.color_mode = 'RGBA'
    sc.render.image_settings.color_depth = '16'
    sc.view_settings.view_transform = 'Standard'; sc.view_settings.exposure = 0.0
    sc.render.filepath = OUT
    bpy.ops.render.render(write_still=True)
    print('rendered', OUT, SIZE, 'px', P)


if __name__ == '__main__':
    render(sys.argv[1:])

#!/usr/bin/env python3
"""The MITOTECH CELL BOOSTER kit as an exact 3D model, rendered with Blender's Cycles (pip package bpy 4.5).

Why a model: the owner's rule is that a pack opens in a film only by a real photo or an exact 3D model, and that the
image model never draws a pack. Everything printed here is the owner's own print, rasterised from his vector files:
  box-front.png, box-metal.png   the lid's face, print R15 (site/proto/img/mitotech-cell-booster-3d, make_textures.py)
  label-card-powder.png, label-card-ampoule.png   the vial labels as on the owner's card of 22/11 (see below)
  guide.png                      the user guide R7 (USER_GUIDE_PRINT_R7.pdf, 297 x 232 mm) - inside the lid
  plate-soft.jpg                 the film's own clinic plate without the pack, blurred: the room behind the table
The textures are built by kit-textures.sh. The vial's glass and the applicator are the profiles of the owner's
render R15, as fitted in site/proto/scenes/mitotech-cell-booster.js (fractions of the vial's height).

The look of the vials is the owner's word of 22/11 ("this is how our ampoules look", his card with the two vials),
and it overrides the print file R15 with its dark green labels and white caps: the clear vial has a frosted white
label with black text and loose white powder, the amber vial has white text straight on the glass, both have a
silver-grey cap over a dark crimp and a black stopper. The lines of the labels are the card's, word for word.

What the print files do not say is taken from the owner's example photo of 22/11 (another brand's kit of the same
construction, "how MITOTECH opens") and is an assumption until he sends photos of his own open box:
  - the lid is hinged along the back edge, opens to about 100 degrees and is held by a white ribbon on the left;
  - the user guide is printed inside the lid;
  - a white insert holds two rows: four powder vials at the back, four ampoules at the front, an applicator at
    each end of each row (kit contents by the guide: powder x 4, ampoule x 4, applicators 4 pcs);
  - the size: the lid 306 x 241 mm (the guide sheet plus the board), the box 56 mm thick.

usage:  kit3d.py <textures dir> <out dir> [key=value ...]
  w, h        frame size in px (1344 x 760)
  spp         samples per pixel (48)
  angles      lid angles in degrees, comma separated, one frame each (0,102)
  clip        N - render the opening as N frames instead (the lid eases from 0 to `open`, with holds at both ends)
  open        the open angle (102)
  first,last  with clip: render only frames first..last (to resume or to split the work)
  name        file name stem (kit)
  border      x0,x1,y0,y1 - render only this part of the frame (fractions, y from the bottom), to look closely
Each frame is written as <out dir>/<name>-<index>.png.
"""
import math
import os
import sys

import bpy
from mathutils import Vector

TEX, OUT = sys.argv[1], sys.argv[2]
ARG = dict(a.split('=', 1) for a in sys.argv[3:] if '=' in a)
W_PX, H_PX, SPP = int(ARG.get('w', 1344)), int(ARG.get('h', 760)), int(ARG.get('spp', 48))
OPEN = float(ARG.get('open', 102))
NAME = ARG.get('name', 'kit')

# ---- sizes, metres (z up, the viewer at -y, the hinge at +y)
W, D = 0.306, 0.241            # the lid's face
T = 0.003                      # the board
HB, HS, HN = 0.034, 0.053, 0.050   # the base's outer wall, the spine (and the lid's underside), the white neck
TN = 0.0025                    # the neck's wall
FLOOR, INS = 0.012, 0.030      # the pockets' floor, the insert's top
L = 0.067                      # a vial with its cap
R = 0.2331 * L                 # its body's radius
GREEN = (0x15 / 255, 0x47 / 255, 0x34 / 255)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
cy = scene.cycles
cy.device = 'CPU'
cy.samples = SPP
cy.use_adaptive_sampling = True
cy.adaptive_threshold = 0.015
cy.use_denoising = True
cy.denoiser = 'OPENIMAGEDENOISE'
cy.max_bounces, cy.glossy_bounces, cy.transmission_bounces, cy.transparent_max_bounces = 14, 6, 14, 16
cy.caustics_reflective = cy.caustics_refractive = False
scene.render.threads_mode = 'FIXED'
scene.render.threads = int(ARG.get('threads', 4))
scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage = W_PX, H_PX, 100
scene.render.image_settings.file_format = 'PNG'
if 'border' in ARG:                                 # a part of the frame only: x0,x1,y0,y1 as fractions, y from the bottom
    b = [float(v) for v in ARG['border'].split(',')]
    scene.render.use_border = scene.render.use_crop_to_border = True
    scene.render.border_min_x, scene.render.border_max_x, scene.render.border_min_y, scene.render.border_max_y = b
scene.render.image_settings.color_mode = 'RGB'
scene.view_settings.view_transform = ARG.get('view', 'Filmic')
try:
    scene.view_settings.look = ARG.get('look', 'High Contrast')
except TypeError:
    scene.view_settings.look = 'None'
scene.view_settings.exposure = float(ARG.get('exposure', 0))


def srgb(c):
    return tuple(((v / 12.92) if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4) for v in c) + (1.0,)


# ---- materials
def material(name, color=(0.8, 0.8, 0.8), rough=0.5, metal=0.0, **more):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes['Principled BSDF']
    bsdf.inputs['Base Color'].default_value = srgb(color)
    bsdf.inputs['Roughness'].default_value = rough
    bsdf.inputs['Metallic'].default_value = metal
    for key, value in more.items():
        bsdf.inputs[key].default_value = value
    return mat


def image(file, data=False):
    img = bpy.data.images.load(os.path.join(TEX, file))
    if data:
        img.colorspace_settings.name = 'Non-Color'
    return img


def printed(name, file, rough=0.5, metal_map=None, alpha=False):
    """A printed sheet: the picture as the colour; with metal_map (G roughness, B metalness) a foil under inks;
    with alpha the picture's own transparency (a frosted label, text printed on bare glass)."""
    mat = material(name, rough=rough)
    tree = mat.node_tree
    bsdf = tree.nodes['Principled BSDF']
    tex = tree.nodes.new('ShaderNodeTexImage')
    tex.image = image(file)
    tex.extension = 'EXTEND'
    tree.links.new(tex.outputs['Color'], bsdf.inputs['Base Color'])
    if alpha:
        tex.image.alpha_mode = 'STRAIGHT'
        tree.links.new(tex.outputs['Alpha'], bsdf.inputs['Alpha'])
    if metal_map:
        mtex = tree.nodes.new('ShaderNodeTexImage')
        mtex.image = image(metal_map, data=True)
        mtex.extension = 'EXTEND'
        sep = tree.nodes.new('ShaderNodeSeparateColor')
        tree.links.new(mtex.outputs['Color'], sep.inputs['Color'])
        tree.links.new(sep.outputs['Green'], bsdf.inputs['Roughness'])
        less = tree.nodes.new('ShaderNodeMath')
        less.operation = 'MULTIPLY'
        less.inputs[1].default_value = FOIL_METAL
        tree.links.new(sep.outputs['Blue'], less.inputs[0])
        tree.links.new(less.outputs[0], bsdf.inputs['Metallic'])
    return mat


def glass(name, tint=(1, 1, 1), ior=1.5, rough=0.0, shadow=0.9):
    """Clear or tinted glass that lets light through into its shadow (Cycles has no caustics here: without this
    a vial would throw a black shadow)."""
    mat = material(name, color=tint, rough=rough)
    tree = mat.node_tree
    bsdf = tree.nodes['Principled BSDF']
    bsdf.inputs['Transmission Weight'].default_value = 1.0
    bsdf.inputs['IOR'].default_value = ior
    out = tree.nodes['Material Output']
    clear = tree.nodes.new('ShaderNodeBsdfTransparent')
    clear.inputs['Color'].default_value = srgb(tuple(0.35 + 0.65 * v for v in tint))
    path = tree.nodes.new('ShaderNodeLightPath')
    fac = tree.nodes.new('ShaderNodeMath')
    fac.operation = 'MULTIPLY'
    fac.inputs[1].default_value = shadow
    mix = tree.nodes.new('ShaderNodeMixShader')
    tree.links.new(path.outputs['Is Shadow Ray'], fac.inputs[0])
    tree.links.new(fac.outputs[0], mix.inputs['Fac'])
    tree.links.new(bsdf.outputs['BSDF'], mix.inputs[1])
    tree.links.new(clear.outputs['BSDF'], mix.inputs[2])
    tree.links.new(mix.outputs['Shader'], out.inputs['Surface'])
    return mat


FOIL_METAL = float(ARG.get('foilmetal', 0.16))
M_FOIL = material('foil', GREEN, rough=0.34, metal=FOIL_METAL, **{'Coat Weight': 0.25, 'Coat Roughness': 0.2})
M_FACE = printed('face', 'box-front.png', metal_map='box-metal.png')
M_CARD = material('card', (0.955, 0.955, 0.95), rough=0.62)
M_GUIDE = printed('guide', 'guide.png', rough=0.6)
M_RIBBON = material('ribbon', (0.96, 0.96, 0.95), rough=0.38, **{'Sheen Weight': 0.4})
M_GLASS = glass('glass')
M_AMBER = glass('amber', tint=(0.80, 0.47, 0.17), shadow=0.55)
M_PLASTIC = material('applicator', (0.93, 0.94, 0.94), rough=0.32, **{'Transmission Weight': float(ARG.get('appclear', 0.45)), 'IOR': 1.49})
M_CAP = material('cap', (0.70, 0.71, 0.73), rough=0.42, metal=0.85)        # silver-grey, matte
M_RING = material('ring', (0.10, 0.10, 0.11), rough=0.3, metal=0.7)         # the dark crimp under the cap
M_STOP = material('stopper', (0.03, 0.03, 0.035), rough=0.55)               # black rubber
# the powder glows a little: with caustics off, the light that real glass lets through to it is missing
M_CAKE = material('powder', (0.97, 0.97, 0.96), rough=0.95, **{'Emission Color': (1, 1, 1, 1), 'Emission Strength': float(ARG.get('cake', 0.3))})
M_TIP = material('tip', (0.96, 0.96, 0.955), rough=0.4)
M_LABEL = {'P': printed('label-powder', 'label-card-powder.png', rough=0.5, alpha=True),
           'B': printed('label-ampoule', 'label-card-ampoule.png', rough=0.5, alpha=True)}


# ---- meshes
def mesh_object(name, verts, faces, mat, smooth=False, uvs=None, parent=None):
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.materials.append(mat)
    if uvs:
        layer = me.uv_layers.new(name='UV')
        for poly in me.polygons:
            for loop, vert in zip(poly.loop_indices, poly.vertices):
                layer.data[loop].uv = uvs[vert]
    if smooth:
        me.polygons.foreach_set('use_smooth', [True] * len(me.polygons))
        me.set_sharp_from_angle(angle=math.radians(38))
    me.update()
    ob = bpy.data.objects.new(name, me)
    scene.collection.objects.link(ob)
    if parent:
        ob.parent = parent
    return ob


def box(name, x0, x1, y0, y1, z0, z1, mat, parent=None, round_edge=0.0005):
    v = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    f = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    ob = mesh_object(name, v, f, mat, parent=parent)
    if round_edge and min(x1 - x0, y1 - y0, z1 - z0) > 2.2 * round_edge:
        bevel = ob.modifiers.new('edge', 'BEVEL')
        bevel.width, bevel.segments = round_edge, 2
    return ob


def sheet(name, corners, mat, parent=None):
    """A printed rectangle: corners in the order (u0 v0), (u1 v0), (u1 v1), (u0 v1)."""
    return mesh_object(name, corners, [(0, 1, 2, 3)], mat, uvs=[(0, 0), (1, 0), (1, 1), (0, 1)], parent=parent)


def lathe(name, profile, mat, segs=72, parent=None):
    """profile: (radius, height) pairs from the foot up; radius 0 is a point on the axis."""
    verts, rows = [], []
    for r, z in profile:
        if r < 1e-7:
            rows.append([len(verts)])
            verts.append((0.0, 0.0, z))
        else:
            rows.append(list(range(len(verts), len(verts) + segs)))
            verts += [(r * math.sin(2 * math.pi * i / segs), -r * math.cos(2 * math.pi * i / segs), z) for i in range(segs)]
    faces = []
    for a, b in zip(rows, rows[1:]):
        for i in range(segs):
            j = (i + 1) % segs
            if len(a) == 1 and len(b) > 1:
                faces.append((a[0], b[j], b[i]))
            elif len(b) == 1 and len(a) > 1:
                faces.append((a[i], a[j], b[0]))
            elif len(a) > 1:
                faces.append((a[i], a[j], b[j], b[i]))
    return mesh_object(name, verts, faces, mat, smooth=True, parent=parent)


def arc(cx, cz, r, a0, a1, n):
    return [(cx + r * math.cos(a0 + (a1 - a0) * i / n), cz + r * math.sin(a0 + (a1 - a0) * i / n)) for i in range(n + 1)]


def scaled(points, k=L, dz=0.0):
    return [(r * k, (z - dz) * k) for r, z in points]


RV = 0.2331
RI = RV - 0.013
GLASS_OUT = ([(0, 0), (RV - 0.035, 0)] + arc(RV - 0.035, 0.035, 0.035, -math.pi / 2, 0, 8)
             + [(RV, 0.735), (RV - 0.006, 0.76), (0.2, 0.778), (0.168, 0.79), (0.135, 0.798), (0.128, 0.806),
                (0.128, 0.83), (0.15, 0.836), (0.15, 0.864), (0.142, 0.868), (0.1, 0.868)])
GLASS_IN = ([(0.1, 0.84), (0.105, 0.806), (0.118, 0.796), (0.155, 0.787), (0.19, 0.775), (RI - 0.008, 0.758), (RI, 0.735)]
            + arc(RI - 0.03, 0.058, 0.03, 0, -math.pi / 2, 6) + [(0, 0.028)])
RING = [(0.1, 0.915), (0.176, 0.915), (0.18, 0.909), (0.18, 0.822), (0.174, 0.815), (0.135, 0.815), (0.135, 0.86), (0.1, 0.866)]
CAP = ([(0, 0.915), (0.186, 0.915), (0.192, 0.921)] + arc(0.172, 0.978, 0.02, 0, math.pi / 2, 8)
       + [(0.11, 0.9985), (0, 1.0)])
STOP = [(0, 0.725), (0.092, 0.725), (0.1, 0.735), (0.1, 0.80), (0.105, 0.806), (0.105, 0.866), (0.146, 0.866), (0.15, 0.872), (0.15, 0.905),
        (0, 0.905)]
APP = [(0.13, 0.80), (0.192, 0.80), (0.198, 0.81), (0.198, 0.98), (0.19, 1.0), (0.15, 1.035), (0.09, 1.06), (0.063, 1.075),
       (0.05, 1.15), (0.036, 1.27), (0.0, 1.27)]
APP_IN = [(0.0, 1.262), (0.03, 1.262), (0.044, 1.15), (0.057, 1.07), (0.085, 1.052), (0.143, 1.028), (0.183, 0.995),
          (0.188, 0.98), (0.188, 0.80), (0.13, 0.80)]
TIP = [(0, 1.262), (0.037, 1.262)] + arc(0.017, 1.3, 0.02, -0.2, math.pi / 2, 6) + [(0, 1.32)]
LABEL_BAND, LABEL_HALF = (0.126, 0.63), math.radians(56)      # a front label, as on the owner's card


def vial(kind, x, y_foot, z_axis):
    """A vial lying in its pocket: the foot toward the viewer, the cap toward the hinge, the label's title up."""
    root = bpy.data.objects.new('vial-' + kind, None)
    scene.collection.objects.link(root)
    lathe('glass', scaled(GLASS_OUT + GLASS_IN), M_AMBER if kind == 'B' else M_GLASS, parent=root)
    lathe('ring', scaled(RING), M_RING, parent=root)
    lathe('cap', scaled(CAP), M_CAP, parent=root)
    lathe('stopper', scaled(STOP), M_STOP, parent=root)
    if kind == 'P':
        powder(root)
    n, r = 64, RV * 1.006 * L
    z0, z1 = LABEL_BAND[0] * L, LABEL_BAND[1] * L
    verts, uvs, faces = [], [], []
    for i in range(n + 1):
        phi = -LABEL_HALF + 2 * LABEL_HALF * i / n         # from the front (-y) toward +x
        for z, v in ((z0, 0.0), (z1, 1.0)):
            verts.append((r * math.sin(phi), -r * math.cos(phi), z))
            uvs.append((i / n, v))
    for i in range(n):
        faces.append((2 * i, 2 * i + 2, 2 * i + 3, 2 * i + 1))
    mesh_object('label', verts, faces, M_LABEL[kind], smooth=True, uvs=uvs, parent=root)
    root.rotation_euler = (-math.pi / 2, 0, 0)          # the top to +y, the front up
    root.location = (x, y_foot, z_axis)
    return root


def powder(root):
    """Loose powder in a vial that lies on its side: a shallow uneven layer along the lower wall (the vial's back,
    +y, is down once it lies). About the amount of the card's heap: a seventh of the vial's cross-section."""
    r, stations, arc_n = (RI - 0.004) * L, 60, 20
    verts, faces = [], []
    for k in range(stations + 1):
        z = (0.04 + 0.60 * k / stations) * L
        wave = 0.035 * math.sin(k * 0.41) + 0.025 * math.sin(k * 0.17 + 1.0)   # a gently uneven surface, no ridges
        taper = min(1.0, k / 5.0, (stations - k) / 8.0)          # the layer thins out toward both ends
        half = math.radians(62) * (0.35 + 0.65 * taper) * (1 + wave)
        for j in range(arc_n + 1):
            a = -half + 2 * half * j / arc_n
            verts.append((r * math.sin(a), r * math.cos(a), z))
    row = arc_n + 1
    for k in range(stations):
        for j in range(arc_n):
            a, b = k * row + j, (k + 1) * row + j
            faces.append((a, a + 1, b + 1, b))                   # against the glass
        faces.append((k * row, (k + 1) * row, (k + 1) * row + arc_n, k * row + arc_n))   # the powder's own surface
    faces.append(tuple(range(row)))
    faces.append(tuple(range(stations * row, stations * row + row)))
    ob = mesh_object('powder', verts, faces, M_CAKE, parent=root)
    ob.data.polygons.foreach_set('use_smooth', [True] * len(ob.data.polygons))
    return ob


def applicator(x, y_mid, z_axis):
    """An applicator lying in its pocket, the collar toward the hinge, the tip toward the viewer."""
    root = bpy.data.objects.new('applicator', None)
    scene.collection.objects.link(root)
    lathe('body', scaled(APP + APP_IN, dz=0.80), M_PLASTIC, parent=root)
    lathe('tip', scaled(TIP, dz=0.80), M_TIP, segs=32, parent=root)
    root.rotation_euler = (math.pi / 2, 0, 0)           # the tip to -y
    root.location = (x, y_mid + 0.26 * L, z_axis)
    return root


def stadium(cx, cy, width, length, z0, z1, n=20):
    """A prism with round ends, its long side along y: a pocket's cutter."""
    r, h = width / 2, (length - width) / 2
    ring = [(cx + r * math.cos(math.pi * i / n), cy + h + r * math.sin(math.pi * i / n)) for i in range(n + 1)]
    ring += [(cx - r * math.cos(math.pi * i / n), cy - h - r * math.sin(math.pi * i / n)) for i in range(n + 1)]
    m = len(ring)
    verts = [(x, y, z0) for x, y in ring] + [(x, y, z1) for x, y in ring]
    faces = [tuple(range(m - 1, -1, -1)), tuple(range(m, 2 * m))]
    faces += [(i, (i + 1) % m, m + (i + 1) % m, m + i) for i in range(m)]
    return verts, faces


VIAL_X = (-0.069, -0.023, 0.023, 0.069)
APP_X = (-0.120, 0.120)
ROW_FOOT = {'P': 0.0225, 'B': -0.0855}            # where a vial's foot lies: the powders behind, the ampoules in front
ROW_MID = {k: v + L / 2 for k, v in ROW_FOOT.items()}


def build_base():
    box('bottom', -W / 2 + T, W / 2 - T, -D / 2 + T, D / 2 - T, 0.0002, T, M_FOIL)
    box('front', -W / 2, W / 2, -D / 2, -D / 2 + T, 0, HB, M_FOIL)
    box('left', -W / 2, -W / 2 + T, -D / 2 + T, D / 2 - T, 0, HB, M_FOIL)
    box('right', W / 2 - T, W / 2, -D / 2 + T, D / 2 - T, 0, HB, M_FOIL)
    box('spine', -W / 2, W / 2, D / 2 - T, D / 2, 0, HS, M_FOIL)
    g = T + 0.0003                                   # the neck stands a hair inside the lid's walls
    box('neck-front', -W / 2 + g, W / 2 - g, -D / 2 + g, -D / 2 + g + TN, T, HN, M_CARD)
    box('neck-left', -W / 2 + g, -W / 2 + g + TN, -D / 2 + g + TN, D / 2 - T - 0.0006, T, HN, M_CARD)
    box('neck-right', W / 2 - g - TN, W / 2 - g, -D / 2 + g + TN, D / 2 - T - 0.0006, T, HN, M_CARD)
    box('neck-back', -W / 2 + g, W / 2 - g, D / 2 - T - 0.0006, D / 2 - T, T, HS - 0.0004, M_CARD)
    i = g + TN
    box('floor', -W / 2 + i, W / 2 - i, -D / 2 + i, D / 2 - T - 0.0006, T, FLOOR, M_CARD)
    slab = box('insert', -W / 2 + i, W / 2 - i, -D / 2 + i, D / 2 - T - 0.0006, FLOOR, INS, M_CARD, round_edge=0)
    verts, faces = [], []
    pockets = [(x, ROW_MID[k], 2 * R + 0.003, L + 0.006) for k in 'PB' for x in VIAL_X]
    pockets += [(x, ROW_MID[k], 0.0305, 0.043) for k in 'PB' for x in APP_X]
    for cx, cyy, width, length in pockets:
        v, f = stadium(cx, cyy, width, length, FLOOR - 0.001, INS + 0.001)
        faces += [tuple(n + len(verts) for n in face) for face in f]
        verts += v
    cutter = mesh_object('pockets', verts, faces, M_CARD)
    cut = slab.modifiers.new('pockets', 'BOOLEAN')
    cut.operation, cut.object, cut.solver = 'DIFFERENCE', cutter, 'EXACT'
    bevel = slab.modifiers.new('edge', 'BEVEL')
    bevel.width, bevel.segments, bevel.limit_method, bevel.angle_limit = 0.0008, 2, 'ANGLE', math.radians(40)
    bpy.context.view_layer.update()
    done = bpy.data.meshes.new_from_object(slab.evaluated_get(bpy.context.evaluated_depsgraph_get()))
    slab.modifiers.clear()
    slab.data = done
    bpy.data.objects.remove(cutter)
    for kind in 'PB':
        for x in VIAL_X:
            vial(kind, x, ROW_FOOT[kind], FLOOR + R + 0.0002)
        for x in APP_X:
            applicator(x, ROW_MID[kind], FLOOR + 0.198 * L + 0.0002)


def build_lid():
    """The lid in its own frame: the hinge line is its x axis, the face lies toward -y, the underside at z 0."""
    lid = bpy.data.objects.new('lid', None)
    scene.collection.objects.link(lid)
    lid.location = (0, D / 2, HS)
    box('lid-board', -W / 2, W / 2, -D, 0, 0, T, M_FOIL, parent=lid)
    sheet('lid-face', [(-W / 2, -D, T + 0.0002), (W / 2, -D, T + 0.0002), (W / 2, 0, T + 0.0002), (-W / 2, 0, T + 0.0002)],
          M_FACE, parent=lid)
    drop = HS - HB
    box('lid-left', -W / 2, -W / 2 + T, -D + T, -0.002, -drop, -0.0001, M_FOIL, parent=lid)
    box('lid-right', W / 2 - T, W / 2, -D + T, -0.002, -drop, -0.0001, M_FOIL, parent=lid)
    box('lid-front', -W / 2, W / 2, -D, -D + T, -drop, -0.0001, M_FOIL, parent=lid)
    e = 0.0004                                       # the white lining inside the lid's walls and under its board
    box('lid-left-in', -W / 2 + T, -W / 2 + T + e, -D + T, -0.002, -drop + 0.0003, 0, M_CARD, parent=lid)
    box('lid-right-in', W / 2 - T - e, W / 2 - T, -D + T, -0.002, -drop + 0.0003, 0, M_CARD, parent=lid)
    box('lid-front-in', -W / 2 + T, W / 2 - T, -D + T, -D + T + e, -drop + 0.0003, 0, M_CARD, parent=lid)
    box('lid-lining', -W / 2 + T, W / 2 - T, -D + T, 0, -e, 0, M_CARD, parent=lid)
    gw, gh = 0.297, 0.232                            # the guide sheet, its head toward the lid's free edge
    y_far, z = -D + T + (D - T - gh) / 2, -e - 0.0002
    sheet('lid-guide', [(-gw / 2, y_far + gh, z), (gw / 2, y_far + gh, z), (gw / 2, y_far, z), (-gw / 2, y_far, z)],
          M_GUIDE, parent=lid)
    return lid


RIB_A = Vector((-W / 2 + T + TN + 0.0009, 0.035, HN - 0.004))      # on the neck's left wall
RIB_B = Vector((-W / 2 + T + 0.0009, -0.110, -0.008))             # on the lid's left wall, in the lid's frame


def set_lid(lid, ribbon, degrees):
    a = math.radians(degrees)
    lid.rotation_euler = (-a, 0, 0)
    b = Vector((RIB_B.x, D / 2 + RIB_B.y * math.cos(a) + RIB_B.z * math.sin(a), HS - RIB_B.y * math.sin(a) + RIB_B.z * math.cos(a)))
    along = b - RIB_A
    across = along.cross(Vector((1, 0, 0)))
    across = across.normalized() * 0.005 if across.length > 1e-6 else Vector((0, 0.005, 0))
    for vert, point in zip(ribbon.data.vertices, (RIB_A - across, RIB_A + across, b + across, b - across)):
        vert.co = point
    ribbon.data.update()


# ---- the room: a polished cream stone table, the clinic behind it out of focus, daylight from a window on the right
def build_room():
    stone = material('stone', (0.86, 0.83, 0.78), rough=0.1, **{'Coat Weight': 0.35, 'Coat Roughness': 0.04})
    tree = stone.node_tree
    bsdf = tree.nodes['Principled BSDF']
    coords = tree.nodes.new('ShaderNodeTexCoord')
    noise = tree.nodes.new('ShaderNodeTexNoise')
    tree.links.new(coords.outputs['Object'], noise.inputs['Vector'])
    noise.inputs['Scale'].default_value = 6.5
    noise.inputs['Detail'].default_value = 7.0
    noise.inputs['Distortion'].default_value = 2.4
    ramp = tree.nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].position, ramp.color_ramp.elements[1].position = 0.42, 0.66
    ramp.color_ramp.elements[0].color, ramp.color_ramp.elements[1].color = srgb((0.885, 0.855, 0.805)), srgb((0.80, 0.765, 0.71))
    tree.links.new(noise.outputs['Fac'], ramp.inputs['Fac'])
    tree.links.new(ramp.outputs['Color'], bsdf.inputs['Base Color'])
    table = box('table', -1.7, 1.7, -1.2, float(ARG.get('tableback', 0.42)), -0.04, 0.0, stone, round_edge=0.004)
    world = bpy.data.worlds.new('world')
    world.use_nodes = True
    back = world.node_tree.nodes['Background']
    back.inputs['Color'].default_value = srgb((1.0, 0.955, 0.9))
    back.inputs['Strength'].default_value = float(ARG.get('ambient', 0.75))
    scene.world = world
    lamp('window', (1.7, 1.25, 1.35), (0.0, 0.0, 0.03), 1.3, 0.9, float(ARG.get('key', 240)), (1.0, 0.985, 0.96))
    lamp('fill', (-1.5, -1.1, 1.0), (0.0, 0.0, 0.05), 1.6, 1.2, float(ARG.get('fill', 14)), (1.0, 0.95, 0.88))
    lamp('top', (0.1, 0.1, 1.9), (0.0, 0.0, 0.0), 1.4, 1.4, float(ARG.get('top', 8)), (1.0, 0.98, 0.95))
    return table


def lamp(name, at, to, sx, sy, watts, color):
    data = bpy.data.lights.new(name, 'AREA')
    data.shape, data.size, data.size_y, data.energy, data.color = 'RECTANGLE', sx, sy, watts, color
    ob = bpy.data.objects.new(name, data)
    scene.collection.objects.link(ob)
    ob.location = at
    ob.rotation_euler = (Vector(to) - Vector(at)).to_track_quat('-Z', 'Y').to_euler()
    ob.visible_camera = False
    return ob


def build_camera():
    data = bpy.data.cameras.new('camera')
    data.lens, data.sensor_width = float(ARG.get('lens', 58)), 36
    data.shift_x, data.shift_y = float(ARG.get('shiftx', 0.17)), float(ARG.get('shifty', 0.0))
    ob = bpy.data.objects.new('camera', data)
    scene.collection.objects.link(ob)
    scene.camera = ob
    target = Vector((float(ARG.get('tx', 0.0)), float(ARG.get('ty', 0.03)), float(ARG.get('tz', 0.115))))
    dist, el, az = float(ARG.get('dist', 1.47)), math.radians(float(ARG.get('el', 41))), math.radians(float(ARG.get('az', 25)))
    ob.location = target + dist * Vector((math.sin(az) * math.cos(el), -math.cos(az) * math.cos(el), math.sin(el)))
    ob.rotation_euler = (target - ob.location).to_track_quat('-Z', 'Y').to_euler()
    data.dof.use_dof = True
    data.dof.focus_distance = dist
    data.dof.aperture_fstop = float(ARG.get('fstop', 5.6))
    # the room: the film's clinic plate, soft, on a sheet that faces the camera far behind the table. Its rows
    # `roomshift`..: the part with the people and the window shows above the table's far edge
    far = float(ARG.get('roomdist', 4.2))
    half_w = far * 18 / data.lens * float(ARG.get('roomscale', 1.12))
    half_h = half_w * H_PX / W_PX
    cx = data.shift_x * 36 / data.lens * far
    cyy = (data.shift_y * 36 / data.lens * far) + 2 * half_h * float(ARG.get('roomshift', 0.25))
    backdrop = material('room')
    tree = backdrop.node_tree
    tree.nodes.remove(tree.nodes['Principled BSDF'])
    emit = tree.nodes.new('ShaderNodeEmission')
    tex = tree.nodes.new('ShaderNodeTexImage')
    tex.image = image('plate-soft.jpg')
    tex.extension = 'EXTEND'
    emit.inputs['Strength'].default_value = float(ARG.get('room', 1.0))
    tree.links.new(tex.outputs['Color'], emit.inputs['Color'])
    tree.links.new(emit.outputs['Emission'], tree.nodes['Material Output'].inputs['Surface'])
    wall = sheet('room', [(cx - half_w, cyy - half_h, -far), (cx + half_w, cyy - half_h, -far), (cx + half_w, cyy + half_h, -far),
                          (cx - half_w, cyy + half_h, -far)], backdrop, parent=ob)
    wall.visible_shadow = wall.visible_diffuse = False      # a picture of the room, not a lamp
    return ob


build_room()
build_base()
LID = build_lid()
RIBBON = mesh_object('ribbon', [(0, 0, 0)] * 4, [(0, 1, 2, 3)], M_RIBBON)
build_camera()


def ease(t):
    t = min(1.0, max(0.0, t))
    return t * t * t * (t * (6 * t - 15) + 10)


if 'clip' in ARG:
    total = int(ARG['clip'])
    hold_in, hold_out = int(ARG.get('holdin', 10)), int(ARG.get('holdout', 22))
    plan = [OPEN * ease((n - hold_in) / max(1, total - 1 - hold_in - hold_out)) for n in range(total)]
    frames = range(int(ARG.get('first', 0)), int(ARG.get('last', total - 1)) + 1)
else:
    plan = [float(v) for v in ARG.get('angles', '0,102').split(',')]
    frames = range(len(plan))
os.makedirs(OUT, exist_ok=True)
import shutil
same = {}                                            # the camera stands still: a hold is one render, copied
for n in range(len(plan)):
    target = os.path.join(OUT, '%s-%04d.png' % (NAME, n))
    key = round(plan[n], 3)
    if n not in frames:
        if os.path.exists(target):
            same.setdefault(key, target)
        continue
    if os.path.exists(target) and ARG.get('redo') != '1':
        same.setdefault(key, target)
        continue
    if key in same:
        shutil.copyfile(same[key], target)
        print('frame %d angle %.1f = %s' % (n, plan[n], os.path.basename(same[key])), flush=True)
        continue
    set_lid(LID, RIBBON, plan[n])
    scene.render.filepath = target
    bpy.ops.render.render(write_still=True)
    same[key] = target
    print('frame %d angle %.1f -> %s' % (n, plan[n], target), flush=True)

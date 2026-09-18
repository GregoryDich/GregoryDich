#!/usr/bin/env python3
"""
Процедурная рифовая сцена для аквариума (Blender 4.2+/5.x как модуль `bpy`).

Песок, скальная стена, кораллы-мозговики, ветвистые кораллы, трубчатые губки,
актиния, морская звезда, веера-горгонарии, галька; вода — градиент + туман по
дальности. Рендер Cycles в ДВА слоя:
  reef_bg.jpg — задник (вода, дальний риф, песок) — рыбы плавают поверх него;
  reef_fg.png — прозрачный передний план (ближние кораллы) — рыбы проходят ЗА ним.

  python3 reef.py --out ../assets --res 1920 --samples 96
  python3 reef.py --out /tmp/x --preview          # быстро, низкое качество
"""
import sys, os, math, random
import bpy, bmesh
from mathutils import Vector, Matrix

def arg(name, default, cast=str):
    return cast(sys.argv[sys.argv.index(name) + 1]) if name in sys.argv else default
PREVIEW = '--preview' in sys.argv
OUT = arg('--out', 'out'); RES = arg('--res', 960 if PREVIEW else 1920, int)
SAMPLES = arg('--samples', 24 if PREVIEW else 96, int); SEED = arg('--seed', 7, int)
LAYERS = arg('--only', 'bg,fg').split(',')
ASPECT = 16 / 10
FOG = (.03, .16, .42)
rng = random.Random(SEED)

# ---------------------------------------------------------------- база
try: bpy.ops.wm.read_factory_settings(use_empty=True)
except Exception: pass
sc = bpy.context.scene
BG = bpy.data.collections.new('bg'); FG = bpy.data.collections.new('fg')
sc.collection.children.link(BG); sc.collection.children.link(FG)

def new_obj(name, me, coll, loc=(0, 0, 0), rot=(0, 0, 0), scale=(1, 1, 1)):
    ob = bpy.data.objects.new(name, me); coll.objects.link(ob)
    ob.location = loc; ob.rotation_euler = rot; ob.scale = scale
    return ob

def smooth(me):
    for p in me.polygons: p.use_smooth = True

def tex_clouds(name, scale, depth=3):
    t = bpy.data.textures.new(name, 'CLOUDS'); t.noise_scale = scale; t.noise_depth = depth; return t

def displace(ob, tex, strength, coords='GLOBAL'):
    d = ob.modifiers.new('disp', 'DISPLACE'); d.texture = tex; d.strength = strength; d.mid_level = .5; d.texture_coords = coords

def subsurf(ob, lv):
    m = ob.modifiers.new('subd', 'SUBSURF'); m.levels = max(0, lv - 1); m.render_levels = lv

# ---------------------------------------------------------------- материалы
def mat(name, color, rough=.75, sss=0, bump=.35, bump_scale=6, tint2=None, coat=0, detail=5, cells=0):
    m = bpy.data.materials.new(name); m.use_nodes = True; n = m.node_tree.nodes; l = m.node_tree.links; p = n['Principled BSDF']
    p.inputs['Roughness'].default_value = rough; p.inputs['Subsurface Weight'].default_value = sss
    p.inputs['Coat Weight'].default_value = coat; p.inputs['Subsurface Radius'].default_value = (.1, .05, .03)
    noise = n.new('ShaderNodeTexNoise'); noise.inputs['Scale'].default_value = bump_scale; noise.inputs['Detail'].default_value = detail
    if tint2:
        ramp = n.new('ShaderNodeValToRGB'); ramp.color_ramp.elements[0].color = (*color, 1); ramp.color_ramp.elements[1].color = (*tint2, 1)
        ramp.color_ramp.elements[0].position = .35; ramp.color_ramp.elements[1].position = .65
        l.new(noise.outputs['Fac'], ramp.inputs['Fac']); col_out = ramp.outputs['Color']
    else:
        rgb = n.new('ShaderNodeRGB'); rgb.outputs['Color'].default_value = (*color, 1); col_out = rgb.outputs['Color']
    # ambient occlusion → тёмные щели и основания (главный признак «настоящего» рифа)
    ao = n.new('ShaderNodeAmbientOcclusion'); ao.inputs['Distance'].default_value = .8; ao.samples = 8
    aomap = n.new('ShaderNodeMapRange'); aomap.inputs['To Min'].default_value = .28; aomap.inputs['To Max'].default_value = 1.0
    l.new(ao.outputs['AO'], aomap.inputs['Value'])
    scl = n.new('ShaderNodeVectorMath'); scl.operation = 'SCALE'
    l.new(col_out, scl.inputs[0]); l.new(aomap.outputs['Result'], scl.inputs['Scale']); l.new(scl.outputs['Vector'], p.inputs['Base Color'])
    b = n.new('ShaderNodeBump'); b.inputs['Strength'].default_value = bump
    l.new(noise.outputs['Fac'], b.inputs['Height']); l.new(b.outputs['Normal'], p.inputs['Normal'])
    if cells:   # ячейки полипов поверх крупного рельефа
        vor = n.new('ShaderNodeTexVoronoi'); vor.inputs['Scale'].default_value = cells
        b2 = n.new('ShaderNodeBump'); b2.inputs['Strength'].default_value = .8
        l.new(vor.outputs['Distance'], b2.inputs['Height']); l.new(b.outputs['Normal'], b2.inputs['Normal']); l.new(b2.outputs['Normal'], p.inputs['Normal'])
    return m

def add_fog(m, start=12.0, end=26.0):
    """Туман по дальности от камеры прямо в шейдере (работает и в прозрачном слое)."""
    n = m.node_tree.nodes; l = m.node_tree.links; out = n['Material Output']
    lk = next((x for x in l if x.to_socket == out.inputs['Surface']), None)
    if not lk: return
    src = lk.from_socket; l.remove(lk)
    cam = n.new('ShaderNodeCameraData'); mr = n.new('ShaderNodeMapRange')
    mr.inputs['From Min'].default_value = start; mr.inputs['From Max'].default_value = end
    mr.inputs['To Min'].default_value = 0; mr.inputs['To Max'].default_value = .7
    l.new(cam.outputs['View Distance'], mr.inputs['Value'])
    em = n.new('ShaderNodeEmission'); em.inputs['Color'].default_value = (*FOG, 1); em.inputs['Strength'].default_value = 1.0
    mix = n.new('ShaderNodeMixShader'); l.new(mr.outputs['Result'], mix.inputs['Fac'])
    l.new(src, mix.inputs[1]); l.new(em.outputs['Emission'], mix.inputs[2]); l.new(mix.outputs['Shader'], out.inputs['Surface'])

# ---------------------------------------------------------------- генераторы
def sand(coll):
    bm = bmesh.new(); bmesh.ops.create_grid(bm, x_segments=180, y_segments=180, size=1.0)
    me = bpy.data.meshes.new('sand'); bm.to_mesh(me); bm.free(); smooth(me)
    ob = new_obj('sand', me, coll, scale=(40, 40, 1))
    displace(ob, tex_clouds('sand_hills', 3.0, 2), .35)
    displace(ob, tex_clouds('sand_ripples', .9, 1), .025); subsurf(ob, 1)
    m = mat('sand', (.50, .45, .30), rough=.95, bump=.3, bump_scale=30, tint2=(.36, .33, .22))
    n = m.node_tree.nodes; l = m.node_tree.links; p = n['Principled BSDF']
    tc = n.new('ShaderNodeTexCoord'); vor = n.new('ShaderNodeTexVoronoi'); vor.feature = 'DISTANCE_TO_EDGE'
    vor.inputs['Scale'].default_value = 150
    dn = n.new('ShaderNodeTexNoise'); dn.inputs['Scale'].default_value = 35; l.new(tc.outputs['Generated'], dn.inputs['Vector'])
    vm = n.new('ShaderNodeVectorMath'); vm.operation = 'MULTIPLY_ADD'; vm.inputs[1].default_value = (.02, .02, .02)
    l.new(dn.outputs['Color'], vm.inputs[0]); l.new(tc.outputs['Generated'], vm.inputs[2]); l.new(vm.outputs['Vector'], vor.inputs['Vector'])
    web = n.new('ShaderNodeMapRange'); web.inputs['From Min'].default_value = .0; web.inputs['From Max'].default_value = .05
    web.inputs['To Min'].default_value = .06; web.inputs['To Max'].default_value = 0.0   # едва заметная мягкая сетка
    l.new(vor.outputs['Distance'], web.inputs['Value'])
    p.inputs['Emission Color'].default_value = (.75, .92, 1.0, 1); l.new(web.outputs['Result'], p.inputs['Emission Strength'])
    ob.data.materials.append(m); return ob

def boulder(name, coll, loc, r, color, tint2=None, kind='brain', seed=0, sss=.1):
    bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=4 if PREVIEW else 5, radius=1.0)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free(); smooth(me)
    sq = (r, r * rng.uniform(.85, 1.15), r * (.22 if kind == 'plate' else rng.uniform(.6, .85)))
    ob = new_obj(name, me, coll, loc=loc, rot=(0, 0, rng.uniform(0, 6.28)), scale=sq)
    if kind == 'brain':
        t = bpy.data.textures.new(name + '_t', 'VORONOI'); t.noise_scale = .16 * r; t.weight_1 = 1; t.weight_2 = -1
        displace(ob, t, .34 * r)
    elif kind in ('lumpy', 'plate'):
        displace(ob, tex_clouds(name + '_t', .35 * r, 5), .5 * r)
    else:  # rock
        displace(ob, tex_clouds(name + '_t', .35 * r, 6), .7 * r)
    subsurf(ob, 1)
    if kind in ('lumpy', 'plate'): sss = max(sss, .3)
    ob.data.materials.append(mat(name + '_m', color, rough=.8, sss=sss, bump=.8, bump_scale=16 / r, tint2=tint2, cells=(0 if kind == 'rock' else 60 / r)))
    return ob

def branching(name, coll, loc, h, color, tip, seed=0, thick=.085, trunks=(3, 4)):
    r2 = random.Random(seed)
    cu = bpy.data.curves.new(name, 'CURVE'); cu.dimensions = '3D'; cu.bevel_depth = 1.0
    cu.bevel_resolution = 2 if PREVIEW else 4; cu.fill_mode = 'FULL'; cu.use_fill_caps = True
    def branch(p, d, length, radius, depth):
        sp = cu.splines.new('NURBS'); sp.use_endpoint_u = True; sp.order_u = 3
        cur = Vector(p); dd = Vector(d).normalized(); n = 5; pts = []
        for i in range(n + 1):
            pts.append((cur.copy(), radius * (1 - .55 * i / n)))
            dd = (dd + Vector((r2.uniform(-.3, .3), r2.uniform(-.3, .3), r2.uniform(.05, .25)))).normalized()
            cur = cur + dd * (length / n)
        sp.points.add(len(pts) - 1)
        for k, (v, rr) in enumerate(pts): sp.points[k].co = (v.x, v.y, v.z, 1); sp.points[k].radius = rr
        if depth > 0:
            for _ in range(r2.choice([2, 2, 3])):
                t = r2.uniform(.35, 1.0); base = pts[min(n, int(t * n))][0]
                nd = (dd + Vector((r2.uniform(-1, 1), r2.uniform(-1, 1), r2.uniform(.3, 1)))).normalized()
                branch(base, nd, length * r2.uniform(.55, .75), radius * .62, depth - 1)
    for _ in range(r2.randint(*trunks)):
        branch(loc, (r2.uniform(-.35, .35), r2.uniform(-.35, .35), 1), h * .5, h * thick, 2 if PREVIEW else 3)
    ob = bpy.data.objects.new(name, cu); coll.objects.link(ob)
    m = mat(name + '_m', color, rough=.7, sss=.25, bump=.4, bump_scale=30)
    n = m.node_tree.nodes; l = m.node_tree.links; p = n['Principled BSDF']
    tc = n.new('ShaderNodeTexCoord'); sep = n.new('ShaderNodeSeparateXYZ'); l.new(tc.outputs['Object'], sep.inputs['Vector'])
    mr = n.new('ShaderNodeMapRange'); mr.inputs['From Min'].default_value = loc[2]; mr.inputs['From Max'].default_value = loc[2] + h
    ramp = n.new('ShaderNodeValToRGB'); ramp.color_ramp.elements[0].color = (*color, 1); ramp.color_ramp.elements[1].color = (*tip, 1)
    ramp.color_ramp.elements[0].position = .3
    l.new(sep.outputs['Z'], mr.inputs['Value']); l.new(mr.outputs['Result'], ramp.inputs['Fac']); l.new(ramp.outputs['Color'], p.inputs['Base Color'])
    ob.data.materials.append(m); return ob

def tubes(name, coll, loc, h, color, tint2, n=5, seed=0):
    r2 = random.Random(seed); bm = bmesh.new()
    for i in range(n):
        hh = h * r2.uniform(.55, 1.0); rr = hh * r2.uniform(.09, .13)
        rot = Matrix.Rotation(r2.uniform(-.35, .35), 4, 'X') @ Matrix.Rotation(r2.uniform(-.35, .35), 4, 'Y')
        M = Matrix.Translation((loc[0] + r2.uniform(-.25, .25) * h, loc[1] + r2.uniform(-.25, .25) * h, loc[2] + hh / 2 - .1)) @ rot
        bmesh.ops.create_cone(bm, cap_ends=True, segments=20, radius1=rr, radius2=rr * 1.3, depth=hh, matrix=M)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free(); smooth(me)
    ob = new_obj(name, me, coll)
    displace(ob, tex_clouds(name + '_t', .25, 2), .06); subsurf(ob, 1)
    ob.data.materials.append(mat(name + '_m', color, rough=.85, sss=.3, bump=.6, bump_scale=18, tint2=tint2)); return ob

def anemone(name, coll, loc, r, color, tip, n=140, seed=0):
    r2 = random.Random(seed); bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=24, v_segments=12, radius=r, matrix=Matrix.Translation(loc) @ Matrix.Diagonal((1, 1, .45, 1)))
    up = Vector((0, 0, 1))
    for i in range(n if not PREVIEW else n // 2):
        d = Vector((r2.uniform(-1, 1), r2.uniform(-1, 1), r2.uniform(.25, 1))).normalized()
        base = Vector(loc) + Vector((d.x * r * .9, d.y * r * .9, d.z * r * .4))
        L = r * r2.uniform(.55, .9); tilt = (d + Vector((r2.uniform(-.4, .4), r2.uniform(-.4, .4), r2.uniform(0, .5)))).normalized()
        M = Matrix.Translation(base + tilt * L / 2) @ up.rotation_difference(tilt).to_matrix().to_4x4()
        bmesh.ops.create_cone(bm, cap_ends=True, segments=8, radius1=r * .06, radius2=r * .025, depth=L, matrix=M)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free(); smooth(me)
    ob = new_obj(name, me, coll)
    ob.data.materials.append(mat(name + '_m', color, rough=.5, sss=.5, bump=.15, bump_scale=20, tint2=tip, coat=.2)); return ob

def starfish(name, coll, loc, r, color, rot=0):
    bm = bmesh.new(); vs = []
    for k in range(10):
        a = math.pi * 2 * k / 10 + rot; rr = r if k % 2 == 0 else r * .42
        vs.append(bm.verts.new((loc[0] + rr * math.cos(a), loc[1] + rr * math.sin(a), loc[2])))
    bm.faces.new(vs); me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    ob = new_obj(name, me, coll)
    s = ob.modifiers.new('solid', 'SOLIDIFY'); s.thickness = r * .28; s.offset = 1
    subsurf(ob, 3); smooth(me)
    ob.data.materials.append(mat(name + '_m', color, rough=.8, bump=.9, bump_scale=40, tint2=tuple(c * .7 for c in color))); return ob

def seafan(name, coll, loc, w, h, color, yaw=0):
    bm = bmesh.new(); bmesh.ops.create_grid(bm, x_segments=2, y_segments=2, size=.5)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    ob = new_obj(name, me, coll, loc=(loc[0], loc[1], loc[2] + h / 2), rot=(math.radians(90), 0, yaw), scale=(w, h, 1))
    m = bpy.data.materials.new(name + '_m'); m.use_nodes = True; n = m.node_tree.nodes; l = m.node_tree.links; p = n['Principled BSDF']
    p.inputs['Base Color'].default_value = (*color, 1); p.inputs['Roughness'].default_value = .7
    tc = n.new('ShaderNodeTexCoord'); vor = n.new('ShaderNodeTexVoronoi'); vor.feature = 'DISTANCE_TO_EDGE'
    vor.inputs['Scale'].default_value = 16; l.new(tc.outputs['Generated'], vor.inputs['Vector'])
    nz = n.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 3; l.new(tc.outputs['Generated'], nz.inputs['Vector'])
    lt = n.new('ShaderNodeMath'); lt.operation = 'LESS_THAN'; lt.inputs[1].default_value = .05
    l.new(vor.outputs['Distance'], lt.inputs[0])
    # обрезаем силуэт веера: эллипс по UV (Generated)
    sep = n.new('ShaderNodeSeparateXYZ'); l.new(tc.outputs['Generated'], sep.inputs['Vector'])
    ex = n.new('ShaderNodeMath'); ex.operation = 'SUBTRACT'; ex.inputs[1].default_value = .5; l.new(sep.outputs['X'], ex.inputs[0])
    ey = n.new('ShaderNodeMath'); ey.operation = 'SUBTRACT'; ey.inputs[1].default_value = .45; l.new(sep.outputs['Y'], ey.inputs[0])
    ex2 = n.new('ShaderNodeMath'); ex2.operation = 'MULTIPLY'; l.new(ex.outputs[0], ex2.inputs[0]); l.new(ex.outputs[0], ex2.inputs[1])
    ey2 = n.new('ShaderNodeMath'); ey2.operation = 'MULTIPLY'; l.new(ey.outputs[0], ey2.inputs[0]); l.new(ey.outputs[0], ey2.inputs[1])
    ey2s = n.new('ShaderNodeMath'); ey2s.operation = 'MULTIPLY'; ey2s.inputs[1].default_value = .8; l.new(ey2.outputs[0], ey2s.inputs[0])
    add = n.new('ShaderNodeMath'); add.operation = 'ADD'; l.new(ex2.outputs[0], add.inputs[0]); l.new(ey2s.outputs[0], add.inputs[1])
    nzs = n.new('ShaderNodeMath'); nzs.operation = 'MULTIPLY_ADD'; nzs.inputs[1].default_value = .06; nzs.inputs[2].default_value = .19
    l.new(nz.outputs['Fac'], nzs.inputs[0])
    inside = n.new('ShaderNodeMath'); inside.operation = 'LESS_THAN'; l.new(add.outputs[0], inside.inputs[0]); l.new(nzs.outputs[0], inside.inputs[1])
    alpha = n.new('ShaderNodeMath'); alpha.operation = 'MULTIPLY'; l.new(lt.outputs[0], alpha.inputs[0]); l.new(inside.outputs[0], alpha.inputs[1])
    l.new(alpha.outputs[0], p.inputs['Alpha'])
    ob.data.materials.append(m); return ob

def cauliflower(name, coll, loc, r, color, tint2, n=42, seed=0):
    r2 = random.Random(seed); bm = bmesh.new()
    for i in range(n):
        d = Vector((r2.uniform(-1, 1), r2.uniform(-1, 1), r2.uniform(.1, 1))).normalized() * r * r2.uniform(.3, .85)
        rr = r * r2.uniform(.22, .34)
        bmesh.ops.create_icosphere(bm, subdivisions=3, radius=rr, matrix=Matrix.Translation((loc[0] + d.x, loc[1] + d.y, loc[2] + d.z * .8)))
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free(); smooth(me)
    ob = new_obj(name, me, coll)
    displace(ob, tex_clouds(name + '_t', .12 * r, 3), .12 * r); subsurf(ob, 1)
    ob.data.materials.append(mat(name + '_m', color, rough=.7, sss=.4, bump=.6, bump_scale=40 / r, tint2=tint2, cells=60 / r)); return ob

def sponge_ball(name, coll, loc, r, color, tint2, seed=0):
    bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=4 if PREVIEW else 5, radius=r)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free(); smooth(me)
    ob = new_obj(name, me, coll, loc=loc, rot=(0, 0, seed))
    t = bpy.data.textures.new(name + '_t', 'VORONOI'); t.noise_scale = .55 * r; t.weight_1 = 1
    displace(ob, t, .5 * r, 'LOCAL'); subsurf(ob, 1)
    ob.data.materials.append(mat(name + '_m', color, rough=.6, sss=.35, bump=.5, bump_scale=30 / r, tint2=tint2, cells=45 / r)); return ob

def pebbles(name, coll, n, area, seed=0):
    r2 = random.Random(seed); bm = bmesh.new()
    for i in range(n):
        r = r2.uniform(.05, .16); x = r2.uniform(area[0], area[1]); y = r2.uniform(area[2], area[3])
        M = Matrix.Translation((x, y, r * .35)) @ Matrix.Diagonal((1, r2.uniform(.7, 1.3), r2.uniform(.5, .8), 1)) @ Matrix.Rotation(r2.uniform(0, 6.28), 4, 'Z')
        bmesh.ops.create_icosphere(bm, subdivisions=2, radius=r, matrix=M)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free(); smooth(me)
    ob = new_obj(name, me, coll)
    ob.data.materials.append(mat(name + '_m', (.42, .38, .3), rough=.9, bump=.4, bump_scale=30, tint2=(.28, .25, .2))); return ob

# ---------------------------------------------------------------- сцена
sand(BG)
# скальная стена слева (задник) и камни
for i, (x, y, z, r) in enumerate([(-5.2, 1.5, .6, 2.4), (-4.4, 2.8, 2.4, 2.1), (-5.0, 1.0, 3.9, 1.7), (-3.6, 4.5, 1.0, 2.2), (-6.0, 4.0, 4.6, 1.9)]):
    boulder(f'wall{i}', BG, (x, y, z), r, (.26, .24, .2), tint2=(.42, .28, .45), kind='rock', seed=i)
for i, (x, y, z, r) in enumerate([(4.6, 5.5, .8, 2.3), (1.5, 6.5, 1.0, 2.6), (-1.5, 7.0, .8, 2.2), (6.2, 3.5, .5, 1.8)]):
    boulder(f'rock{i}', BG, (x, y, z), r, (.24, .23, .2), tint2=(.38, .26, .4), kind='rock', seed=10 + i)
# кораллы-мозговики / мягкие — насыщенная палитра LMA2
boulder('brain_pink', BG, (-2.3, 1.0, .55), 1.15, (.92, .42, .36), tint2=(.7, .25, .25), kind='brain', seed=20)
boulder('brain_green', BG, (1.9, 1.8, .5), 1.0, (.45, .68, .25), tint2=(.25, .45, .15), kind='brain', seed=21)
boulder('soft_purple', BG, (.2, 3.0, .7), 1.4, (.5, .25, .65), tint2=(.3, .12, .45), kind='lumpy', seed=22)
boulder('soft_white', BG, (-.9, 1.6, .5), .9, (.92, .9, .82), tint2=(.72, .75, .68), kind='lumpy', seed=23, sss=.3)
boulder('brain_blue', BG, (3.6, 3.2, .6), 1.2, (.35, .55, .8), tint2=(.2, .35, .6), kind='brain', seed=24)
boulder('brain_yellow', BG, (-1.2, 4.8, 1.2), 1.3, (.9, .7, .2), tint2=(.6, .45, .12), kind='brain', seed=25)
boulder('brain_orange', BG, (-.2, 1.9, .45), .85, (.95, .5, .2), tint2=(.75, .3, .1), kind='brain', seed=26)
boulder('soft_magenta', BG, (2.7, 2.4, .6), 1.0, (.85, .25, .6), tint2=(.6, .12, .45), kind='lumpy', seed=27)
boulder('brain_red', BG, (-2.9, 2.9, 1.5), .9, (.85, .2, .15), tint2=(.55, .1, .1), kind='brain', seed=28)
# ветвистые
branching('stag_pink', BG, (-.6, .4, .05), 1.7, (.95, .45, .55), (.98, .88, .9), seed=30)
branching('stag_cream', BG, (2.9, .8, .05), 1.5, (.85, .78, .55), (.98, .96, .85), seed=31)
branching('stag_orange', BG, (4.4, 2.6, .05), 2.1, (.95, .5, .2), (1, .85, .6), seed=32)
branching('stag_blue', BG, (-3.2, 3.6, 2.6), 1.4, (.55, .7, .9), (.9, .95, 1), seed=33)
# губки, актиния, веера
tubes('tube_yellow', BG, (4.2, 1.2, 0), 2.0, (.95, .72, .15), (.7, .5, .1), n=6, seed=40)
tubes('tube_orange', BG, (1.0, 4.2, 0), 1.6, (.95, .42, .12), (.7, .28, .08), n=4, seed=41)
tubes('tube_red', BG, (-1.8, 2.6, 0), 1.3, (.85, .2, .15), (.6, .12, .1), n=4, seed=42)
anemone('anemone2', BG, (2.2, .3, .1), .5, (.95, .5, .35), (1, .8, .7), seed=43)
seafan('fan_red', BG, (-3.9, 3.4, 3.1), 2.0, 1.8, (.85, .25, .2), yaw=.35)
seafan('fan_orange', BG, (4.3, 2.4, 1.9), 1.5, 1.4, (.95, .6, .2), yaw=-.6)
pebbles('pebbles', BG, 14, (-6, 6, -1, 4), seed=50)
sponge_ball('sponge_bg', BG, (3.0, 2.0, .6), .6, (.95, .62, .14), (.7, .42, .06), seed=2)
# крупные формы как в LMA2: пилон с жёлтыми губками справа, розовая «капуста» и белый ветвистый в центре, жёлтый кринoид слева
boulder('pillar_right', BG, (5.0, 1.6, 1.4), 1.6, (.26, .24, .2), tint2=(.42, .28, .45), kind='rock', seed=36)
tubes('tube_yellow_top', BG, (5.0, 1.4, 2.2), 2.2, (.95, .72, .15), (.7, .5, .1), n=7, seed=44)
boulder('plate_orange', BG, (-3.4, .6, 1.3), 1.1, (.95, .55, .2), tint2=(.7, .35, .1), kind='plate', seed=29)
cauliflower('cauli_pink', BG, (-1.0, .2, .3), 1.25, (.98, .55, .5), (.85, .35, .35), seed=70)
branching('stag_white', BG, (-.3, 1.6, .05), 2.3, (.93, .92, .86), (1, 1, .97), seed=34, thick=.07)
branching('crinoid_yellow', BG, (-3.8, .0, .05), 1.7, (.95, .8, .15), (1, .95, .5), seed=35, thick=.012, trunks=(10, 14))
# передний план — рыбы проходят ЗА этим
boulder('fg_orange', FG, (-3.2, -1.8, .35), .8, (.95, .45, .2), tint2=(.75, .28, .12), kind='lumpy', seed=60)
anemone('anemone', FG, (.5, -1.3, .12), .7, (.98, .52, .36), (1, .78, .62), seed=61)
tubes('tube_purple', FG, (3.9, -1.9, 0), 1.3, (.45, .25, .85), (.3, .15, .6), n=5, seed=62)
starfish('star', FG, (2.6, -2.4, .02), .55, (.95, .5, .2), rot=.4)
boulder('fg_rock', FG, (1.6, -2.6, .15), .45, (.25, .25, .22), tint2=(.18, .25, .18), kind='rock', seed=63)
boulder('fg_green', FG, (-1.4, -2.2, .25), .55, (.4, .65, .25), tint2=(.25, .45, .15), kind='brain', seed=64)
sponge_ball('sponge_fg', FG, (1.4, -1.1, .55), .55, (.95, .6, .12), (.7, .4, .06), seed=1)

for m in bpy.data.materials: add_fog(m)

# ---------------------------------------------------------------- свет, вода, камера
w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True; n = w.node_tree.nodes; l = w.node_tree.links
bg = n['Background']; tc = n.new('ShaderNodeTexCoord'); sep = n.new('ShaderNodeSeparateXYZ'); l.new(tc.outputs['Generated'], sep.inputs['Vector'])
mr = n.new('ShaderNodeMapRange'); mr.inputs['From Min'].default_value = -.4; mr.inputs['From Max'].default_value = .9
ramp = n.new('ShaderNodeValToRGB'); e = ramp.color_ramp.elements
e[0].color = (.01, .05, .18, 1); e[0].position = 0; e[1].color = (.16, .55, .9, 1); e[1].position = 1
mid = ramp.color_ramp.elements.new(.45); mid.color = (.03, .18, .5, 1)
l.new(sep.outputs['Z'], mr.inputs['Value']); l.new(mr.outputs['Result'], ramp.inputs['Fac']); l.new(ramp.outputs['Color'], bg.inputs['Color'])
bg.inputs['Strength'].default_value = .35

target = new_obj('target', None, sc.collection, loc=(.2, 1.0, 1.7))
def light(name, typ, loc, energy, color, size=6):
    d = bpy.data.lights.new(name, typ); d.energy = energy; d.color = color
    if typ == 'AREA': d.size = size
    if typ == 'SUN': d.angle = .03
    o = new_obj(name, d, sc.collection, loc=loc)
    c = o.constraints.new('TRACK_TO'); c.target = target; c.track_axis = 'TRACK_NEGATIVE_Z'; c.up_axis = 'UP_Y'; return o
light('sun', 'SUN', (2, 4, 12), 5.0, (.85, .95, 1))
light('fill', 'AREA', (-4, -9, 5), 60, (.6, .8, 1), 10)
light('rim', 'AREA', (5, 8, 6), 300, (.5, .85, 1), 8)

cd = bpy.data.cameras.new('cam'); cd.lens = 28; cd.sensor_width = 36
cam = new_obj('cam', cd, sc.collection, loc=(.3, -7.2, 1.4))
c = cam.constraints.new('TRACK_TO'); c.target = target; c.track_axis = 'TRACK_NEGATIVE_Z'; c.up_axis = 'UP_Y'
sc.camera = cam

sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = SAMPLES; sc.cycles.use_denoising = True
sc.cycles.use_adaptive_sampling = True; sc.cycles.max_bounces = 6
sc.render.resolution_x = RES; sc.render.resolution_y = int(RES / ASPECT); sc.render.resolution_percentage = 100
sc.view_settings.view_transform = 'Standard'; sc.view_settings.look = 'None'
os.makedirs(OUT, exist_ok=True)

import time; t = time.time()
if 'bg' in LAYERS:
    # слой 1: задник (без переднего плана)
    for o in FG.objects: o.hide_render = True
    sc.render.film_transparent = False
    sc.render.image_settings.file_format = 'JPEG'; sc.render.image_settings.quality = 92; sc.render.image_settings.color_mode = 'RGB'
    sc.render.filepath = os.path.join(OUT, 'reef_bg.jpg'); bpy.ops.render.render(write_still=True)
    print(f'OK reef_bg {time.time() - t:.0f}s', flush=True); t = time.time()
if 'fg' in LAYERS:
    # слой 2: передний план поверх «дырок» (задник как holdout — перекрывает и отбрасывает тени)
    for o in FG.objects: o.hide_render = False
    for o in BG.objects: o.is_holdout = True
    sc.render.film_transparent = True
    sc.render.image_settings.file_format = 'PNG'; sc.render.image_settings.color_mode = 'RGBA'
    sc.render.filepath = os.path.join(OUT, 'reef_fg.png'); bpy.ops.render.render(write_still=True)
    print(f'OK reef_fg {time.time() - t:.0f}s', flush=True)
if '--blend' in sys.argv: bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, 'reef.blend'))

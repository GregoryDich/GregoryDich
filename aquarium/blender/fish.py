#!/usr/bin/env python3
"""
Параметрический генератор рифовых рыб (Blender 4.2+/5.x как Python-модуль `bpy`).

Тело — лофт эллипсов по аналитическому профилю (эллипс с разными показателями
вперёд/назад + сужение в хвостовой стебель), плавники — тонкие полигоны с
Solidify и рельефом лучей, глаз — сферы. Окрас печётся numpy'ем в текстуру
(градиент спина→брюхо, полосы, пятна, области), рендер Cycles → прозрачный PNG
носом ВПРАВО — готовый спрайт для aquarium/index.html.

  python3 fish.py --out ../fish                              # все виды
  python3 fish.py --out ../fish --only clownfish --samples 64 --res 1000
  --blend  — дополнительно сохранить .blend каждой рыбы (открыть в Blender)
"""
import sys, os, math
import numpy as np
import bpy, bmesh

def arg(name, default, cast=str):
    return cast(sys.argv[sys.argv.index(name) + 1]) if name in sys.argv else default

OUT = arg('--out', 'out'); ONLY = arg('--only', None); SAMPLES = arg('--samples', 128, int)
RES = arg('--res', 1400, int); SAVE_BLEND = '--blend' in sys.argv
ONLY = ONLY.split(',') if ONLY else None
TAU = math.tau

# ---------------------------------------------------------------- профили тела
# H/W — макс. полувысота/полуширина (длина тела = 1); c — где пик; wb/wf — полуоси эллипса
# назад/вперёд; eb/ef — показатели (0.5 эллипс, меньше — острее, больше — «квадратнее»);
# ped — толщина хвостового стебля (доля), tap — длина сужения. w* — то же для ширины.
# tail: (длина, размах) по умолчанию для типа тела.
BODY = {
    'oval':  dict(H=.24, W=.13, c=.47, wb=.50, wf=.57, eb=.55, ef=.50, ped=.34, tap=.26, wc=.42, wwb=.46, wwf=.62, we=.60, tail=(.24, .20)),
    'disc':  dict(H=.30, W=.11, c=.46, wb=.49, wf=.545, eb=.60, ef=.42, ped=.16, tap=.24, wc=.42, wwb=.46, wwf=.62, we=.60, tail=(.20, .26)),
    'round': dict(H=.31, W=.22, c=.50, wb=.54, wf=.55, eb=.70, ef=.60, ped=.26, tap=.22, wc=.45, wwb=.50, wwf=.60, we=.70, tail=(.22, .22)),
    'small': dict(H=.22, W=.12, c=.46, wb=.50, wf=.57, eb=.55, ef=.50, ped=.30, tap=.26, wc=.42, wwb=.46, wwf=.62, we=.60, tail=(.22, .17)),
}

def profile(u, c, wb, wf, eb, ef, ped, tap):
    w = wb if u < c else wf; e = eb if u < c else ef
    core = max(0.0, 1 - ((u - c) / w) ** 2) ** e
    t = min(1.0, max(0.0, u / tap)); taper = ped + (1 - ped) * (t * t * (3 - 2 * t))
    return core * taper

# ---------------------------------------------------------------- виды
# patterns: ('bands', centers_v(число или (v, выступ)), width, color, edge_color|None, edge_w)
#           ('hstripes', count, width_frac, color)       — полосы вокруг тела (по высоте)
#           ('spots', n, r, color, 'lower'|'upper'|'all', seed)
#           ('region', v0, v1, t0, t1, color, soft)      — область: v вдоль тела, t 0=брюхо..1=спина
#           ('bicolor', split_v, color, soft, slant, 'rear'|'front')
#           ('wavy', count, width, color, edge, amp)
SPECIES = {
    'clownfish': dict(body='oval', back=(.93,.33,.03), belly=(1,.60,.22),
        patterns=[('bands',[.11,(.46,.05),.79],.10,(.98,.98,.96),(.03,.02,.02),.014)],
        fin=(.98,.45,.08), fin_edge=(.06,.03,.02), tail='rounded', dorsal=('hump',.07), anal=('hump',.05)),
    'blue_tang': dict(body='disc', back=(.04,.20,.80), belly=(.20,.45,.95),
        patterns=[('ellipse',.52,.74,.44,.34,(.03,.03,.06),.15), ('ellipse',.46,.70,.20,.15,(.10,.35,.95),.2)],
        fin=(.05,.20,.80), fin_edge=(.02,.02,.05), tail='lunate', tail_color=(.98,.80,.10), tail_edge=(.03,.03,.05),
        pectoral=(.98,.80,.10), dorsal=('sail',.12), anal=('sail',.10)),
    'yellow_tang': dict(body='disc', Hs=1.0, back=(1,.80,.04), belly=(1,.88,.25),
        patterns=[('region',.02,.09,.40,.60,(.98,.98,.95),.01)],
        fin=(1,.82,.06), fin_edge=(.85,.6,.02), tail='truncate', dorsal=('sail',.16), anal=('sail',.13)),
    'powder_blue_tang': dict(body='disc', back=(.25,.55,.90), belly=(.55,.80,.98),
        patterns=[('ellipse',.72,.12,.16,.22,(.95,.97,1),.2), ('region',.80,1,0,1,(.04,.04,.08),.03)],
        fin=(.98,.82,.10), fin_edge=(.05,.05,.1), tail='truncate', tail_color=(.95,.97,1), tail_edge=(.05,.05,.1),
        pectoral=(.98,.82,.10), dorsal=('sail',.13), anal=('sail',.11), anal_color=(.95,.97,1)),
    'pufferfish': dict(body='round', Ws=1.1, back=(.12,.09,.06), belly=(.10,.08,.06),   # спинорог-клоун
        patterns=[('ellipse',.55,.88,.32,.28,(.95,.70,.10),.2), ('spots',30,.02,(.22,.13,.05),'upper',3),
                  ('spots',28,.07,(.97,.96,.92),'lower',7), ('region',.94,1,0,1,(.95,.75,.15),.02)],
        fin=(.15,.10,.06), fin_edge=(.95,.75,.15), tail='truncate', dorsal=('hump',.10), dorsal_u=(.55,.86),
        anal=('hump',.09), anal_u=(.55,.86)),
    'royal_gramma': dict(body='small', back=(.55,.10,.75), belly=(.75,.35,.90),
        patterns=[('bicolor',.45,(1,.75,.05),.05,-.15,'rear')],
        fin=(.80,.45,.65), fin_edge=(.9,.7,.2), tail='rounded', tail_color=(1,.78,.10), dorsal=('long',.07), anal=('hump',.05)),
    'emperor_angelfish': dict(body='disc', Hs=1.12, back=(.08,.28,.68), belly=(.15,.40,.80),
        patterns=[('hstripes',9,.45,(.98,.85,.15)), ('ellipse',.86,.6,.12,.3,(.05,.06,.15),.2)],
        fin=(.10,.30,.70), fin_edge=(.98,.85,.15), tail='truncate', tail_color=(.98,.80,.12), dorsal=('sail',.13), anal=('sail',.11)),
    'regal_angelfish': dict(body='disc', Hs=1.05, back=(1,.60,.10), belly=(1,.78,.40),
        patterns=[('bands',[.18,.36,.54,.72,.90],.075,(.98,.97,.92),(.10,.15,.55),.016)],
        fin=(1,.62,.12), fin_edge=(.1,.15,.55), tail='truncate', tail_color=(.98,.80,.12), dorsal=('sail',.13),
        anal=('sail',.11), anal_color=(.2,.3,.75)),
    'mandarinfish': dict(body='small', Hs=1.1, Ws=1.4, back=(.10,.55,.40), belly=(.30,.70,.55),
        patterns=[('wavy',6,.05,(.98,.50,.10),(.10,.35,.85),.05)],
        fin=(.95,.5,.15), fin_edge=(.1,.35,.85), tail='rounded', dorsal=('hump',.09), anal=('hump',.07), pectoral_r=.2),
    'blue_chromis': dict(body='small', back=(.15,.45,.95), belly=(.45,.75,1),
        patterns=[], fin=(.35,.6,1), fin_edge=(.15,.3,.8), tail='forked', dorsal=('long',.06), anal=('hump',.05)),
    'flame_angel': dict(body='oval', Hs=1.1, back=(.92,.22,.05), belly=(1,.50,.20),
        patterns=[('bands',[.32,.44,.56,.68],.045,(.15,.05,.05),None,0)],
        fin=(.95,.30,.08), fin_edge=(.2,.35,.9), tail='rounded', dorsal=('long',.09), anal=('hump',.07)),
    'moorish_idol': dict(body='disc', Hs=1.6, Ws=.8, back=(.95,.95,.90), belly=(.98,.98,.95),
        patterns=[('ellipse',.51,.8,.14,.3,(.98,.82,.10),.2), ('bands',[.30,.75],.20,(.05,.05,.06),None,0)],
        fin=(.95,.95,.9), fin_edge=(.05,.05,.06), tail='truncate', tail_color=(.05,.05,.06), dorsal=('long',.35), anal=('sail',.10)),
    'bicolor_angel': dict(body='disc', Hs=.8, back=(.98,.8,.1), belly=(1,.86,.3),
        patterns=[('bicolor',.5,(.12,.22,.78),.03,0,'rear'), ('region',.80,.9,.5,1,(.12,.22,.78),.02)],
        fin=(.15,.25,.8), fin_edge=(.05,.1,.5), tail='truncate', tail_color=(.98,.85,.15), tail_edge=(.9,.7,.1), dorsal=('sail',.12), anal=('sail',.10)),
    'spanish_hogfish': dict(body='oval', Hs=1.05, back=(.8,.15,.35), belly=(.98,.8,.2),
        patterns=[('region',0,1,.55,1,(.8,.15,.35),.05)],
        fin=(.98,.75,.2), fin_edge=(.9,.5,.1), tail='forked', tail_color=(.98,.85,.15), dorsal=('long',.10), anal=('hump',.07)),
}

# ---------------------------------------------------------------- текстура окраса
def bake_texture(name, spec, W=1024, H=1024):
    u = (np.arange(W) + .5) / W; v = (np.arange(H) + .5) / H
    U, V = np.meshgrid(u, v)                       # (H, W); u: 0 брюхо .25 ближний бок .5 спина; v: 0 хвост..1 нос
    tb = (1 - np.cos(TAU * U)) / 2                  # 0 брюхо → 1 спина
    col = lambda c: np.array(c, dtype=np.float32)
    k = np.clip(tb, 0, 1) ** .75
    img = col(spec['belly'])[None, None] * (1 - k[..., None]) + col(spec['back'])[None, None] * k[..., None]
    def smooth(x, e0, e1):
        t = np.clip((x - e0) / (e1 - e0 + 1e-9), 0, 1); return t * t * (3 - 2 * t)
    def paint(mask, color):
        nonlocal img
        img = img * (1 - mask[..., None]) + col(color)[None, None] * mask[..., None]
    for pat in spec.get('patterns', []):
        kind = pat[0]
        if kind == 'bands':
            _, centers, width, color, ecol, ew = pat
            for c in centers:
                c, bulge = (c if isinstance(c, tuple) else (c, 0.0))
                d = np.abs(V - (c + bulge * (1 - np.abs(2 * tb - 1))))
                if ecol: paint(smooth(d, width/2 - .012, width/2 + .012) * (1 - smooth(d, width/2 + ew - .012, width/2 + ew + .012)), ecol)
                paint(1 - smooth(d, width/2 - .012, width/2 + .012), color)
        elif kind == 'hstripes':
            _, count, wf, color = pat
            s = np.abs(((tb * count) % 1.0) - .5) * 2
            paint((1 - smooth(s, wf - .06, wf + .06)) * (1 - smooth(np.abs(V - .5), .36, .42)), color)
        elif kind == 'spots':
            _, n, r, color, region, seed = pat
            rng = np.random.default_rng(seed); mask = np.zeros_like(U)
            for _ in range(n * 8):
                cu, cv = rng.uniform(0, 1), rng.uniform(.12, .9)
                t = (1 - math.cos(TAU * cu)) / 2
                if region == 'lower' and t > .48: continue
                if region == 'upper' and t < .55: continue
                rr = r * rng.uniform(.65, 1.0)
                du = np.minimum(np.abs(U - cu), 1 - np.abs(U - cu)) * 1.9
                d = np.sqrt(du * du + (V - cv) ** 2)
                mask = np.maximum(mask, 1 - smooth(d, rr - .012, rr + .012)); n -= 1
                if n <= 0: break
            paint(mask, color)
        elif kind == 'ellipse':                       # (cv, ct, rv, rt, color, soft) — органичное пятно
            _, cv, ct, rv, rt, color, soft = pat
            q = ((V - cv) / rv) ** 2 + ((tb - ct) / rt) ** 2
            paint(1 - smooth(q, 1 - soft, 1 + soft), color)
        elif kind == 'region':
            _, v0, v1, t0, t1, color, soft = pat
            m = smooth(V, v0 - soft, v0 + soft) * (1 - smooth(V, v1 - soft, v1 + soft)) * \
                smooth(tb, t0 - soft, t0 + soft) * (1 - smooth(tb, t1 - soft, t1 + soft))
            paint(m, color)
        elif kind == 'bicolor':
            _, split, color, soft, slant, side = pat
            edge = split + slant * (tb - .5); m = smooth(V, edge - soft, edge + soft)
            paint(m if side == 'front' else 1 - m, color)
        elif kind == 'wavy':
            _, count, width, color, ecol, amp = pat
            for i in range(count):
                c = .12 + .76 * i / max(1, count - 1)
                d = np.abs(V - (c + amp * np.sin(TAU * 3 * U + c * 13)))
                if ecol: paint(smooth(d, width/2 - .004, width/2 + .004) * (1 - smooth(d, width/2 + .014, width/2 + .022)), ecol)
                paint(1 - smooth(d, width/2 - .004, width/2 + .004), color)
    rgba = np.concatenate([np.clip(img, 0, 1), np.ones((H, W, 1), np.float32)], -1).astype(np.float32)
    im = bpy.data.images.new(name + '_skin', W, H, alpha=True)
    im.colorspace_settings.name = 'sRGB'
    im.pixels.foreach_set(rgba.ravel())
    try: im.pack()
    except Exception: pass
    return im

# ---------------------------------------------------------------- геометрия
def link(ob):
    bpy.context.scene.collection.objects.link(ob); return ob

def build_body(spec, R=80, S=48):
    b = BODY[spec['body']]; H = b['H'] * spec.get('Hs', 1); W = b['W'] * spec.get('Ws', 1)
    ph = lambda u: H * profile(u, b['c'], b['wb'], b['wf'], b['eb'], b['ef'], b['ped'], b['tap'])
    pw = lambda u: W * profile(u, b['wc'], b['wwb'], b['wwf'], b['we'], b['we'], .5, .2)
    droop = lambda u: -H * .10 * max(0.0, (u - .72) / .28) ** 2      # нос чуть вниз — «прикус»
    bm = bmesh.new(); uv = bm.loops.layers.uv.new('UVMap'); rings = []
    for i in range(R + 1):
        u = i / R; x = -.5 + u; hh, ww = ph(u), pw(u); ring = []
        for j in range(S):
            phi = TAU * j / S; c, s = math.cos(phi), math.sin(phi)
            ring.append(bm.verts.new((x, -s * ww, -c * hh * (1.07 if c > 0 else 1.0) + droop(u))))
        rings.append(ring)
    tail_v = bm.verts.new((-.505, 0, 0)); nose_v = bm.verts.new((.508, 0, droop(1)))
    def setuv(f, uvs):
        for l, (a, bb) in zip(f.loops, uvs): l[uv].uv = (a, bb)
    for i in range(R):
        for j in range(S):
            f = bm.faces.new((rings[i][j], rings[i][(j+1) % S], rings[i+1][(j+1) % S], rings[i+1][j]))
            setuv(f, [(j/S, i/R), ((j+1)/S, i/R), ((j+1)/S, (i+1)/R), (j/S, (i+1)/R)])
    for j in range(S):
        f = bm.faces.new((tail_v, rings[0][(j+1) % S], rings[0][j])); setuv(f, [((j+.5)/S, 0), ((j+1)/S, 0), (j/S, 0)])
        f = bm.faces.new((nose_v, rings[R][j], rings[R][(j+1) % S])); setuv(f, [((j+.5)/S, 1), (j/S, 1), ((j+1)/S, 1)])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new('body'); bm.to_mesh(me); bm.free()
    for p in me.polygons: p.use_smooth = True
    ob = link(bpy.data.objects.new('body', me))
    m = ob.modifiers.new('subd', 'SUBSURF'); m.levels = 1; m.render_levels = 2
    return ob, ph, pw, H, W, b

def fin_object(name, pts, loc=(0, 0, 0), rot=(0, 0, 0), thick=.012):
    bm = bmesh.new(); vs = [bm.verts.new((x, 0, z)) for (x, z) in pts]
    f = bm.faces.new(vs); bmesh.ops.triangulate(bm, faces=[f])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    ob = link(bpy.data.objects.new(name, me)); ob.location = loc; ob.rotation_euler = rot
    s = ob.modifiers.new('solid', 'SOLIDIFY'); s.thickness = thick; s.offset = 0
    return ob

def tail_pts(kind, T, spread, base):
    x0, xt = -.47, -.5 - T
    if kind == 'rounded':
        pts = [(x0, base), (xt + T*.30, spread)]
        for k in range(1, 8):
            a = 1 - 2*k/8; pts.append((xt + T*.22*a*a, spread*a*.98))
        return pts + [(xt + T*.30, -spread), (x0, -base)]
    if kind == 'forked':  return [(x0, base), (xt + T*.1, spread), (xt, spread*.9), (xt + T*.45, .03), (xt + T*.45, -.03), (xt, -spread*.9), (xt + T*.1, -spread), (x0, -base)]
    if kind == 'lunate':  return [(x0, base), (xt - T*.05, spread), (xt + T*.15, spread*.55), (xt + T*.35, 0), (xt + T*.15, -spread*.55), (xt - T*.05, -spread), (x0, -base)]
    return [(x0, base), (xt + T*.05, spread), (xt, spread*.85), (xt - T*.02, 0), (xt, -spread*.85), (xt + T*.05, -spread), (x0, -base)]  # truncate

def rim_pts(ph, u0, u1, h, shape, sign=1, n=20):
    base, top = [], []
    for k in range(n + 1):
        s = k / n; u = u0 + (u1 - u0) * s; x = -.5 + u
        if shape == 'hump':   fh = h * math.sin(math.pi * s) ** .6
        elif shape == 'long': fh = h * min(1, s * 3.5) ** .7 * (1 - .45 * s)
        else:                 fh = h * (1 - (1 - s) ** 2.2) * (1 - .15 * max(0, s - .8) / .2)   # sail
        base.append((x, sign * ph(u) * .9)); top.append((x, sign * (ph(u) + fh)))
    return base + top[::-1]

def pectoral_pts(r, n=18):                         # округлая лопатка, крепится у нуля, тянется назад
    return [(-r * .55 + r * .6 * math.cos(TAU * k / n), r * .32 * math.sin(TAU * k / n)) for k in range(n)]

def sphere(name, r, loc, seg=32):
    bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=seg // 2, radius=r)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    for p in me.polygons: p.use_smooth = True
    ob = link(bpy.data.objects.new(name, me)); ob.location = loc; return ob

# ---------------------------------------------------------------- материалы
def body_material(img):
    m = bpy.data.materials.new('skin'); m.use_nodes = True; n = m.node_tree.nodes; l = m.node_tree.links
    p = n['Principled BSDF']
    tex = n.new('ShaderNodeTexImage'); tex.image = img; tex.interpolation = 'Cubic'
    # живая кожа: лёгкая пятнистость цвета + чешуйки (ячейки Вороного), матово-влажная, без «пластика»
    tc = n.new('ShaderNodeTexCoord')
    mot = n.new('ShaderNodeTexNoise'); mot.inputs['Scale'].default_value = 5; mot.inputs['Detail'].default_value = 4
    l.new(tc.outputs['Object'], mot.inputs['Vector'])
    mmap = n.new('ShaderNodeMapRange'); mmap.inputs['From Min'].default_value = .3; mmap.inputs['From Max'].default_value = .7
    mmap.inputs['To Min'].default_value = .86; mmap.inputs['To Max'].default_value = 1.1; l.new(mot.outputs['Fac'], mmap.inputs['Value'])
    vor = n.new('ShaderNodeTexVoronoi'); vor.feature = 'DISTANCE_TO_EDGE'; vor.inputs['Scale'].default_value = 90
    l.new(tc.outputs['Object'], vor.inputs['Vector'])
    vmap = n.new('ShaderNodeMapRange'); vmap.inputs['From Min'].default_value = 0; vmap.inputs['From Max'].default_value = .04
    vmap.inputs['To Min'].default_value = .84; vmap.inputs['To Max'].default_value = 1.0; l.new(vor.outputs['Distance'], vmap.inputs['Value'])
    s1 = n.new('ShaderNodeVectorMath'); s1.operation = 'SCALE'; l.new(tex.outputs['Color'], s1.inputs[0]); l.new(mmap.outputs['Result'], s1.inputs['Scale'])
    s2 = n.new('ShaderNodeVectorMath'); s2.operation = 'SCALE'; l.new(s1.outputs['Vector'], s2.inputs[0]); l.new(vmap.outputs['Result'], s2.inputs['Scale'])
    l.new(s2.outputs['Vector'], p.inputs['Base Color'])
    p.inputs['Roughness'].default_value = .5; p.inputs['Subsurface Weight'].default_value = .25
    p.inputs['Subsurface Radius'].default_value = (.04, .015, .008)
    p.inputs['Coat Weight'].default_value = .12; p.inputs['Coat Roughness'].default_value = .2
    p.inputs['Specular IOR Level'].default_value = .35
    bump = n.new('ShaderNodeBump'); bump.inputs['Strength'].default_value = .18; bump.inputs['Distance'].default_value = .01
    l.new(vor.outputs['Distance'], bump.inputs['Height']); l.new(bump.outputs['Normal'], p.inputs['Normal'])
    return m

def fin_material(name, color, edge, axis='X', edge_at_zero=True, alpha=1.0):
    """axis — вдоль какой оси Generated плавник вытянут (там край/кончик); лучи идут вдоль неё."""
    m = bpy.data.materials.new(name); m.use_nodes = True; n = m.node_tree.nodes; l = m.node_tree.links
    p = n['Principled BSDF']; out = n['Material Output']
    p.inputs['Roughness'].default_value = .75; p.inputs['Coat Weight'].default_value = .0; p.inputs['Specular IOR Level'].default_value = .1   # без блика — плавник не белеет
    tc = n.new('ShaderNodeTexCoord'); sep = n.new('ShaderNodeSeparateXYZ'); l.new(tc.outputs['Generated'], sep.inputs['Vector'])
    rc = n.new('ShaderNodeValToRGB'); ra = n.new('ShaderNodeValToRGB')
    l.new(sep.outputs[axis], rc.inputs['Fac']); l.new(sep.outputs[axis], ra.inputs['Fac'])
    color = tuple(c * .88 for c in color); e = edge or color
    c0, c1 = ((e, color) if edge_at_zero else (color, e))
    a0, a1 = ((.55, .85) if edge_at_zero else (.85, .55))   # полупрозрачные к краю, как настоящие
    rc.color_ramp.elements[0].color = (*c0, 1); rc.color_ramp.elements[1].color = (*c1, 1)
    rc.color_ramp.elements[0].position = .0 if edge_at_zero else .4; rc.color_ramp.elements[1].position = .6 if edge_at_zero else 1.0
    ra.color_ramp.elements[0].color = (a0,) * 3 + (1,); ra.color_ramp.elements[1].color = (a1,) * 3 + (1,)
    l.new(rc.outputs['Color'], p.inputs['Base Color'])
    mul = n.new('ShaderNodeMath'); mul.operation = 'MULTIPLY'; mul.inputs[1].default_value = alpha
    l.new(ra.outputs['Color'], mul.inputs[0]); l.new(mul.outputs[0], p.inputs['Alpha'])
    wave = n.new('ShaderNodeTexWave'); wave.wave_type = 'BANDS'; wave.bands_direction = 'Z' if axis == 'X' else 'X'
    wave.inputs['Scale'].default_value = 26; wave.inputs['Distortion'].default_value = .8
    l.new(tc.outputs['Generated'], wave.inputs['Vector'])
    bump = n.new('ShaderNodeBump'); bump.inputs['Strength'].default_value = .35; bump.inputs['Distance'].default_value = .02
    l.new(wave.outputs['Fac'], bump.inputs['Height']); l.new(bump.outputs['Normal'], p.inputs['Normal'])
    tr = n.new('ShaderNodeBsdfTranslucent'); tr.inputs['Color'].default_value = (*color, 1)
    mix = n.new('ShaderNodeMixShader'); mix.inputs['Fac'].default_value = .0
    l.new(p.outputs['BSDF'], mix.inputs[1]); l.new(tr.outputs['BSDF'], mix.inputs[2]); l.new(mix.outputs['Shader'], out.inputs['Surface'])
    return m

def plain_material(name, color, rough=.2, coat=1.0):
    m = bpy.data.materials.new(name); m.use_nodes = True; p = m.node_tree.nodes['Principled BSDF']
    p.inputs['Base Color'].default_value = (*color, 1); p.inputs['Roughness'].default_value = rough
    p.inputs['Coat Weight'].default_value = coat; return m

# ---------------------------------------------------------------- сцена
def setup_scene():
    try: bpy.ops.wm.read_factory_settings(use_empty=True)
    except Exception:
        for o in list(bpy.data.objects): bpy.data.objects.remove(o, do_unlink=True)
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = SAMPLES
    sc.cycles.use_denoising = True; sc.cycles.use_adaptive_sampling = True
    sc.render.film_transparent = True; sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = 'PNG'; sc.render.image_settings.color_mode = 'RGBA'
    sc.view_settings.view_transform = 'Standard'; sc.view_settings.look = 'None'
    w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True
    bg = w.node_tree.nodes['Background']; bg.inputs['Color'].default_value = (.03, .16, .38, 1); bg.inputs['Strength'].default_value = 1.0
    target = link(bpy.data.objects.new('target', None))
    def light(name, typ, loc, energy, color, size=3):
        d = bpy.data.lights.new(name, typ); d.energy = energy; d.color = color
        if typ == 'AREA': d.size = size
        o = link(bpy.data.objects.new(name, d)); o.location = loc
        c = o.constraints.new('TRACK_TO'); c.target = target; c.track_axis = 'TRACK_NEGATIVE_Z'; c.up_axis = 'UP_Y'
        return o
    light('key', 'SUN', (1.5, -2.5, 4), 2.4, (.95, .97, 1))
    light('fill', 'AREA', (-2.5, -4, .8), 150, (.6, .8, 1), 6)
    light('rim', 'AREA', (1.0, 3.5, 1.6), 150, (.6, .9, 1), 3)
    light('top', 'AREA', (0, -.5, 3.5), 90, (.85, 1, 1), 3)
    cd = bpy.data.cameras.new('cam'); cd.type = 'ORTHO'
    cam = link(bpy.data.objects.new('cam', cd)); cam.location = (0, -8, 0); cam.rotation_euler = (math.radians(90), 0, 0)
    sc.camera = cam
    return sc, cam

def build_fish(fid, spec):
    body, ph, pw, H, W, b = build_body(spec)
    parts = [body]
    body.data.materials.append(body_material(bake_texture(fid, spec)))
    fin, edge = spec['fin'], spec.get('fin_edge')
    T, spread = spec.get('tail_size', b['tail'])
    tail = fin_object('tail', tail_pts(spec['tail'], T, spread, max(.03, ph(.03) * 1.05)))
    tail.data.materials.append(fin_material('tail_m', spec.get('tail_color', fin), spec.get('tail_edge', edge), 'X', True, 1.0)); parts.append(tail)
    d_shape, d_h = spec['dorsal']; du = spec.get('dorsal_u', {'hump': (.30, .86), 'long': (.30, .90), 'sail': (.20, .93)}[d_shape])
    dors = fin_object('dorsal', rim_pts(ph, du[0], du[1], d_h, d_shape, 1))
    dors.data.materials.append(fin_material('dorsal_m', spec.get('dorsal_color', fin), edge, 'Z', False)); parts.append(dors)
    a_shape, a_h = spec['anal']; au = spec.get('anal_u', {'hump': (.34, .74), 'long': (.35, .8), 'sail': (.30, .92)}[a_shape])
    anal = fin_object('anal', rim_pts(ph, au[0], au[1], a_h, a_shape, -1))
    anal.data.materials.append(fin_material('anal_m', spec.get('anal_color', fin), edge, 'Z', True)); parts.append(anal)
    r = spec.get('pectoral_r', .17); up = .68
    pec = fin_object('pectoral', pectoral_pts(r), loc=(-.5 + up, -pw(up) * .85, -ph(up) * .1),
                     rot=(math.radians(-25), math.radians(-15), 0), thick=.008)
    pec.data.materials.append(fin_material('pec_m', spec.get('pectoral', fin), edge, 'X', True, 1.0)); parts.append(pec)
    ue = .84; re_ = .042 if spec['body'] in ('oval', 'small') else .048
    ez = ph(ue) * .25 + (-H * .10 * max(0.0, (ue - .72) / .28) ** 2)
    eye = sphere('eye', re_, (-.5 + ue, -pw(ue) * .9, ez)); eye.data.materials.append(plain_material('eye_m', (.32, .2, .07), .25, .6)); parts.append(eye)
    pup = sphere('pupil', re_ * .62, (-.5 + ue, -pw(ue) * .9 - re_ * .55, ez)); pup.data.materials.append(plain_material('pupil_m', (.01, .01, .012), .2)); parts.append(pup)
    root = link(bpy.data.objects.new('fish_' + fid, None))
    for p in parts: p.parent = root
    root.rotation_euler = (0, 0, math.radians(-8))          # чуть носом к камере — объём
    bbox = (-.5 - T - .04, .54, -(H * 1.07 + a_h) - .03, H + d_h + .03)
    return root, bbox

def render_species(fid, spec):
    sc, cam = setup_scene()
    root, (x0, x1, z0, z1) = build_fish(fid, spec)
    bw, bh = (x1 - x0) * 1.06, (z1 - z0) * 1.10
    sc.render.resolution_x = RES; sc.render.resolution_y = int(RES * bh / bw)
    cam.data.ortho_scale = bw; cam.location = ((x0 + x1) / 2, -8, (z0 + z1) / 2)
    os.makedirs(OUT, exist_ok=True)
    sc.render.filepath = os.path.join(OUT, fid + '.png')
    bpy.ops.render.render(write_still=True)
    if SAVE_BLEND: bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, fid + '.blend'))

if __name__ == '__main__':
    import time
    for fid, spec in SPECIES.items():
        if ONLY and fid not in ONLY: continue
        t = time.time(); render_species(fid, spec); print(f'OK {fid} {time.time() - t:.0f}s', flush=True)

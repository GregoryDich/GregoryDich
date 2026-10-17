"""Exosome cells for the V-TECH scroll story (owner 17/10): round glassy cells with gold particles inside that float
like asteroids over a deep background, nearer and farther with the scroll (refs: his three cell pictures of 17/10).
One cell per render, path-traced in Cycles on a transparent film; the page lays the sprites over plate.webp.

  render (Python with bpy 4.2):  cells_scene.py <out.png> <seed> [size=1024] [samples=128] [key=value …]
  post (python3 + PIL, numpy, scipy):  cells_scene.py post <render.png> <out stem>  → <stem>-0/-1/-2.webp
  plate (python3 + PIL, numpy, scipy):  cells_scene.py plate <out.webp> [2592x1620]

render writes <out.png> (RGBA, the geometric alpha) and <out>-k.png (the same frame over black, Filmic): the light
of the cell (glowing rims, the haze inside, the particles) lives mostly in the see-through parts, so the post step
rebuilds the alpha from both (alpha = max(geometric, brightness)), and the sprite then gives over black exactly the
render and over the plate a glow that is not lost. post adds a soft bloom and makes the three focus levels:
0 sharp, 1 soft (Gaussian), 2 bokeh (a disc with a brighter rim, blurred in light, so the brightest particles open
into discs as through a lens).
keys (each one drawn from the seed when not given): core (core radius / cell), dens (particles), wob (the shell's
slow wobble), rip (ripples), flat (depth squash, < 1 a disc seen face on), outer (a faint second layer), inner (an
inner membrane around the core), cres (the gold crescent of light inside, 0 none), strands (dotted strands on the
core), glow (the core's glowing limb), tilt (turn of the cell, radians)."""
import math, os, random, sys


def params(seed, kv):
    R = random.Random(seed)
    P = dict(core=R.uniform(0.54, 0.74), dens=R.uniform(0.75, 1.6), wob=R.uniform(0.025, 0.055), rip=R.uniform(0.004, 0.009),
             flat=1.0, outer=float(R.random() < 0.5), inner=float(R.random() < 0.35), cres=R.choice((0.0, 0.5, 1.0)),
             strands=float(R.choice((0, 0, 4))), glow=R.uniform(0.7, 1.2), tilt=R.uniform(0, 6.28), warm=R.choice((0.0, 0.5, 1.0)),
             ell=R.uniform(-0.05, 0.05), th=R.uniform(0.045, 0.08))
    for a in kv:
        k, v = a.split('='); assert k in P, k; P[k] = float(v)
    return P


# ---------------------------------------------------------------- render (bpy) ----------------------------------------
def render(argv):
    import bpy, bmesh
    import numpy as np
    from mathutils import Vector, noise

    OUT, SEED = os.path.abspath(argv[0]), int(argv[1])
    SIZE = int(argv[2]) if len(argv) > 2 else 1024
    SAMPLES = int(argv[3]) if len(argv) > 3 else 128
    P = params(SEED, argv[4:]); print('cell', SEED, {k: round(v, 3) for k, v in P.items()})
    rng = np.random.default_rng(SEED)
    O = Vector((SEED * 7.31 % 50, SEED * 3.17 % 50, SEED * 5.53 % 50))   # the cell's own patch of noise

    bpy.ops.wm.read_factory_settings(use_empty=True)
    scn = bpy.context.scene
    root = bpy.data.objects.new('cell', None); scn.collection.objects.link(root)
    root.rotation_euler = (0.35 * math.sin(P['tilt']), 0.35 * math.cos(P['tilt']), P['tilt']); root.scale = (1 + P['ell'], 1 - P['ell'], P['flat'])

    def fbm(p, octaves=3):
        s, a, f = 0.0, 1.0, 1.0
        for _ in range(octaves): s += a * noise.noise(p * f); a *= 0.5; f *= 2.03
        return s

    def obj(name, data, m=None, parent=root):
        ob = bpy.data.objects.new(name, data); scn.collection.objects.link(ob); ob.parent = parent
        if m: ob.data.materials.append(m)
        return ob

    def surface(radius, inward=False, sub=6):   # a closed, smooth, displaced sphere; radius(n) → r along the unit vector n
        bm2 = bmesh.new(); bmesh.ops.create_icosphere(bm2, subdivisions=sub, radius=1.0)
        for v in bm2.verts:
            n = v.co.normalized(); v.co = n * radius(n)
        if inward: bmesh.ops.reverse_faces(bm2, faces=bm2.faces[:])   # a shell's inner wall faces the cavity
        me = bpy.data.meshes.new('surf'); bm2.to_mesh(me); bm2.free()
        me.polygons.foreach_set('use_smooth', [True] * len(me.polygons)); me.update()
        return me

    def shell(outer, inner, sub=6):   # both walls in one mesh, so the volume between them is one closed body
        bm = bmesh.new()
        for me in (surface(outer, sub=sub), surface(inner, inward=True, sub=sub)): bm.from_mesh(me); bpy.data.meshes.remove(me)
        me = bpy.data.meshes.new('shell'); bm.to_mesh(me); bm.free()
        me.polygons.foreach_set('use_smooth', [True] * len(me.polygons)); me.update()
        return me

    # the membrane: a slow wobble shared by both walls (even thickness), its own ripples on each wall
    W, RIP = P['wob'], P['rip']
    def shape(n): return 1.0 + W * fbm(n * 1.3 + O, 2) + 0.4 * W * noise.noise(n * 3.1 + O * 0.7)
    def outer_r(n): return shape(n) + RIP * fbm(n * 7.0 + O * 1.3, 2)
    TH = P['th']
    def inner_r(n): return shape(n) - TH * (1 + 0.35 * noise.noise(n * 2.3 + O * 1.9)) + 0.6 * RIP * fbm(n * 8.0 + O * 2.1, 2)
    RC = P['core']
    COFF = Vector(rng.normal(0, 0.03, 3))   # the core sits a little off centre
    def core_r(n): return RC * (1.0 + 0.5 * W * fbm(n * 1.7 + O * 0.4, 2))

    # ---------- materials ----------
    def nodes(m):   # every glow here is seen, not cast (nothing is diffuse): no light sampling, no light tree
        m.use_nodes = True; m.cycles.emission_sampling = 'NONE'; nt = m.node_tree; nt.nodes.clear()
        return nt, nt.nodes.new('ShaderNodeOutputMaterial')

    VIOLET, SILVER = (0.55, 0.13, 1.0, 1), (0.62, 0.72, 1.0, 1)
    # the room the glass mirrors: black, with soft lobes (direction, colour, sharpness, strength); camera at +z, y up.
    # A rim reflects what lies behind the cell: a broad violet behind-left-low, silver strips behind-top that the
    # ripples break into streaks, a sheen up front-left for the face, a faint rose lower right
    LOBES = (((0.0, 0.35, -1.0), (0.35, 0.40, 0.55), 2.0, 0.07),     # a dim blue-grey sky behind: the gel reads dark and glossy
             ((-0.62, -0.32, -0.72), (0.55, 0.12, 1.0), 26.0, 1.0),     # violet, behind-left-low
             ((0.10, 0.70, -0.70), (0.75, 0.82, 1.0), 120.0, 4.5), ((-0.38, 0.74, -0.55), (0.75, 0.80, 1.0), 160.0, 4.0),
             ((0.48, 0.52, -0.70), (0.80, 0.80, 1.0), 140.0, 3.0), ((0.25, 0.60, -0.76), (0.70, 0.76, 1.0), 20.0, 0.35), ((-0.80, 0.25, -0.55), (0.62, 0.45, 1.0), 30.0, 0.6),
             ((-0.5, 0.58, 0.64), (0.92, 0.9, 1.0), 80.0, 1.0), ((0.72, -0.55, -0.42), (0.85, 0.28, 0.75), 10.0, 0.4))

    def env(nt, d):   # the lobes seen along the direction d (a node socket) → a colour socket
        acc = None
        for dv, col, pw, k in LOBES:
            dt = nt.nodes.new('ShaderNodeVectorMath'); dt.operation = 'DOT_PRODUCT'; dt.inputs[1].default_value = Vector(dv).normalized(); nt.links.new(d, dt.inputs[0])
            mx = nt.nodes.new('ShaderNodeMath'); mx.operation = 'MAXIMUM'; mx.inputs[1].default_value = 0; nt.links.new(dt.outputs['Value'], mx.inputs[0])
            pn = nt.nodes.new('ShaderNodeMath'); pn.operation = 'POWER'; pn.inputs[1].default_value = pw; nt.links.new(mx.outputs[0], pn.inputs[0])
            sc = nt.nodes.new('ShaderNodeVectorMath'); sc.operation = 'SCALE'; sc.inputs[0].default_value = tuple(c * k for c in col); nt.links.new(pn.outputs[0], sc.inputs[3])
            if acc is None: acc = sc.outputs[0]
            else:
                ad = nt.nodes.new('ShaderNodeVectorMath'); ad.operation = 'ADD'; nt.links.new(acc, ad.inputs[0]); nt.links.new(sc.outputs[0], ad.inputs[1]); acc = ad.outputs[0]
        return acc

    def glass(name, rim, body, sheen=1.0, waves=0.9, dark=2.5):
        """A membrane: two thin clear walls and a faint lavender glow between them. Everything is computed in the
        shader, so nothing is left to chance and a few samples give a clean picture: the walls let the ray straight
        through (no lens: a refracting shell became a milky light guide), the mirror is the Fresnel share of the lobes
        along the reflected ray (ripples from a bump), tinted violet below-left and silver-blue above as a thin film
        would, the edge glows a little, and the glow between the walls adds up along the path, so the edge seen
        side-on is bright while the face stays clear."""
        m = bpy.data.materials.new(name); nt, out = nodes(m)
        g = nt.nodes.new('ShaderNodeNewGeometry')
        # the gel's surface: folds that run along the outline (rings about the view axis, wavering) over slow waves
        tco = nt.nodes.new('ShaderNodeTexCoord')
        wv = nt.nodes.new('ShaderNodeTexWave'); wv.wave_type = 'RINGS'; wv.inputs['Scale'].default_value = 3.2; wv.inputs['Distortion'].default_value = 5.0
        wv.inputs['Detail'].default_value = 2.0; wv.inputs['Detail Scale'].default_value = 1.2; nt.links.new(tco.outputs['Object'], wv.inputs['Vector'])
        bn = nt.nodes.new('ShaderNodeTexNoise'); bn.inputs['Scale'].default_value = 2.2; bn.inputs['Detail'].default_value = 3; nt.links.new(tco.outputs['Object'], bn.inputs['Vector'])
        hm = nt.nodes.new('ShaderNodeMath'); hm.operation = 'MULTIPLY_ADD'; hm.inputs[1].default_value = 0.5; nt.links.new(wv.outputs['Fac'], hm.inputs[0]); nt.links.new(bn.outputs['Fac'], hm.inputs[2])
        bp = nt.nodes.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = waves; bp.inputs['Distance'].default_value = 0.025
        nt.links.new(hm.outputs[0], bp.inputs['Height'])
        ni = nt.nodes.new('ShaderNodeVectorMath'); ni.operation = 'SCALE'; ni.inputs[3].default_value = -1; nt.links.new(g.outputs['Incoming'], ni.inputs[0])
        rf = nt.nodes.new('ShaderNodeVectorMath'); rf.operation = 'REFLECT'; nt.links.new(ni.outputs[0], rf.inputs[0]); nt.links.new(bp.outputs['Normal'], rf.inputs[1])
        # Schlick's Fresnel on |N·I|, the same from either side (the Fresnel node takes a wall seen from inside for
        # glass-to-air: total reflection over most of the cell, which filled it with violet)
        cs = nt.nodes.new('ShaderNodeVectorMath'); cs.operation = 'DOT_PRODUCT'; nt.links.new(bp.outputs['Normal'], cs.inputs[0]); nt.links.new(g.outputs['Incoming'], cs.inputs[1])
        ab = nt.nodes.new('ShaderNodeMath'); ab.operation = 'ABSOLUTE'; nt.links.new(cs.outputs['Value'], ab.inputs[0])
        om = nt.nodes.new('ShaderNodeMath'); om.operation = 'SUBTRACT'; om.use_clamp = True; om.inputs[0].default_value = 1.0; nt.links.new(ab.outputs[0], om.inputs[1])
        p5 = nt.nodes.new('ShaderNodeMath'); p5.operation = 'POWER'; p5.inputs[1].default_value = 5.0; nt.links.new(om.outputs[0], p5.inputs[0])
        fr = nt.nodes.new('ShaderNodeMath'); fr.operation = 'MULTIPLY_ADD'; fr.inputs[1].default_value = 0.98; fr.inputs[2].default_value = 0.02; nt.links.new(p5.outputs[0], fr.inputs[0])
        # where on the cell (from its centre, the same for every wall; a wall's own normal flips on the inner and far walls)
        pd = nt.nodes.new('ShaderNodeVectorMath'); pd.operation = 'NORMALIZE'; nt.links.new(g.outputs['Position'], pd.inputs[0])
        sx = nt.nodes.new('ShaderNodeSeparateXYZ'); nt.links.new(pd.outputs[0], sx.inputs[0])
        side = nt.nodes.new('ShaderNodeMath'); side.operation = 'MULTIPLY_ADD'; side.inputs[1].default_value = 0.6; side.inputs[2].default_value = 0.45
        nt.links.new(sx.outputs['Y'], side.inputs[0])
        side2 = nt.nodes.new('ShaderNodeMath'); side2.operation = 'MULTIPLY_ADD'; side2.inputs[1].default_value = 0.25
        nt.links.new(sx.outputs['X'], side2.inputs[0]); nt.links.new(side.outputs[0], side2.inputs[2])
        tn = nt.nodes.new('ShaderNodeTexNoise'); tn.inputs['Scale'].default_value = 2.2   # the film drifts a little
        side3 = nt.nodes.new('ShaderNodeMath'); side3.operation = 'MULTIPLY_ADD'; side3.inputs[1].default_value = 0.5; side3.use_clamp = True
        nt.links.new(tn.outputs['Fac'], side3.inputs[0]); nt.links.new(side2.outputs[0], side3.inputs[2])
        side4 = nt.nodes.new('ShaderNodeMath'); side4.operation = 'SUBTRACT'; side4.use_clamp = True; side4.inputs[1].default_value = 0.25; nt.links.new(side3.outputs[0], side4.inputs[0])
        tint = nt.nodes.new('ShaderNodeMix'); tint.data_type = 'RGBA'; tint.inputs[6].default_value = VIOLET; tint.inputs[7].default_value = SILVER
        nt.links.new(side4.outputs[0], tint.inputs['Factor'])
        pn = nt.nodes.new('ShaderNodeVectorMath'); pn.operation = 'NORMALIZE'; nt.links.new(g.outputs['Position'], pn.inputs[0])
        ins = nt.nodes.new('ShaderNodeVectorMath'); ins.operation = 'DOT_PRODUCT'; nt.links.new(rf.outputs[0], ins.inputs[0]); nt.links.new(pn.outputs[0], ins.inputs[1])
        inw = nt.nodes.new('ShaderNodeMath'); inw.operation = 'MULTIPLY'; inw.use_clamp = True; inw.inputs[1].default_value = -1; nt.links.new(ins.outputs['Value'], inw.inputs[0])
        inp = nt.nodes.new('ShaderNodeMath'); inp.operation = 'POWER'; inp.inputs[1].default_value = 3.0; nt.links.new(inw.outputs[0], inp.inputs[0])
        gold = nt.nodes.new('ShaderNodeVectorMath'); gold.operation = 'SCALE'; gold.inputs[0].default_value = (0.9, 0.38, 0.08); nt.links.new(inp.outputs[0], gold.inputs[3])
        envd = nt.nodes.new('ShaderNodeVectorMath'); envd.operation = 'ADD'; nt.links.new(env(nt, rf.outputs[0]), envd.inputs[0]); nt.links.new(gold.outputs[0], envd.inputs[1])
        refl = nt.nodes.new('ShaderNodeVectorMath'); refl.operation = 'MULTIPLY'; nt.links.new(envd.outputs[0], refl.inputs[0])
        film = nt.nodes.new('ShaderNodeMix'); film.data_type = 'RGBA'; film.inputs['Factor'].default_value = 0.3; film.inputs[6].default_value = (1, 1, 1, 1)
        nt.links.new(tint.outputs[2], film.inputs[7]); nt.links.new(film.outputs[2], refl.inputs[1])
        # the far half of the cell is seen through the gel: its walls mirror at a quarter (else violet rings it all round)
        pz = nt.nodes.new('ShaderNodeSeparateXYZ'); nt.links.new(g.outputs['Position'], pz.inputs[0])
        far = nt.nodes.new('ShaderNodeMapRange'); far.inputs['From Min'].default_value = -0.3; far.inputs['From Max'].default_value = 0.1
        far.inputs['To Min'].default_value = 0.25 * sheen; far.inputs['To Max'].default_value = sheen; nt.links.new(pz.outputs['Z'], far.inputs['Value'])
        fk = nt.nodes.new('ShaderNodeMath'); fk.operation = 'MULTIPLY'; nt.links.new(far.outputs['Result'], fk.inputs[1]); nt.links.new(fr.outputs[0], fk.inputs[0])
        rs = nt.nodes.new('ShaderNodeVectorMath'); rs.operation = 'SCALE'; nt.links.new(refl.outputs[0], rs.inputs[0]); nt.links.new(fk.outputs[0], rs.inputs[3])
        lw = nt.nodes.new('ShaderNodeLayerWeight'); lw.inputs['Blend'].default_value = 0.5
        pw = nt.nodes.new('ShaderNodeMath'); pw.operation = 'POWER'; pw.inputs[1].default_value = 14.0; nt.links.new(lw.outputs['Facing'], pw.inputs[0])
        k = nt.nodes.new('ShaderNodeMath'); k.operation = 'MULTIPLY'; k.inputs[1].default_value = rim; nt.links.new(pw.outputs[0], k.inputs[0])
        rc = nt.nodes.new('ShaderNodeVectorMath'); rc.operation = 'SCALE'; nt.links.new(tint.outputs[2], rc.inputs[0]); nt.links.new(k.outputs[0], rc.inputs[3])
        tot = nt.nodes.new('ShaderNodeVectorMath'); tot.operation = 'ADD'; nt.links.new(rs.outputs[0], tot.inputs[0]); nt.links.new(rc.outputs[0], tot.inputs[1])
        em = nt.nodes.new('ShaderNodeEmission'); nt.links.new(tot.outputs[0], em.inputs['Color'])
        tr, ad = nt.nodes.new('ShaderNodeBsdfTransparent'), nt.nodes.new('ShaderNodeAddShader')
        nt.links.new(tr.outputs[0], ad.inputs[0]); nt.links.new(em.outputs[0], ad.inputs[1]); nt.links.new(ad.outputs[0], out.inputs['Surface'])
        # between the walls: a dark blue-grey gel that dims what lies behind its edge, with a breath of lavender light
        ve = nt.nodes.new('ShaderNodeEmission'); ve.inputs['Color'].default_value = (0.55, 0.5, 1.0, 1); ve.inputs['Strength'].default_value = body
        va = nt.nodes.new('ShaderNodeVolumeAbsorption'); va.inputs['Color'].default_value = (0.55, 0.55, 0.72, 1); va.inputs['Density'].default_value = dark
        vs = nt.nodes.new('ShaderNodeAddShader'); nt.links.new(ve.outputs[0], vs.inputs[0]); nt.links.new(va.outputs[0], vs.inputs[1])
        nt.links.new(vs.outputs[0], out.inputs['Volume'])
        return m

    # brand gold through Filmic MHC (measured): (1, .42, .08) at 0.4 / 0.8 / 1.6 / 3.2 shows #ac7c2e / #cca349 / #e3c56c /
    # #f2de94, i.e. deep gold, the brand's #c9a24b, light gold, a pale spark: one hue, the brightness does the rest
    GOLD_DEEP, GOLD_PALE = (1.0, 0.38, 0.07, 1), (1.0, 0.46, 0.10, 1)
    def core_mat():   # the nucleus: dark warm matter, mottled, its limb glowing gold (light seen through its edge)
        m = bpy.data.materials.new('core'); nt, out = nodes(m)
        tc = nt.nodes.new('ShaderNodeTexCoord'); ns = nt.nodes.new('ShaderNodeTexNoise'); ns.inputs['Scale'].default_value = 5.0; ns.inputs['Detail'].default_value = 6
        nt.links.new(tc.outputs['Object'], ns.inputs['Vector'])
        mx = nt.nodes.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.inputs[6].default_value = (0.0015, 0.0016, 0.0024, 1)
        mx.inputs[7].default_value = tuple(c * (1 - P['warm']) + w * P['warm'] for c, w in zip((0.006, 0.0062, 0.009), (0.024, 0.010, 0.0028))) + (1,)   # ref 41 blue-black … ref 40 brown
        nt.links.new(ns.outputs['Fac'], mx.inputs['Factor'])
        lw = nt.nodes.new('ShaderNodeLayerWeight'); lw.inputs['Blend'].default_value = 0.5
        pw = nt.nodes.new('ShaderNodeMath'); pw.operation = 'POWER'; pw.inputs[1].default_value = 3.0; nt.links.new(lw.outputs['Facing'], pw.inputs[0])
        k = nt.nodes.new('ShaderNodeMath'); k.operation = 'MULTIPLY'; k.inputs[1].default_value = 0.2 * P['glow']; nt.links.new(pw.outputs[0], k.inputs[0])
        sc = nt.nodes.new('ShaderNodeVectorMath'); sc.operation = 'SCALE'; sc.inputs[0].default_value = GOLD_DEEP[:3]
        nt.links.new(k.outputs[0], sc.inputs[3])
        ad = nt.nodes.new('ShaderNodeVectorMath'); ad.operation = 'ADD'; nt.links.new(mx.outputs[2], ad.inputs[0]); nt.links.new(sc.outputs[0], ad.inputs[1])
        em = nt.nodes.new('ShaderNodeEmission'); nt.links.new(ad.outputs[0], em.inputs['Color']); nt.links.new(em.outputs[0], out.inputs['Surface'])
        return m

    def dots_mat():   # each particle: emission, its brightness b and warmth h from the point cloud
        m = bpy.data.materials.new('dots'); nt, out = nodes(m)
        ab, ah = nt.nodes.new('ShaderNodeAttribute'), nt.nodes.new('ShaderNodeAttribute')
        ab.attribute_type = ah.attribute_type = 'GEOMETRY'; ab.attribute_name, ah.attribute_name = 'b', 'h'
        mx = nt.nodes.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.inputs[6].default_value = GOLD_DEEP; mx.inputs[7].default_value = GOLD_PALE
        nt.links.new(ah.outputs['Fac'], mx.inputs['Factor'])
        em = nt.nodes.new('ShaderNodeEmission'); nt.links.new(mx.outputs[2], em.inputs['Color']); nt.links.new(ab.outputs['Fac'], em.inputs['Strength'])
        nt.links.new(em.outputs[0], out.inputs['Surface'])
        return m

    def haze_mat():   # the light inside: a gold haze hugging the core, and a crescent pooled against the membrane
        m = bpy.data.materials.new('haze'); nt, out = nodes(m)
        tc = nt.nodes.new('ShaderNodeTexCoord'); p = tc.outputs['Object']
        def op(kind, a, b=None, clamp=False):
            n = nt.nodes.new('ShaderNodeMath'); n.operation = kind; n.use_clamp = clamp
            for i, x in enumerate((a, b)):
                if x is None: continue
                if isinstance(x, (int, float)): n.inputs[i].default_value = x
                else: nt.links.new(x, n.inputs[i])
            return n.outputs[0]
        off = nt.nodes.new('ShaderNodeVectorMath'); off.operation = 'SUBTRACT'; off.inputs[1].default_value = COFF; nt.links.new(p, off.inputs[0])
        ln = nt.nodes.new('ShaderNodeVectorMath'); ln.operation = 'LENGTH'; nt.links.new(off.outputs[0], ln.inputs[0])
        d = op('MAXIMUM', op('SUBTRACT', ln.outputs['Value'], RC), 0.0)
        halo = op('EXPONENT', op('MULTIPLY', d, -1 / 0.04))   # 1 at the core's skin, gone ~0.12 out
        nm = nt.nodes.new('ShaderNodeVectorMath'); nm.operation = 'NORMALIZE'; nt.links.new(p, nm.inputs[0])
        dt = nt.nodes.new('ShaderNodeVectorMath'); dt.operation = 'DOT_PRODUCT'; dt.inputs[1].default_value = CRES_DIR; nt.links.new(nm.outputs[0], dt.inputs[0])
        lob = op('POWER', op('MAXIMUM', dt.outputs['Value'], 0.0), 3.0)
        lp = nt.nodes.new('ShaderNodeVectorMath'); lp.operation = 'LENGTH'; nt.links.new(p, lp.inputs[0])
        band = op('EXPONENT', op('MULTIPLY', op('POWER', op('SUBTRACT', lp.outputs['Value'], 0.5 * (RC + 0.94)), 2.0), -1 / 0.006))
        ns = nt.nodes.new('ShaderNodeTexNoise'); ns.inputs['Scale'].default_value = 4.0; ns.inputs['Detail'].default_value = 2; nt.links.new(p, ns.inputs['Vector'])
        cres = op('MULTIPLY', op('MULTIPLY', lob, band), op('MULTIPLY', ns.outputs['Fac'], 2.0 * P['cres']))
        dens = op('ADD', op('MULTIPLY', halo, 0.15 * P['glow']), cres)
        em = nt.nodes.new('ShaderNodeEmission'); em.inputs['Color'].default_value = GOLD_DEEP
        nt.links.new(op('MULTIPLY', dens, 1.6), em.inputs['Strength']); nt.links.new(em.outputs[0], out.inputs['Volume'])
        return m

    CRES_DIR = Vector(rng.normal(0, 1, 3)); CRES_DIR.z = -abs(CRES_DIR.z) * 0.3; CRES_DIR.y = -abs(CRES_DIR.y) - 0.6; CRES_DIR.normalize()

    # ---------- geometry ----------
    obj('membrane', shell(outer_r, inner_r), glass('membrane', 0.45, 0.008))
    if P['outer'] > 0.5:   # a faint second skin, a little larger and out of step with the first (ref 40)
        def o2(n): return shape(n) + 0.03 + 1.0 * W * noise.noise(n * 2.0 + O * 3.3) + RIP * fbm(n * 6 + O * 4.1, 2)
        obj('outer', shell(o2, lambda n: o2(n) - 0.02), glass('outer', 0.35, 0.005, 0.6, 0.6, 1.0))
    if P['inner'] > 0.5:   # an inner membrane between the core and the cytoplasm
        ri = RC + 0.55 * (0.92 - RC)
        def i1(n): return ri * (1 + 0.6 * W * fbm(n * 1.9 + O * 5.1, 2))
        obj('inner', shell(i1, lambda n: i1(n) - 0.025, sub=5), glass('inner', 0.25, 0.006, 0.5, 0.6, 1.0)).location = COFF * 0.5
    core = obj('core', surface(core_r, sub=5), core_mat()); core.location = COFF
    obj('haze', surface(lambda n: inner_r(n) - 0.012, sub=4), haze_mat())

    # ---------- particles: a point cloud (Geometry Nodes, points render as tiny spheres in Cycles) ----------
    def dirs(n):
        v = rng.normal(size=(n, 3)); return v / np.linalg.norm(v, axis=1)[:, None]
    def radial(D, f):   # f(n) at each unit vector
        return np.array([f(Vector(d)) for d in D])
    pts, rad, bri, hue = [], [], [], []
    def add(p, r, b, h): pts.append(p); rad.append(r); bri.append(b); hue.append(h)
    dens = P['dens']
    # on the core's skin, clustered by a slow noise (the limb fills up by itself in projection)
    n = int(6500 * dens * (RC / 0.64) ** 2); D = dirs(n)
    keep = np.array([rng.random() < 0.45 + 0.55 * max(0, 0.5 + noise.noise(Vector(d) * 2.6 + O)) for d in D]); D = D[keep]
    r = radial(D, core_r) + 0.006 + np.abs(rng.normal(0, 0.006, len(D)))
    add(D * r[:, None] + np.array(COFF), rng.lognormal(np.log(0.0031), 0.3, len(D)), rng.lognormal(0, 0.8, len(D)) * 1.1, rng.random(len(D)))
    # the cytoplasm: sparser, smaller, denser toward the membrane's inner wall (r^5)
    n = int(900 * dens); D = dirs(n); rin = radial(D, inner_r)
    a = RC + 0.05; u = rng.random(n); rr = (a ** 6 + u * (np.maximum(rin - 0.015, a + 0.01) ** 6 - a ** 6)) ** (1 / 6)
    add(D * rr[:, None], rng.lognormal(np.log(0.0025), 0.3, n), rng.lognormal(0, 0.6, n) * 0.8, rng.random(n))
    # a thin skin of points just inside the membrane
    n = int(1200 * dens); D = dirs(n); rr = radial(D, inner_r) - 0.008 - np.abs(rng.normal(0, 0.01, n))
    add(D * rr[:, None], rng.lognormal(np.log(0.0025), 0.3, n), rng.lognormal(0, 0.6, n) * 1.0, rng.random(n))
    if P['cres'] > 0:   # the crescent: points pile up where the light pools
        n = int(2500 * P['cres'] * dens); D = dirs(n * 3); w = np.clip(D @ np.array(CRES_DIR), 0, 1) ** 3
        D = D[rng.random(len(D)) < w][:n]; rin = radial(D, inner_r)
        rr = RC + 0.04 + (rin - RC - 0.06) * rng.beta(4, 2, len(D))
        add(D * rr[:, None], rng.lognormal(np.log(0.0028), 0.3, len(D)), rng.lognormal(0, 0.6, len(D)) * 1.8, 0.5 + 0.5 * rng.random(len(D)))
    TURN = root.rotation_euler.to_matrix()
    for s in range(int(P['strands'])):   # dotted strands wandering over the core (ref 42), on the side we see
        d = Vector(dirs(1)[0])
        while (TURN @ d).z < 0.25: d = Vector(dirs(1)[0])
        t = d.cross(Vector(dirs(1)[0])).normalized(); seg = []
        for i in range(int(rng.integers(40, 90))):
            seg.append(d * (core_r(d) + 0.009)); ang = rng.normal(0, 0.35)
            t = (t * math.cos(ang) + d.cross(t) * math.sin(ang)).normalized(); d = (d + t * 0.013).normalized(); t = (t - d * t.dot(d)).normalized()
        S = np.array(seg); add(S + np.array(COFF), np.full(len(S), 0.0028), np.full(len(S), 2.4), np.full(len(S), 0.8))
    n = int(rng.integers(18, 40)); D = dirs(n)   # a few strays outside, some larger and brighter
    rr = 1.08 + rng.random(n) ** 1.5 * 0.42
    add(D * rr[:, None], rng.lognormal(np.log(0.006), 0.35, n), rng.lognormal(0.3, 0.6, n) * 1.4, rng.random(n) * 0.6)
    pts, rad, bri, hue = (np.concatenate(x) for x in (pts, rad, bri, hue)); print('points', len(pts))
    me = bpy.data.meshes.new('pts'); me.vertices.add(len(pts)); me.vertices.foreach_set('co', pts.astype(np.float32).ravel())
    for name, arr in (('rad', rad), ('b', bri), ('h', hue)):
        me.attributes.new(name, 'FLOAT', 'POINT').data.foreach_set('value', arr.astype(np.float32))
    me.update()
    po = obj('particles', me)
    ng = bpy.data.node_groups.new('points', 'GeometryNodeTree')
    ng.interface.new_socket('Geometry', in_out='INPUT', socket_type='NodeSocketGeometry')
    ng.interface.new_socket('Geometry', in_out='OUTPUT', socket_type='NodeSocketGeometry')
    gi, go = ng.nodes.new('NodeGroupInput'), ng.nodes.new('NodeGroupOutput')
    mp = ng.nodes.new('GeometryNodeMeshToPoints'); na = ng.nodes.new('GeometryNodeInputNamedAttribute'); na.data_type = 'FLOAT'; na.inputs['Name'].default_value = 'rad'
    sm = ng.nodes.new('GeometryNodeSetMaterial'); sm.inputs['Material'].default_value = dots_mat()
    ng.links.new(gi.outputs[0], mp.inputs['Mesh']); ng.links.new(na.outputs['Attribute'], mp.inputs['Radius'])
    ng.links.new(mp.outputs['Points'], sm.inputs['Geometry']); ng.links.new(sm.outputs['Geometry'], go.inputs[0])
    po.modifiers.new('points', 'NODES').node_group = ng

    scn.world = bpy.data.worlds.new('black'); scn.world.color = (0, 0, 0)   # the lobes live in the membrane's shader

    # ---------- camera: a long lens, the cell ~0.73 of the frame (room for glow, strays and the bokeh blur) ----------
    cam = bpy.data.objects.new('camera', bpy.data.cameras.new('camera')); scn.collection.objects.link(cam); scn.camera = cam
    cam.data.lens = 100; cam.data.sensor_width = 36; cam.location = (0, 0, 7.4); cam.data.clip_start = 1; cam.data.clip_end = 20

    r, c = scn.render, scn.cycles
    r.engine = 'CYCLES'; c.device = 'CPU'; c.samples = SAMPLES; c.seed = SEED
    if os.environ.get('VT_DEVICE'):   # a GPU backend, e.g. METAL on the owner's Mac
        pr = bpy.context.preferences.addons['cycles'].preferences; pr.compute_device_type = os.environ['VT_DEVICE']; pr.get_devices()
        for d in pr.devices: d.use = d.type != 'CPU'
        c.device = 'GPU'
    c.use_adaptive_sampling = True; c.adaptive_threshold = 0.004
    c.use_denoising = False   # everything is emission or clear glass: no noise to remove, and OIDN would smear the particles
    c.max_bounces = 16; c.diffuse_bounces = 0; c.glossy_bounces = 6; c.transmission_bounces = 4; c.transparent_max_bounces = 48; c.volume_bounces = 0
    c.caustics_reflective = c.caustics_refractive = False; c.sample_clamp_indirect = 0; c.sample_clamp_direct = 0   # a clamp would dim what is seen through the glass
    c.volume_step_rate = 1.0
    r.film_transparent = True; c.film_transparent_glass = True
    r.resolution_x = r.resolution_y = SIZE; r.resolution_percentage = 100
    scn.view_settings.view_transform = 'Filmic'; scn.view_settings.look = 'Medium High Contrast'
    scn.view_settings.exposure = float(os.environ.get('CELL_EXPOSURE', 0))
    r.image_settings.file_format = 'PNG'; r.image_settings.color_mode = 'RGBA'; r.image_settings.color_depth = '16'
    r.filepath = OUT
    # the compositor writes the same frame over black as well (for the post step's alpha)
    scn.use_nodes = True; ct = scn.node_tree; ct.nodes.clear()
    rl, cp = ct.nodes.new('CompositorNodeRLayers'), ct.nodes.new('CompositorNodeComposite'); ct.links.new(rl.outputs['Image'], cp.inputs['Image'])
    ao = ct.nodes.new('CompositorNodeAlphaOver'); ao.inputs[1].default_value = (0, 0, 0, 1); ct.links.new(rl.outputs['Image'], ao.inputs[2])
    fo = ct.nodes.new('CompositorNodeOutputFile'); fo.base_path = os.path.dirname(OUT); stem = os.path.splitext(os.path.basename(OUT))[0]
    fo.file_slots[0].path = stem + '-k#'; fo.format.file_format = 'PNG'; fo.format.color_mode = 'RGB'; fo.format.color_depth = '16'
    ct.links.new(ao.outputs['Image'], fo.inputs[0])
    scn.frame_set(1)
    bpy.ops.render.render(write_still=True)
    os.replace(os.path.join(os.path.dirname(OUT), stem + '-k1.png'), os.path.join(os.path.dirname(OUT), stem + '-k.png'))


# ---------------------------------------------------------------- post (PIL) ------------------------------------------
def post(argv):
    import numpy as np
    from PIL import Image
    from scipy import ndimage, signal
    src, stem = argv[0], argv[1]
    a = np.asarray(Image.open(src).convert('RGBA'), np.float32)[..., 3] / 255
    k = np.asarray(Image.open(os.path.splitext(src)[0] + '-k.png').convert('RGB'), np.float32) / 255
    lin = k ** 2.2
    # bloom in light: the particles and the rims bleed a little, as in the references
    hi = np.maximum(lin - 0.06, 0)
    bl = sum(wt * ndimage.gaussian_filter(hi, (s, s, 0)) for s, wt in ((1.5, 0.22), (6.0, 0.12), (22.0, 0.12)))
    lin = lin + bl
    Q, AQ = int(os.environ.get('CELL_Q', 78)), int(os.environ.get('CELL_AQ', 100))   # lossy alpha left rings round the glow
    SOFT_PX, BOKEH_PX = (int(v) for v in os.environ.get('CELL_PX', '448,352').split(','))   # the blurred levels carry no fine detail: saved smaller, the page scales them
    def save(lin_rgb, alpha, path, size=None):   # premultiplied light → straight sRGB with alpha = max(alpha, brightness)
        disp = np.clip(lin_rgb, 0, None)
        disp = np.where(disp > 0.8, 0.8 + 0.2 * np.tanh((disp - 0.8) / 0.2), disp) ** (1 / 2.2)   # soft shoulder
        A = np.maximum(np.clip(alpha, 0, 1), disp.max(axis=2))
        if size and size != A.shape[0]:   # resample premultiplied (the light over black), then divide
            rs = lambda c: np.asarray(Image.fromarray(np.ascontiguousarray(c, np.float32)).resize((size, size), Image.LANCZOS))
            disp = np.clip(np.dstack([rs(disp[..., i]) for i in range(3)]), 0, 1); A = np.maximum(np.clip(rs(A), 0, 1), disp.max(axis=2))
        # alpha rounded up to sixteenths (the colour divides by it, so over black the sprite is exact; over the dark plate
        # the error is a sixteenth of the plate, under 2/255): the lossless alpha plane shrinks to less than half
        A = np.where(A < 2 / 255, A, np.ceil(A * 16) / 16)
        col = np.where(A[..., None] > 1e-4, disp / np.maximum(A[..., None], 1e-4), 0)
        w = np.clip(A * 3, 0, 1)[..., None]   # where the sprite is faint its colour barely shows: smoothed there (fewer bytes)
        col = col * w + ndimage.gaussian_filter(col, (2.5, 2.5, 0)) * (1 - w)
        im = np.dstack([np.clip(col, 0, 1), A]) * 255 + 0.5
        Image.fromarray(im.astype(np.uint8), 'RGBA').save(path, 'WEBP', quality=Q, alpha_quality=AQ, method=6)
        return path, os.path.getsize(path)
    def gold(x, f=0.8):   # a blur averages Filmic's pale-yellow sparks with the dark into khaki: pull warm light back to gold
        r = x[..., :1]; warm = np.clip((r - x[..., 2:]) / np.maximum(r, 1e-6), 0, 1) * f
        return x * (1 - warm) + r * np.array([1.0, 0.48, 0.11]) * warm
    print(save(lin, a, stem + '-0.webp'))
    s = float(os.environ.get('CELL_SOFT', 6))   # 1: soft focus
    print(save(gold(ndimage.gaussian_filter(lin, (s, s, 0)), 0.35), ndimage.gaussian_filter(a, s), stem + '-1.webp', SOFT_PX))
    R = float(os.environ.get('CELL_BOKEH', 25))   # 2: bokeh, a disc with a brighter rim; highlights lifted first so they open into discs
    y, x = np.mgrid[-math.ceil(R):math.ceil(R) + 1, -math.ceil(R):math.ceil(R) + 1]; d = np.hypot(x, y)
    ker = np.clip(R + 0.5 - d, 0, 1) * (1 + 0.6 * np.clip((d - 0.72 * R) / (0.28 * R), 0, 1)); ker /= ker.sum()
    lum = lin.max(axis=2, keepdims=True); boost = 1 + 12 * np.clip((lum - 0.3) / 0.4, 0, 1) ** 2
    hdr = signal.fftconvolve(lin * boost, ker[..., None], mode='same', axes=(0, 1)) * (lin.sum() / (lin * boost).sum()) * 0.55   # same light, gathered into discs, dimmed
    print(save(gold(hdr), signal.fftconvolve(a, ker, mode='same'), stem + '-2.webp', BOKEH_PX))


# ---------------------------------------------------------------- plate (PIL) -----------------------------------------
def plate(argv):
    """The deep background of S2–S3: near-black with a faint violet-indigo haze, a few far cells out of focus (a violet
    rim round a dim gold body, as behind the cells in the references) and gold dust; the right half (the copy) calms
    down to the black. It crossfades with the gold smoke (vt-bg-wide.jpg): the same warm near-black (~#0d0b0b) and a
    breath of warm haze low on the left, so the change of mood is a change of light, not of paper."""
    import numpy as np
    from PIL import Image
    from scipy import ndimage
    out = argv[0]; W, H = (int(v) for v in (argv[1] if len(argv) > 1 else '2592x1620').split('x'))
    rng = np.random.default_rng(int(os.environ.get('PLATE_SEED', 23)))
    q = 4; h, w = H // q, W // q   # the soft layers at quarter size, the dust at full size
    def field(scale, octaves=4, g=0.55):
        f = np.zeros((h, w), np.float32); amp = 1.0
        for o in range(octaves):
            s = max(2, int(scale / 2 ** o)); n = rng.normal(size=(h // s + 3, w // s + 3)).astype(np.float32)
            f += amp * ndimage.zoom(n, s, order=3)[:h, :w]; amp *= g
        return (f - f.mean()) / f.std()
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32); u, v = xx / w, yy / h
    def smooth(x, a, b): t = np.clip((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t)
    left = 1 - 0.85 * smooth(u, 0.30, 0.80)   # everything lives on the left (the 3D) and fades out under the copy
    lin = np.zeros((h, w, 3), np.float32)
    haze = np.clip(field(150) * 0.6 + 0.25, 0, None) ** 2.5 * (0.5 + 0.5 * np.clip(field(60, 3) + 0.7, 0, None))
    pool = np.exp(-(((u - 0.28) / 0.32) ** 2 + ((v - 0.5) / 0.45) ** 2))
    lin += (haze * left * (0.3 + 0.7 * pool))[..., None] * np.array([0.0105, 0.0052, 0.0240])   # violet-indigo
    warm = np.clip(field(180, 3) * 0.6 + 0.3, 0, None) ** 2 * np.exp(-(((u - 0.05) / 0.25) ** 2 + ((v - 0.95) / 0.32) ** 2))
    lin += warm[..., None] * np.array([0.020, 0.0105, 0.0030])   # warm, low left, where the smoke's plume left off
    # far cells, out of focus: a soft violet ring round a dim warm body, a few gold discs inside
    cells = [(0.06, 0.16, 46), (0.40, 0.08, 30), (0.52, 0.86, 54), (0.13, 0.80, 24), (0.30, 0.42, 16), (0.60, 0.40, 14),
             (-0.02, 0.52, 38), (0.46, 0.60, 11), (0.24, 1.02, 34), (0.66, 0.16, 18)]
    for cx, cy, R in cells:
        R *= rng.uniform(0.9, 1.15); cx, cy = cx * w, cy * h
        d = np.hypot(xx - cx, yy - cy) / R; k = rng.uniform(0.55, 1.0) * (1 - 0.6 * smooth(cx / w, 0.4, 0.75))
        blur = 1.2 + R * 0.10
        body = ndimage.gaussian_filter(np.clip(1 - d, 0, 1) ** 0.5, blur)
        ring = ndimage.gaussian_filter(np.exp(-((d - 0.92) / 0.08) ** 2), blur)
        lin += k * (body[..., None] * np.array([0.020, 0.0085, 0.0018]) + ring[..., None] * np.array([0.020, 0.010, 0.046]))
        for i in range(int(rng.integers(2, 6))):   # inner bokeh: gold discs
            a_, r_ = rng.uniform(0, 6.28), rng.uniform(0, 0.6) * R
            dd = np.hypot(xx - cx - r_ * np.cos(a_), yy - cy - r_ * np.sin(a_)) / (R * rng.uniform(0.12, 0.22))
            lin += k * ndimage.gaussian_filter(np.clip(1.4 - dd, 0, 1).clip(0, 1), 0.8)[..., None] * np.array([0.040, 0.019, 0.004])
    big = np.dstack([np.asarray(Image.fromarray(lin[..., c]).resize((W, H), Image.BICUBIC)) for c in range(3)])
    # gold dust: fine points, a few soft discs, sparse under the copy
    U = np.linspace(0, 1, W, dtype=np.float32)[None, :]; V = np.linspace(0, 1, H, dtype=np.float32)[:, None]
    dust = np.zeros((H, W), np.float32); n = 1400
    px, py = rng.uniform(0, W, n), rng.uniform(0, H, n)
    keep = rng.random(n) < 1 - 0.8 * smooth(px / W, 0.35, 0.85); px, py = px[keep], py[keep]
    b = rng.lognormal(-1.0, 0.9, len(px))
    np.add.at(dust, (py.astype(int).clip(0, H - 1), px.astype(int).clip(0, W - 1)), b)
    soft = np.zeros_like(dust); m = rng.random(len(px)) < 0.06
    np.add.at(soft, (py[m].astype(int).clip(0, H - 1), px[m].astype(int).clip(0, W - 1)), b[m] * 3)
    dust = ndimage.gaussian_filter(dust, 0.8) * 1.6 + ndimage.gaussian_filter(dust, 4) * 4 + ndimage.gaussian_filter(soft, 9) * 40
    big += dust[..., None] * np.array([1.0, 0.42, 0.08]) * 0.35
    big *= (1 - 0.45 * (((U - 0.38) / 0.8) ** 2 + ((V - 0.5) / 0.75) ** 2))[..., None]   # vignette
    big += np.array([0.0008, 0.0006, 0.0007])   # the black of the smoke (~#0d0b0b)
    disp = np.clip(big, 0, 1) ** (1 / 2.2) * 255 + rng.uniform(-0.7, 0.7, (H, W, 1))   # a whisper of grain against banding
    Image.fromarray(np.clip(disp + 0.5, 0, 255).astype(np.uint8), 'RGB').save(out, 'WEBP', quality=int(os.environ.get('PLATE_Q', 86)), method=6)
    print(out, os.path.getsize(out))


if __name__ == '__main__':
    A = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:]
    {'post': post, 'plate': plate}.get(A[0], None)(A[1:]) if A[0] in ('post', 'plate') else render(A)

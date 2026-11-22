# Sugar Bloom - smooth reusable shapes for the skin kits (22.11.2026).
# The skin kits (game/src/shared/WeaponSkinKits.luau) used to draw spikes as two wedges, rings as
# chains of bars, horns and vines as bars with balls at the joints, runes as cubes. These shapes
# replace those compounds with one smooth mesh each. Every shape fills exactly the unit box
# [-0.5, 0.5]^3 in Roblox space, so a MeshPart of Size {x, y, z} is the same box the old parts used.
#
# Frame (same as the kit helpers): local +Y = length (base at -0.5, point at +0.5), local Z = width,
# local X = thickness.
#
# Run in Blender (after build_weapons.py is exec'd, it reuses Geo/make_object/C):
#   exec(open(r"H:\RobloxSweetGarden\meshes\build_weapons.py").read())
#   exec(open(r"H:\RobloxSweetGarden\meshes\build_kit_shapes.py").read())
#   build_kit_shapes()
import bpy, json, math, os
from mathutils import Vector

KIT_ROOT = r"H:\RobloxSweetGarden\meshes"


def _section_ellipse(n):
    return [(math.cos(2 * math.pi * k / n), math.sin(2 * math.pi * k / n)) for k in range(n)]


def _section_rounded_poly(n, round_=0.22, sub=3, phase=0.0):
    """unit polygon (corner radius 1) with rounded corners: smooth shading reads the facets as a cut
    crystal with soft highlights instead of hard polygon edges"""
    pts = []
    corners = [(math.cos(phase + 2 * math.pi * k / n), math.sin(phase + 2 * math.pi * k / n)) for k in range(n)]
    for k in range(n):
        p0, p1, p2 = Vector(corners[k - 1]), Vector(corners[k]), Vector(corners[(k + 1) % n])
        a = p1 + (p0 - p1) * round_
        b = p1 + (p2 - p1) * round_
        for s in range(sub + 1):
            t = s / sub
            q = (1 - t) ** 2 * a + 2 * (1 - t) * t * p1 + t * t * b  # quadratic bezier round the corner
            pts.append((q.x, q.y))
    return pts


def sweep(rows, section, close_bottom=True, close_top=True, cup=0.0):
    """rows: list of (y, hz, hx). section: unit (z, x) points. A ring of the section scaled (hz, hx)
    at every row; rows with hz == hx == 0 become poles. cup bends the section toward +x (leaves).
    -> verts, faces (roblox space, not yet normalised)"""
    verts, faces, rings = [], [], []
    for (y, hz, hx) in rows:
        if hz <= 1e-6 and hx <= 1e-6:
            rings.append([len(verts)])
            verts.append((0.0, y, 0.0))
            continue
        ring = []
        for (sz, sx) in section:
            z = sz * hz
            x = sx * hx + cup * (sz * sz) * hz
            ring.append(len(verts))
            verts.append((x, y, z))
        rings.append(ring)
    n = len(section)
    for a, b in zip(rings, rings[1:]):
        if len(a) == 1 and len(b) == 1:
            continue
        if len(a) == 1:
            for k in range(n):
                faces.append((a[0], b[(k + 1) % n], b[k]))
        elif len(b) == 1:
            for k in range(n):
                faces.append((a[k], a[(k + 1) % n], b[0]))
        else:
            for k in range(n):
                faces.append((a[k], a[(k + 1) % n], b[(k + 1) % n], b[k]))
    if close_bottom and len(rings[0]) > 1:
        c = len(verts)
        verts.append((0.0, rows[0][0], 0.0))
        r = rings[0]
        for k in range(n):
            faces.append((c, r[(k + 1) % n], r[k]))
    if close_top and len(rings[-1]) > 1:
        c = len(verts)
        verts.append((0.0, rows[-1][0], 0.0))
        r = rings[-1]
        for k in range(n):
            faces.append((c, r[k], r[(k + 1) % n]))
    return verts, faces


def normalise(verts):
    """scale every axis independently so the shape fills [-0.5, 0.5]^3 exactly"""
    lo = [min(v[i] for v in verts) for i in range(3)]
    hi = [max(v[i] for v in verts) for i in range(3)]
    out = []
    for v in verts:
        out.append(tuple((v[i] - (lo[i] + hi[i]) / 2) / max(1e-9, hi[i] - lo[i]) for i in range(3)))
    return out


def _rows(n, f):
    """n+1 rows along t in [0, 1]: f(t) -> (y, hz, hx)"""
    return [f(i / n) for i in range(n + 1)]


def shape_spike():
    # round ogive point: a slightly domed base, belly at 20 %, curved flanks to a sharp tip
    def f(t):
        y = t
        w = 0.5 * (1 - t) ** 0.85 * (1 + 0.22 * math.sin(math.pi * min(1.0, t * 1.6)) * (1 - t))
        return (y, w, w)
    rows = [(-0.04, 0.0, 0.0), (-0.025, 0.30, 0.30), (0.0, 0.46, 0.46)] + _rows(12, f)[1:]
    rows[-1] = (1.0, 0.0, 0.0)
    return sweep(rows, _section_ellipse(16), False, False)


def shape_crystal():
    # cut ice / obsidian crystal: rounded-hexagon prism with a faceted point
    sec = _section_rounded_poly(6, 0.2, 2, math.pi / 6)
    rows = [(0.0, 0.0, 0.0), (0.02, 0.36, 0.36), (0.06, 0.5, 0.5), (0.55, 0.47, 0.47), (0.66, 0.40, 0.40),
            (0.86, 0.14, 0.14), (0.93, 0.05, 0.05), (0.96, 0.0, 0.0)]
    return sweep(rows, sec, False, False)


def shape_blade():
    # flat triangular blade / fin / guard / membrane: lens section (thin rounded edges, thicker spine),
    # full-width base edge, edges bowed out a little, sharp point
    def f(t):
        w = 0.5 * (1 - t) * (1 + 0.16 * math.sin(math.pi * t))
        th = 0.5 * max(0.0, 1 - t) ** 0.6
        return (t, w, th)
    rows = [(0.0, 0.0, 0.0), (0.0, 0.47, 0.35)] + _rows(10, f)[1:]
    rows[-1] = (1.0, 0.0, 0.0)
    # lens section: thin at the edges (z = +-1), thick in the middle
    sec = []
    n = 20
    for k in range(n):
        a = 2 * math.pi * k / n
        z, x = math.cos(a), math.sin(a)
        sec.append((z, x * (1 - 0.55 * z * z)))
    return sweep(rows, sec, False, False)


def shape_leaf():
    # pointed oval leaf: narrow stem end, widest at 40 %, cupped, thin
    def f(t):
        w = 0.5 * math.sin(math.pi * t ** 0.85) ** 0.9
        th = 0.5 * (0.35 + 0.65 * math.sin(math.pi * t ** 0.85))
        return (t, w, th)
    rows = [(0.0, 0.0, 0.0), (0.012, 0.05, 0.25)] + _rows(12, f)[1:]
    rows[-1] = (1.0, 0.0, 0.0)
    sec = []
    n = 16
    for k in range(n):
        a = 2 * math.pi * k / n
        z, x = math.cos(a), math.sin(a)
        sec.append((z, x * (1 - 0.7 * z * z)))
    return sweep(rows, sec, False, False, cup=0.9)


def shape_petal():
    # teardrop petal: narrow at the base, round at the outer end, gently cupped
    def f(t):
        w = 0.5 * math.sqrt(max(0.0, math.sin(math.pi * (0.08 + 0.92 * t) ** 1.4)))
        return (t, w, 0.5 * (0.5 + 0.5 * w / 0.5))
    rows = [(0.0, 0.0, 0.0)] + _rows(12, f)[1:]
    rows[-1] = (1.0, 0.0, 0.0)
    sec = []
    n = 16
    for k in range(n):
        a = 2 * math.pi * k / n
        z, x = math.cos(a), math.sin(a)
        sec.append((z, x * (1 - 0.6 * z * z)))
    return sweep(rows, sec, False, False, cup=0.7)


def shape_rod(A):
    """capsule along Y for a bar A times longer than thick. The kits size it {t, len + t, t}, so the
    round caps (radius t/2) sit centred on the joints of a chain and neighbours blend without a pinch.
    Non-uniform scaling would stretch the caps, hence three meshes for short / mid / long bars."""
    r = 0.5
    body = A  # cylinder length in units of the thickness 1
    rows = []
    k = 5
    for i in range(k + 1):
        a = -math.pi / 2 + math.pi / 2 * i / k
        rows.append((r + r * math.sin(a), r * math.cos(a), r * math.cos(a)))
    top = [(2 * r + body - y, hz, hx) for (y, hz, hx) in reversed(rows)]
    rows = rows + top
    rows[0] = (0.0, 0.0, 0.0)
    rows[-1] = (2 * r + body, 0.0, 0.0)
    return sweep(rows, _section_ellipse(12), False, False)


def shape_gem():
    # rune stone: rounded-square bipyramid with a small table on top
    sec = _section_rounded_poly(4, 0.24, 2, 0.0)
    rows = [(0.0, 0.0, 0.0), (0.42, 0.46, 0.46), (0.5, 0.5, 0.5), (0.58, 0.46, 0.46), (0.95, 0.12, 0.12), (1.0, 0.0, 0.0)]
    return sweep(rows, sec, False, False)


def shape_ring(k):
    """torus round local Y. k = tube diameter / outer diameter (before normalising the height to 1)"""
    U, V = 40, 12
    R = 0.5 - k / 2
    rr = k / 2
    verts, faces = [], []
    for i in range(U):
        a = 2 * math.pi * i / U
        for j in range(V):
            b = 2 * math.pi * j / V
            r = R + rr * math.cos(b)
            verts.append((r * math.cos(a), rr * math.sin(b), r * math.sin(a)))
    for i in range(U):
        for j in range(V):
            i2, j2 = (i + 1) % U, (j + 1) % V
            faces.append((i * V + j, i * V + j2, i2 * V + j2, i2 * V + j))
    return verts, faces


# tube/outer ratios of the three ring meshes; WeaponSkinKits picks the closest to t / (2r + t)
RING_K = {"KRing1": 0.07, "KRing2": 0.14, "KRing3": 0.26}
# length / thickness of the three rod meshes; the kits pick the closest to len / t
ROD_A = {"KRod1": 2, "KRod2": 5, "KRod3": 12}

SHAPES = {
    "KSpike": shape_spike,
    "KCrystal": shape_crystal,
    "KBlade": shape_blade,
    "KLeaf": shape_leaf,
    "KPetal": shape_petal,
    "KRod1": lambda: shape_rod(ROD_A["KRod1"]),
    "KRod2": lambda: shape_rod(ROD_A["KRod2"]),
    "KRod3": lambda: shape_rod(ROD_A["KRod3"]),
    "KGem": shape_gem,
    "KRing1": lambda: shape_ring(RING_K["KRing1"]),
    "KRing2": lambda: shape_ring(RING_K["KRing2"]),
    "KRing3": lambda: shape_ring(RING_K["KRing3"]),
}


def _fix(verts, faces):
    faces = fix_winding(verts, faces)
    # outward: the centroid test - flip all if the signed volume is negative
    vol = 0.0
    for fc in faces:
        a = Vector(verts[fc[0]])
        for k in range(1, len(fc) - 1):
            b, c = Vector(verts[fc[k]]), Vector(verts[fc[k + 1]])
            vol += a.dot(b.cross(c))
    if vol < 0:
        faces = [tuple(reversed(fc)) for fc in faces]
    return faces


def build_kit_shapes(export=True, spread=False):
    coll = weapon_collection("KitShapes")
    out = {}
    for i, (name, fn) in enumerate(SHAPES.items()):
        v, f = fn()
        v = normalise(v)
        f = _fix(v, f)
        g = Geo()
        g.add(v, f, vertex_normals(v, f))
        ob = make_object("SB_" + name, g, [200, 200, 200], "SmoothPlastic", coll)
        if spread:
            ob.location = ((i % 5) * 1.6, 0, -(i // 5) * 1.8)
        out[name] = g.tris()
    if export:
        coll.hide_viewport = False
        coll.hide_render = False
        bpy.ops.object.select_all(action='DESELECT')
        for o in coll.objects:
            o.hide_set(False)
            o.select_set(True)
        bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, "SB_KitShapes.glb"), export_format='GLB',
                                  use_selection=True, export_yup=True, export_apply=True,
                                  export_materials='NONE', export_normals=True, export_texcoords=False)
    json.dump(out, open(os.path.join(KIT_ROOT, "kit_shapes.json"), "w"), indent=1)
    return out

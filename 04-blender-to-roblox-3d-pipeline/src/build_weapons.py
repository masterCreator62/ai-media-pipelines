# Sugar Bloom - smooth weapon meshes (20.11.2026).
# Run inside Blender 5.3 (MCP):  exec(open(r"H:\RobloxSweetGarden\meshes\build_weapons.py").read())
# then call build_all() / build_one("SharkGun") / export_all().
#
# Everything is generated in ROBLOX space (x right, y up, -z forward; studs) and converted to Blender
# (x, -z, y) only when objects are created. glTF export with +Y up turns that back into Roblox axes,
# and a GLB in metres imports at 1 m = 1 stud.
#
# Each weapon becomes a few mesh pieces, one per colour+material group, so Skins.recolor keeps working
# per piece. meta.json records each piece's Roblox bbox centre/size (MeshPart pos/size in Handle space).
import bpy, bmesh, json, math, os
from mathutils import Matrix, Vector

ROOT = r"H:\RobloxSweetGarden\meshes"
SPECS = os.path.join(ROOT, "specs.json")
OUT = os.path.join(ROOT, "glb")
os.makedirs(OUT, exist_ok=True)

C0 = Matrix(((1, 0, 0), (0, 0, -1), (0, 1, 0)))  # roblox -> blender
# Import 3D turns every GLB 180 deg about Y; pre-turn the export so the uploaded mesh matches Roblox space
TURN = Matrix(((-1, 0, 0), (0, 1, 0), (0, 0, -1)))
C = C0 @ TURN


def rxm(a):
    c, s = math.cos(a), math.sin(a)
    return Matrix(((1, 0, 0), (0, c, -s), (0, s, c)))


def rym(a):
    c, s = math.cos(a), math.sin(a)
    return Matrix(((c, 0, s), (0, 1, 0), (-s, 0, c)))


def rzm(a):
    c, s = math.cos(a), math.sin(a)
    return Matrix(((c, -s, 0), (s, c, 0), (0, 0, 1)))


def part_matrix(p):
    R = Matrix.Identity(3)
    if p.get("yaw"):
        R = R @ rym(math.radians(p["yaw"]))
    r = p.get("rot") or [0, 0, 0]
    if any(r):
        R = R @ rxm(math.radians(r[0])) @ rym(math.radians(r[1])) @ rzm(math.radians(r[2]))
    return R


# ------------------------------------------------------------------ geometry accumulators

class Geo:
    """verts/faces in roblox space; optional per-vertex custom normals."""

    def __init__(self):
        self.v = []
        self.f = []
        self.n = None  # list of normals, same length as v, or None

    def add(self, verts, faces, normals=None):
        base = len(self.v)
        if normals is not None or self.n is not None:
            if self.n is None:
                self.n = [None] * len(self.v)
            self.n.extend(normals if normals is not None else [None] * len(verts))
        self.v.extend([tuple(x) for x in verts])
        self.f.extend([tuple(i + base for i in fc) for fc in faces])

    def tris(self):
        return sum(len(fc) - 2 for fc in self.f)


def bm_extract(bm, M=None, pos=(0, 0, 0)):
    bm.verts.ensure_lookup_table()
    idx = {v: i for i, v in enumerate(bm.verts)}
    P = Vector(pos)
    verts = []
    for v in bm.verts:
        co = v.co.copy()
        if M is not None:
            co = M @ co
        verts.append(tuple(co + P))
    faces = [tuple(idx[v] for v in f.verts) for f in bm.faces]
    return verts, faces


def bevel_all(bm, offset, segments):
    if offset <= 0.0005:
        return
    bmesh.ops.bevel(bm, geom=list(bm.edges) + list(bm.verts), offset=offset, offset_type='OFFSET',
                    profile_type='SUPERELLIPSE', segments=segments, profile=0.5, affect='EDGES',
                    clamp_overlap=True)


def prim_block(size, bev=None, seg=None):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = Vector((v.co.x * size[0], v.co.y * size[1], v.co.z * size[2]))
    mn = min(size)
    if bev is None:
        # soft "toy" edges: big bodies get round shoulders, thin plates stay crisp
        bev = min(0.12, 0.28 * mn) if mn > 0.2 else min(0.05, 0.22 * mn)
    if seg is None:
        seg = 3 if mn > 0.25 else (2 if mn > 0.12 else 1)
        seg = min(seg, LITE[0].get("block_seg", 9))
    bevel_all(bm, bev, seg)
    return bm


def prim_wedge(size, bev=None, seg=None):
    # roblox WedgePart: full bottom face, full back face (+z), slope from top-back to bottom-front
    x, y, z = size[0] / 2, size[1] / 2, size[2] / 2
    bm = bmesh.new()
    vs = [bm.verts.new(c) for c in [(-x, -y, -z), (x, -y, -z), (x, -y, z), (-x, -y, z), (-x, y, z), (x, y, z)]]
    for f in [(0, 3, 2, 1), (3, 4, 5, 2), (0, 1, 5, 4), (0, 4, 3), (1, 2, 5)]:
        bm.faces.new([vs[i] for i in f])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mn = min(size)
    if bev is None:
        bev = min(0.08, 0.2 * mn) if mn > 0.2 else min(0.04, 0.18 * mn)
    if seg is None:
        seg = 3 if mn > 0.25 else (2 if mn > 0.12 else 1)
        seg = min(seg, LITE[0].get("block_seg", 9))
    bevel_all(bm, bev, seg)
    return bm


def prim_cyl(length, d, segs=None, bseg=None):
    # along local X (roblox cylinder rule)
    bm = bmesh.new()
    if segs is None:
        segs = 24 if d > 0.5 else (16 if d > 0.15 else 10)
        segs = max(8, round(segs * LITE[0].get("cyl_k", 1.0)))
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=segs, radius1=d / 2, radius2=d / 2, depth=length)
    # cone is along Z -> turn to X
    bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=rym(math.radians(90)))
    rim = [e for e in bm.edges if len(e.link_faces) == 2 and abs(e.link_faces[0].normal.dot(e.link_faces[1].normal)) < 0.5]
    off = min(0.045, 0.22 * min(length, d))
    if off > 0.003:
        bmesh.ops.bevel(bm, geom=rim, offset=off, offset_type='OFFSET', profile_type='SUPERELLIPSE',
                        segments=bseg or (2 if d > 0.15 else 1), profile=0.5, affect='EDGES', clamp_overlap=True)
    return bm


BALL_K = [1.0]  # segment factor for balls (per-weapon LIGHT "ball_seg")
# per-weapon lightening knobs (22.11.2026, triangle budget 6000), set by build_one from LIGHT[wid]:
#   block_seg - most bevel segments on blocks/wedges, cyl_k - factor on cylinder segments,
#   wing_dens - Big Bee wing outline density, pumpkin_u - Pumpkin Shotgun rib segments
LITE = [{}]


def prim_ball(d):
    bm = bmesh.new()
    u, v = (20, 12) if d > 0.5 else ((14, 9) if d > 0.15 else (10, 6))
    u, v = max(8, round(u * BALL_K[0])), max(6, round(v * BALL_K[0]))
    bmesh.ops.create_uvsphere(bm, u_segments=u, v_segments=v, radius=d / 2)
    return bm


def prim_softbox(size, round_frac=0.44, seg=3, puff=0.07, cuts=4):
    """molded gun body: very round edges (pill-like) and a slight bulge along the long axis,
    so receivers, slides, stocks and grips read as cast plastic instead of boxes"""
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = Vector((v.co.x * size[0], v.co.y * size[1], v.co.z * size[2]))
    mn = min(size)
    bevel_all(bm, round_frac * mn, seg)
    L = max(range(3), key=lambda i: size[i])
    half = size[L] / 2
    nrm = [0, 0, 0]
    nrm[L] = 1
    for k in range(1, cuts):
        c = [0, 0, 0]
        c[L] = -half + size[L] * k / cuts
        geom = list(bm.verts) + list(bm.edges) + list(bm.faces)
        bmesh.ops.bisect_plane(bm, geom=geom, plane_co=c, plane_no=nrm, clear_inner=False, clear_outer=False)
    for v in bm.verts:
        t = v.co[L] / half if half > 0 else 0
        f = 1 + puff * (1 - min(1.0, t * t))
        for i in range(3):
            if i != L:
                v.co[i] *= f
    return bm


def part_geo(p):
    s = p["size"]
    sh = p["shape"]
    if sh == "Block" and p.get("_soft"):
        bm = prim_softbox(s)
    elif sh == "Block":
        bm = prim_block(s)
    elif sh == "Wedge":
        bm = prim_wedge(s)
    elif sh == "Cylinder":
        bm = prim_cyl(s[0], min(s[1], s[2]))
    elif sh == "Ball":
        bm = prim_ball(min(s))
    else:
        bm = prim_block(s)
    verts, faces = bm_extract(bm, part_matrix(p), p["pos"])
    bm.free()
    return verts, faces


def gkey(color, mat, tr):
    return (tuple(int(c) for c in color), mat, round(tr or 0, 3))


# ------------------------------------------------------------------ cast bodies (v3): one molded surface per colour group

CAST = {"voxel": 0.032, "smooth_iter": 4, "smooth_fac": 0.6, "group_budget": 1800, "min_tris": 260, "density": 0.085, "fillet": 0.045}


# per-weapon triangle diet (22.11.2026): CactusSniper was 8086 tris -> lighter cast surfaces + petals
LIGHT = {"CactusSniper": {"density": 0.052, "group_budget": 1000, "ball_seg": 0.6},
         "StormStaff": {"block_seg": 2, "cyl_k": 0.55, "ball_seg": 0.6},
         "SunflowerStaff": {"block_seg": 2, "cyl_k": 0.7, "ball_seg": 0.7},
         "ThunderMallet": {"block_seg": 2},
         "BigBee": {"density": 0.072, "wing_dens": 2, "ball_seg": 0.8},
         "PumpkinShotgun": {"density": 0.072, "pumpkin_u": 20, "ball_seg": 0.8}}


def cast_candidate(p):
    """big solid parts of a gun body: these fuse into one cast surface instead of separate pillows"""
    s = p["size"]
    if p.get("mat") == "Neon" or (p.get("transparency") or 0) > 0:
        return False
    if p["shape"] in ("Block", "Wedge"):
        return min(s) >= 2.4 * CAST["voxel"] and max(s) >= 0.18
    if p["shape"] == "Cylinder":
        return min(s[1], s[2]) >= 0.24 and s[0] >= 0.18
    return False


def area_normals(verts, faces):
    acc = [Vector((0, 0, 0)) for _ in verts]
    for fc in faces:
        a = Vector(verts[fc[0]])
        for k in range(1, len(fc) - 1):
            b, c = Vector(verts[fc[k]]), Vector(verts[fc[k + 1]])
            n = (b - a).cross(c - a)  # length = 2*area -> area weighting for free
            for i in (fc[0], fc[k], fc[k + 1]):
                acc[i] += n
    return [tuple(n.normalized()) if n.length > 1e-12 else (0, 1, 0) for n in acc]


def cast_geo(geo, voxel=None, budget=None, cfg=None):
    """voxel-remesh the union of a group's blocks -> smooth -> decimate. Returns (verts, faces, normals)."""
    CAST = cfg or globals()["CAST"]
    voxel = voxel or CAST["voxel"]
    me = bpy.data.meshes.new("_tmp_cast")
    me.from_pydata(geo.v, [], geo.f)
    me.update()
    ob = bpy.data.objects.new("_tmp_cast", me)
    bpy.context.scene.collection.objects.link(ob)
    rm = ob.modifiers.new("rm", 'REMESH')
    rm.mode = 'VOXEL'
    rm.voxel_size = voxel
    rm.adaptivity = 0.0
    fil = CAST.get("fillet", 0)
    if fil > 0:
        # morphological closing: grow, re-voxelize (fills the inner corners), shrink back -> fillets in the joints
        d1 = ob.modifiers.new("grow", 'DISPLACE')
        d1.mid_level, d1.strength, d1.direction = 0.0, fil, 'NORMAL'
        rm2 = ob.modifiers.new("rm2", 'REMESH')
        rm2.mode, rm2.voxel_size, rm2.adaptivity = 'VOXEL', voxel, 0.0
        sm0 = ob.modifiers.new("sm0", 'SMOOTH')
        sm0.factor, sm0.iterations = 0.5, 2
        d2 = ob.modifiers.new("shrink", 'DISPLACE')
        d2.mid_level, d2.strength, d2.direction = 0.0, -fil, 'NORMAL'
    sm = ob.modifiers.new("sm", 'SMOOTH')
    sm.factor = CAST["smooth_fac"]
    sm.iterations = CAST["smooth_iter"]
    dg = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(dg)
    m2 = ev.to_mesh()
    tri_now = sum(len(p.vertices) - 2 for p in m2.polygons)
    ev.to_mesh_clear()
    target = budget or max(CAST["min_tris"], min(CAST["group_budget"], int(tri_now * CAST["density"])))
    if tri_now > target:
        dc = ob.modifiers.new("dc", 'DECIMATE')
        dc.decimate_type = 'COLLAPSE'
        dc.ratio = max(0.01, target / tri_now)
        dc.use_collapse_triangulate = True
        dg = bpy.context.evaluated_depsgraph_get()
        ev = ob.evaluated_get(dg)
    m2 = ev.to_mesh()
    vv = [tuple(v.co) for v in m2.vertices]
    ff = [tuple(p.vertices) for p in m2.polygons]
    ev.to_mesh_clear()
    bpy.data.objects.remove(ob)
    bpy.data.meshes.remove(me)
    return vv, ff, area_normals(vv, ff), tri_now


# ------------------------------------------------------------------ generic weapon: smooth copy of the part list

def groups_from_spec(spec, include_handle=True):
    groups = {}
    parts = list(spec["parts"])
    if include_handle:
        h = spec["handle"]
        parts.insert(0, {"shape": "Block", "size": h["size"], "pos": [0, 0, 0], "rot": [0, 0, 0], "yaw": 0,
                         "color": h.get("color", [28, 28, 32]), "mat": h.get("mat", "SmoothPlastic"), "transparency": 0})
    cast_kind = spec.get("kind") == "gun"
    cast_in = {}
    BALL_K[0] = LIGHT.get(spec.get("id"), {}).get("ball_seg", 1.0)
    for p in parts:
        k = gkey(p["color"], p.get("mat", "SmoothPlastic"), p.get("transparency", 0))
        g = groups.setdefault(k, Geo())
        if cast_kind and cast_candidate(p):
            # near-sharp input: the voxel remesh + smoothing makes the soft edges and fuses the joints
            s = p["size"]
            if p["shape"] == "Block":
                bm = prim_block(s, bev=min(0.03, 0.15 * min(s)), seg=1)
            elif p["shape"] == "Wedge":
                bm = prim_wedge(s, bev=min(0.03, 0.15 * min(s)), seg=1)
            else:
                bm = prim_cyl(s[0], min(s[1], s[2]), segs=32)
            v, f = bm_extract(bm, part_matrix(p), p["pos"])
            bm.free()
            cast_in.setdefault(k, Geo()).add(v, f)
            continue
        v, f = part_geo(p)
        g.add(v, f)
    cfg = dict(CAST, **LIGHT.get(spec.get("id"), {}))
    for k, cg in cast_in.items():
        vv, ff, nn, raw = cast_geo(cg, cfg=cfg)
        groups[k].add(vv, ff, nn)
        groups[k].cast_raw = getattr(groups[k], "cast_raw", 0) + raw
    return groups


# ------------------------------------------------------------------ subdivision helper

def subsurf(verts, faces, levels, mat_idx=None):
    me = bpy.data.meshes.new("_tmp_ss")
    me.from_pydata(verts, [], faces)
    if mat_idx is not None:
        me.polygons.foreach_set("material_index", mat_idx)
    me.update()
    ob = bpy.data.objects.new("_tmp_ss", me)
    bpy.context.scene.collection.objects.link(ob)
    mod = ob.modifiers.new("ss", 'SUBSURF')
    mod.levels = levels
    mod.render_levels = levels
    dg = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(dg)
    m2 = ev.to_mesh()
    vv = [tuple(v.co) for v in m2.vertices]
    ff = [tuple(p.vertices) for p in m2.polygons]
    mi = [p.material_index for p in m2.polygons]
    ev.to_mesh_clear()
    bpy.data.objects.remove(ob)
    bpy.data.meshes.remove(me)
    return vv, ff, mi


def vertex_normals(verts, faces):
    me = bpy.data.meshes.new("_tmp_n")
    me.from_pydata(verts, [], faces)
    me.update()
    ns = [tuple(v.normal) for v in me.vertices]
    bpy.data.meshes.remove(me)
    return ns


def split_by_mat(verts, faces, mi, normals):
    """-> {mat_index: (verts, faces, normals)} with compacted indices"""
    out = {}
    for fc, m in zip(faces, mi):
        out.setdefault(m, []).append(fc)
    res = {}
    for m, fl in out.items():
        remap = {}
        vv, nn, ff = [], [], []
        for fc in fl:
            nf = []
            for i in fc:
                if i not in remap:
                    remap[i] = len(vv)
                    vv.append(verts[i])
                    nn.append(normals[i])
                nf.append(remap[i])
            ff.append(tuple(nf))
        res[m] = (vv, ff, nn)
    return res


# ------------------------------------------------------------------ hero: Shark Gun

GUN = [52, 54, 60]
DARK = [28, 28, 32]
BRASS = [214, 170, 72]
WHITE = [245, 245, 245]


def loft(stations, n=24, belly_arc=None):
    """stations: (z, halfW, halfH, cy). Closed spindle with pole caps. -> verts, faces, mat_idx"""
    verts, faces, mi = [], [], []
    tip0 = stations[0]
    tip1 = stations[-1]
    verts.append((0, tip0[3], tip0[0] + 0.0))  # back pole
    rings = []
    for (z, hw, hh, cy) in stations:
        ring = []
        for k in range(n):
            a = 2 * math.pi * k / n
            # superellipse-ish: slightly flatter belly
            sx, sy = math.cos(a), math.sin(a)
            yy = sy * hh * (0.92 if sy < 0 else 1.0)
            ring.append(len(verts))
            verts.append((sx * hw, cy + yy, z))
        rings.append(ring)
    front = len(verts)
    verts.append((0, tip1[3], tip1[0]))

    def is_belly(k):
        a = 2 * math.pi * (k + 0.5) / n
        deg = math.degrees(a) % 360
        return belly_arc is not None and belly_arc[0] <= deg <= belly_arc[1]

    r0 = rings[0]
    for k in range(n):
        faces.append((0, r0[(k + 1) % n], r0[k]))
        mi.append(1 if is_belly(k) else 0)
    for i in range(len(rings) - 1):
        a, b = rings[i], rings[i + 1]
        for k in range(n):
            faces.append((a[k], a[(k + 1) % n], b[(k + 1) % n], b[k]))
            mi.append(1 if is_belly(k) else 0)
    rl = rings[-1]
    for k in range(n):
        faces.append((front, rl[k], rl[(k + 1) % n]))
        mi.append(1 if is_belly(k) else 0)
    return verts, faces, mi


def pillow(outline2d, origin, u, v, w, thick, inner=0.62):
    """flat fin with thin edges: outline in (u,v) plane coords, thickness along w. -> verts, faces"""
    O, U, V, W = Vector(origin), Vector(u).normalized(), Vector(v).normalized(), Vector(w).normalized()
    cx = sum(p[0] for p in outline2d) / len(outline2d)
    cy = sum(p[1] for p in outline2d) / len(outline2d)
    n = len(outline2d)
    verts = []
    for (a, b) in outline2d:
        verts.append(tuple(O + U * a + V * b))
    for side in (1, -1):
        for (a, b) in outline2d:
            ia, ib = cx + (a - cx) * inner, cy + (b - cy) * inner
            verts.append(tuple(O + U * ia + V * ib + W * (side * thick / 2)))
        verts.append(tuple(O + U * cx + V * cy + W * (side * thick / 2)))
    faces = []
    for si, side in enumerate((1, -1)):
        base = n + si * (n + 1)
        c = base + n
        for k in range(n):
            k2 = (k + 1) % n
            q = (k, k2, base + k2, base + k)
            faces.append(q if side == 1 else tuple(reversed(q)))
            t = (base + k, base + k2, c)
            faces.append(t if side == 1 else tuple(reversed(t)))
    return verts, faces


def densify(outline, k=2):
    """closed Catmull-Rom: k-1 extra points between every pair, so a level-1 subdivision stays round"""
    n = len(outline)
    out = []
    for i in range(n):
        p0, p1, p2, p3 = (Vector(outline[(i + j) % n]) for j in (-1, 0, 1, 2))
        for s in range(k):
            t = s / k
            q = 0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3)
            out.append((q.x, q.y))
    return out


def fix_winding(verts, faces):
    bm = bmesh.new()
    vs = [bm.verts.new(v) for v in verts]
    for fc in faces:
        try:
            bm.faces.new([vs[i] for i in fc])
        except ValueError:
            pass
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.verts.index_update()
    out = [tuple(v.index for v in f.verts) for f in bm.faces]
    bm.free()
    return out


def smooth_piece(verts, faces, levels=2):
    faces = fix_winding(verts, faces)
    vv, ff, _ = subsurf(verts, faces, levels)
    return vv, ff, vertex_normals(vv, ff)


def shark_groups():
    shark = [112, 136, 162]
    dshark = [84, 104, 128]
    belly = [236, 238, 242]
    mouth = [128, 32, 44]
    G = {}

    def put(color, mat, verts, faces, normals=None, tr=0):
        G.setdefault(gkey(color, mat, tr), Geo()).add(verts, faces, normals)

    # body: z from tail (+) to snout (-); (z, halfW, halfH, centreY)
    st = [
        (1.42, 0.05, 0.07, 1.02),
        (1.20, 0.16, 0.20, 1.00),
        (0.80, 0.30, 0.36, 0.99),
        (0.20, 0.52, 0.58, 0.97),
        (-0.55, 0.71, 0.72, 0.95),
        (-1.40, 0.77, 0.75, 0.94),
        (-2.25, 0.73, 0.70, 0.93),
        (-2.95, 0.63, 0.60, 0.93),
        (-3.50, 0.50, 0.48, 0.95),
        (-3.92, 0.34, 0.33, 0.99),
        (-4.18, 0.17, 0.17, 1.03),
        (-4.30, 0.05, 0.05, 1.05),
    ]
    v, f, mi = loft(st, n=16, belly_arc=(212, 328))
    vv, ff, mm = subsurf(v, f, 1, mi)
    nn = vertex_normals(vv, ff)
    for m, (a, b, c) in split_by_mat(vv, ff, mm, nn).items():
        put(belly if m == 1 else shark, "SmoothPlastic", a, b, c)

    # dorsal fin (swept back, concave trailing edge), in the x=0 plane: (z, y)
    dors = [(-1.75, 1.55), (-1.2, 1.80), (-0.55, 2.25), (0.05, 2.55), (-0.05, 2.30), (-0.15, 2.0), (-0.12, 1.72), (0.05, 1.55)]
    a, b = pillow(densify(dors, 3), (0, 0, 0), (0, 0, 1), (0, 1, 0), (1, 0, 0), 0.16)
    put(dshark, "SmoothPlastic", *smooth_piece(a, b, 0))
    # small second dorsal near the tail
    d2 = [(0.55, 1.30), (0.80, 1.42), (1.00, 1.62), (0.98, 1.45), (1.02, 1.28)]
    a, b = pillow(densify(d2, 3), (0, 0, 0), (0, 0, 1), (0, 1, 0), (1, 0, 0), 0.09)
    put(dshark, "SmoothPlastic", *smooth_piece(a, b, 0))
    # caudal fin: crescent, upper lobe longer
    tail = [(1.15, 1.00), (1.45, 1.35), (1.80, 1.85), (2.02, 2.15), (1.85, 1.70), (1.70, 1.25), (1.65, 1.00),
            (1.72, 0.72), (1.92, 0.42), (1.70, 0.55), (1.40, 0.75)]
    a, b = pillow(densify(tail, 3), (0, 0, 0), (0, 0, 1), (0, 1, 0), (1, 0, 0), 0.14)
    put(dshark, "SmoothPlastic", *smooth_piece(a, b, 0))
    # pectoral fins: sweep out, down and back from the lower flank
    for sx in (1, -1):
        out = Vector((sx * 1.0, -0.42, 0.0)).normalized()
        back = Vector((0, -0.10, 1.0)).normalized()
        w = out.cross(back) * sx
        pec = [(0.0, -0.35), (0.0, 0.35), (0.45, 0.45), (0.85, 0.75), (1.0, 0.95), (0.75, 0.55), (0.4, 0.05)]
        a, b = pillow(densify(pec, 3), (sx * 0.52, 0.52, -2.05), tuple(out), tuple(back), tuple(w), 0.11)
        put(dshark, "SmoothPlastic", *smooth_piece(a, b, 0))
        # anal/pelvic fin small
        out2 = Vector((sx * 0.6, -1.0, 0)).normalized()
        pel = [(0.0, -0.15), (0.0, 0.18), (0.30, 0.32), (0.22, 0.05)]
        a, b = pillow(densify(pel, 3), (sx * 0.22, 0.42, 0.25), tuple(out2), (0, 0, 1), tuple(out2.cross(Vector((0, 0, 1)))), 0.07)
        put(dshark, "SmoothPlastic", *smooth_piece(a, b, 0))

    # gills: three soft slits on each flank (darker), just proud of the surface
    # surface half-width of the body at depth z (linear between loft stations)
    def body_hw(z):
        for (z0, w0, _, _), (z1, w1, _, _) in zip(st, st[1:]):
            if z1 <= z <= z0:
                t = (z - z0) / (z1 - z0)
                return w0 + (w1 - w0) * t
        return 0.3

    for sx in (1, -1):
        for i in range(3):
            z = -2.70 + i * 0.19
            hw = body_hw(z)
            bm = bmesh.new()
            bmesh.ops.create_uvsphere(bm, u_segments=8, v_segments=5, radius=0.5)
            for vt in bm.verts:
                vt.co = Vector((vt.co.x * 0.05, vt.co.y * (0.50 - i * 0.04), vt.co.z * 0.055))
            M = rxm(math.radians(-14))  # slanted back like real gill slits
            a, b = bm_extract(bm, M, (0, 0.97, z))
            bm.free()
            # wrap onto the body: x = surface(y, z) + local x
            hh, cy = 0.70, 0.93
            a2 = []
            for (x, y, zz) in a:
                surf = body_hw(zz) * math.sqrt(max(0.0, 1 - ((y - cy) / hh) ** 2))
                a2.append((sx * (surf - 0.01 + x), y, zz))
            a = a2
            if sx < 0:
                b = [tuple(reversed(fc)) for fc in b]
            put([40, 48, 60], "SmoothPlastic", a, b, vertex_normals(a, b))

    # eyes: glossy black with a glowing glint
    for sx in (1, -1):
        bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=12, v_segments=8, radius=0.13)
        a, b = bm_extract(bm, None, (sx * 0.43, 1.17, -3.42))
        bm.free()
        put(DARK, "Glass", a, b, vertex_normals(a, b))
        bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=8, v_segments=5, radius=0.04)
        a, b = bm_extract(bm, None, (sx * 0.53, 1.22, -3.47))
        bm.free()
        put(WHITE, "Neon", a, b, vertex_normals(a, b))

    # mouth cavity + lower jaw
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=16, v_segments=10, radius=0.5)
    for vt in bm.verts:
        vt.co = Vector((vt.co.x * 0.74, vt.co.y * 0.40, vt.co.z * 0.86))
    a, b = bm_extract(bm, None, (0, 0.80, -3.86))
    bm.free()
    put(mouth, "SmoothPlastic", a, b, vertex_normals(a, b))
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=16, v_segments=10, radius=0.5)
    for vt in bm.verts:
        vt.co = Vector((vt.co.x * 0.78, vt.co.y * 0.26, vt.co.z * 0.84))
    a, b = bm_extract(bm, None, (0, 0.60, -3.62))
    bm.free()
    put(belly, "SmoothPlastic", a, b, vertex_normals(a, b))

    # teeth: small curved cones round the mouth rim
    def tooth(base, down, h=0.13, r=0.045):
        bm = bmesh.new()
        bmesh.ops.create_cone(bm, cap_ends=True, segments=6, radius1=r, radius2=0.004, depth=h)
        # cone along +z; point it along `down`
        d = Vector(down).normalized()
        q = Vector((0, 0, 1)).rotation_difference(d)
        M = q.to_matrix()
        a, b = bm_extract(bm, M, tuple(Vector(base) + d * (h / 2)))
        bm.free()
        return a, b

    for i in range(7):
        t = math.radians(-60 + i * 20)
        x, z = 0.33 * math.sin(t), -3.86 - 0.37 * math.cos(t)
        a, b = tooth((x, 0.93, z), (0, -1, -0.15))
        put(WHITE, "SmoothPlastic", a, b, vertex_normals(a, b))
        a, b = tooth((x * 0.95, 0.68, z + 0.02), (0, 1, -0.15), h=0.11)
        put(WHITE, "SmoothPlastic", a, b, vertex_normals(a, b))

    # rotary barrels in the mouth
    metal = Geo()

    def cylZ(length, d, x, y, z, segs=None):
        bm = prim_cyl(length, d, segs, 1)
        a, b = bm_extract(bm, rym(math.radians(90)), (x, y, z))
        bm.free()
        metal.add(a, b)

    cylZ(0.40, 0.50, 0, 0.80, -3.98, 12)     # housing
    cylZ(0.10, 0.56, 0, 0.80, -4.17, 12)     # collar
    for i in range(6):
        ang = math.radians(i * 60)
        cylZ(0.78, 0.11, math.cos(ang) * 0.16, 0.80 + math.sin(ang) * 0.16, -4.50, 6)
    cylZ(0.62, 0.12, 0, 0.80, -4.45, 8)     # spindle
    cylZ(0.07, 0.50, 0, 0.80, -4.80, 12)     # front ring
    # (mid ring dropped for the triangle budget)
    put(GUN, "Metal", metal.v, metal.f)

    # ammo drum on the right flank and a belt of rounds feeding the body
    drum = Geo()
    bm = prim_cyl(0.46, 0.92, 14, 1)
    a, b = bm_extract(bm, None, (0.98, 0.50, -0.62))
    bm.free()
    drum.add(a, b)
    put(GUN, "Metal", drum.v, drum.f)
    brass = Geo()
    bm = prim_cyl(0.49, 0.48, 14, 1)
    a, b = bm_extract(bm, None, (0.98, 0.50, -0.62))
    bm.free()
    brass.add(a, b)
    put(BRASS, "Metal", brass.v, brass.f)
    # curved feed chute from the top of the drum into the flank
    P0, P1, P2 = Vector((0.98, 0.90, -0.80)), Vector((1.00, 1.20, -1.02)), Vector((0.70, 1.14, -1.36))
    nseg, nr = 8, 6
    cv, cf = [], []
    for i in range(nseg + 1):
        t = i / nseg
        pt = (1 - t) ** 2 * P0 + 2 * (1 - t) * t * P1 + t * t * P2
        tg = (2 * (1 - t) * (P1 - P0) + 2 * t * (P2 - P1)).normalized()
        side = tg.cross(Vector((0, 1, 0)))
        if side.length < 1e-4:
            side = Vector((1, 0, 0))
        side.normalize()
        up = side.cross(tg).normalized()
        for k in range(nr):
            a_ = 2 * math.pi * k / nr
            cv.append(tuple(pt + side * (math.cos(a_) * 0.10) + up * (math.sin(a_) * 0.065)))
    for i in range(nseg):
        for k in range(nr):
            k2 = (k + 1) % nr
            cf.append((i * nr + k, i * nr + k2, (i + 1) * nr + k2, (i + 1) * nr + k))
    put(GUN, "Metal", cv, cf)

    # pistol grip (replaces the box handle), trigger guard and trigger
    grip = Geo()
    gv = [(0, -0.5, -0.06), (0, -0.25, -0.02), (0, 0.0, 0.0), (0, 0.25, 0.04), (0, 0.48, 0.06)]
    ring = []
    v2, f2 = [], []
    for j, (_, y, zc) in enumerate(gv):
        w = 0.18 if j < 4 else 0.2
        d = 0.27 - 0.02 * abs(j - 2)
        for k in range(12):
            a_ = 2 * math.pi * k / 12
            v2.append((math.cos(a_) * w, y, zc + math.sin(a_) * d))
    v2.append((0, -0.56, -0.06))
    v2.append((0, 0.52, 0.06))
    nring = len(gv)
    for j in range(nring - 1):
        for k in range(12):
            k2 = (k + 1) % 12
            f2.append((j * 12 + k, j * 12 + k2, (j + 1) * 12 + k2, (j + 1) * 12 + k))
    bot, top = nring * 12, nring * 12 + 1
    for k in range(12):
        f2.append((bot, (k + 1) % 12, k))
        f2.append((top, (nring - 1) * 12 + k, (nring - 1) * 12 + (k + 1) % 12))
    tilt = rxm(math.radians(-10))
    v2 = [tuple(tilt @ Vector(p)) for p in v2]
    vv, ff, nn = smooth_piece(v2, f2, 1)
    grip.add(vv, ff, nn)
    put(DARK, "SmoothPlastic", grip.v, grip.f, grip.n)
    # finger ridges on the front of the grip
    for i in range(3):
        bm = bmesh.new()
        bmesh.ops.create_uvsphere(bm, u_segments=8, v_segments=4, radius=0.5)
        for vt in bm.verts:
            vt.co = Vector((vt.co.x * 0.30, vt.co.y * 0.10, vt.co.z * 0.10))
        y = 0.18 - i * 0.2
        p = tilt @ Vector((0, y, -0.25))
        a, b = bm_extract(bm, None, tuple(p))
        bm.free()
        put([40, 40, 46], "SmoothPlastic", a, b, vertex_normals(a, b))
    # trigger guard: a half torus under the body in front of the grip
    segs, tseg = 12, 6
    R0, r0 = 0.20, 0.035
    vv, ff = [], []
    for i in range(segs + 1):
        th = math.pi * i / segs  # 0..pi (lower half loop)
        cx, cy = math.cos(th) * R0, -math.sin(th) * R0
        for k in range(tseg):
            ph = 2 * math.pi * k / tseg
            nx, ny = math.cos(th), -math.sin(th)
            rr = R0 + math.cos(ph) * r0
            vv.append((math.sin(ph) * r0, -math.sin(th) * rr + 0.32, -0.42 + math.cos(th) * rr))
    for i in range(segs):
        for k in range(tseg):
            k2 = (k + 1) % tseg
            ff.append((i * tseg + k, i * tseg + k2, (i + 1) * tseg + k2, (i + 1) * tseg + k))
    put(GUN, "Metal", vv, ff)
    bm = prim_block((0.06, 0.24, 0.07), 0.025, 2)
    a, b = bm_extract(bm, rxm(math.radians(-14)), (0, 0.24, -0.40))
    bm.free()
    put(BRASS, "Metal", a, b)
    return G


HEROES = {"SharkGun": shark_groups}
# hand-built Pea Rifle and Thorn Rifle (22.11.2026): chamfered lofts + boolean cut-outs, weighted normals
exec(open(os.path.join(ROOT, "hero_rifles.py"), encoding="utf-8").read(), globals())
# hand-built Sprout SMG + Seed Pistol (chat efc0449a) and Cactus/Fart/Pumpkin/Big Bee (22.11.2026);
# hero_guns2.py also holds g2_step, used by the Pea/Thorn receivers
exec(open(os.path.join(ROOT, "hero_small.py"), encoding="utf-8").read(), globals())
exec(open(os.path.join(ROOT, "hero_guns2.py"), encoding="utf-8").read(), globals())


# ------------------------------------------------------------------ partial edits: replace a few parts of an auto model

def lobed_ball(center, R, hscale, lobes, depth, u=32, v=16):
    """pumpkin-like ribbed sphere: radius dips between `lobes` ribs, dimpled at the poles"""
    cx, cy, cz = center
    verts, faces = [], []
    verts.append((cx, cy + R * hscale * 0.78, cz))  # top dimple
    for j in range(1, v):
        th = math.pi * j / v
        for i in range(u):
            ph = 2 * math.pi * i / u
            rib = 1 - depth * (1 - abs(math.cos(lobes * ph / 2)) ** 0.6)
            r = R * rib * math.sin(th)
            y = R * hscale * math.cos(th) * (0.92 if j < 3 or j > v - 3 else 1.0)
            verts.append((cx + r * math.cos(ph), cy + y, cz + r * math.sin(ph)))
    verts.append((cx, cy - R * hscale * 0.82, cz))
    last = len(verts) - 1
    for i in range(u):
        faces.append((0, 1 + (i + 1) % u, 1 + i))
    for j in range(v - 2):
        a, b = 1 + j * u, 1 + (j + 1) * u
        for i in range(u):
            i2 = (i + 1) % u
            faces.append((a + i, a + i2, b + i2, b + i))
    base = 1 + (v - 2) * u
    for i in range(u):
        faces.append((last, base + i, base + (i + 1) % u))
    return verts, faces


def pumpkin_edit(spec):
    drop = set()
    for i, p in enumerate(spec["parts"]):
        c, pos = p["color"], p["pos"]
        near = abs(pos[2] + 0.25) < 0.6 and 0.8 < pos[1] < 1.4
        if near and ((c[0] > 190 and c[2] < 60 and p["shape"] in ("Ball", "Block")) or p.get("mat") == "Neon"):
            drop.add(i)
    kept = dict(spec)
    kept["parts"] = [p for i, p in enumerate(spec["parts"]) if i not in drop]
    G = {}
    v, f = lobed_ball((0, 1.08, -0.25), 0.5, 0.86, 8, 0.10, u=LITE[0].get("pumpkin_u", 24), v=10)
    vv, ff, nn = smooth_piece(v, f, 1)
    G.setdefault(gkey([238, 132, 32], "SmoothPlastic", 0), Geo()).add(vv, ff, nn)
    glow = G.setdefault(gkey([255, 220, 90], "Neon", 0), Geo())
    # jack-o'-lantern face on the front (-z) surface
    for sx in (1, -1):
        a, b = pillow([(-0.08, -0.05), (0.08, -0.05), (0.0, 0.08)], (sx * 0.15, 1.15, -0.715), (1, 0, 0), (0, 1, 0), (0, 0, 1), 0.05, 0.5)
        glow.add(a, b)
    mouth = [(-0.20, 0.02), (-0.12, -0.04), (-0.06, 0.01), (0.0, -0.05), (0.06, 0.01), (0.12, -0.04), (0.20, 0.02),
             (0.14, -0.08), (0.0, -0.11), (-0.14, -0.08)]
    a, b = pillow(mouth, (0, 0.97, -0.725), (1, 0, 0), (0, 1, 0), (0, 0, 1), 0.05, 0.4)
    glow.add(a, b)
    return kept, G


def bee_edit(spec):
    # flat glass rectangles -> two veined insect wings per side (fore + hind), same glass colour
    drop = {i for i, p in enumerate(spec["parts"]) if p.get("mat") == "Glass"}
    glass = [p for i, p in enumerate(spec["parts"]) if i in drop]
    kept = dict(spec)
    kept["parts"] = [p for i, p in enumerate(spec["parts"]) if i not in drop]
    G = {}
    tr = glass[0].get("transparency", 0.45) if glass else 0.45
    col = glass[0]["color"] if glass else [220, 240, 255]
    wing = G.setdefault(gkey(col, "Glass", tr), Geo())
    for sx in (1, -1):
        root = Vector((sx * 0.14, 1.0, -0.45))
        for (length, width, sweep, tilt) in ((0.95, 0.40, 18, 32), (0.70, 0.30, 52, 22)):
            out = Vector((sx * math.cos(math.radians(tilt)), math.sin(math.radians(tilt)), 0))
            back = Vector((0, 0, 1))
            # rotate the wing's long axis back by `sweep`
            u = (out * math.cos(math.radians(sweep)) + back * math.sin(math.radians(sweep))).normalized()
            v = back.cross(u) if sx > 0 else u.cross(back)
            v = (back - u * back.dot(u)).normalized()
            w = u.cross(v)
            outline = [(0.0, -0.06), (0.25 * length, -width * 0.42), (0.7 * length, -width * 0.5), (length, -width * 0.15),
                       (0.92 * length, width * 0.2), (0.55 * length, width * 0.32), (0.15 * length, width * 0.14)]
            a, b = pillow(densify(outline, LITE[0].get("wing_dens", 3)), tuple(root), tuple(u), tuple(v), tuple(w), 0.035, 0.7)
            vv, ff, nn = smooth_piece(a, b, 1)
            wing.add(vv, ff, nn)
    return kept, G


EDITS = {"PumpkinShotgun": pumpkin_edit, "BigBee": bee_edit}


# ------------------------------------------------------------------ scene objects + export

MAT_ROUGH = {"Metal": (0.35, 1.0), "Glass": (0.05, 0.0), "Neon": (0.5, 0.0)}


def get_material(color, mat):
    name = "SB_%d_%d_%d_%s" % (color[0], color[1], color[2], mat)
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    lin = [((c / 255) / 12.92) if c / 255 <= 0.04045 else (((c / 255) + 0.055) / 1.055) ** 2.4 for c in color]
    bsdf.inputs["Base Color"].default_value = (lin[0], lin[1], lin[2], 1)
    rough, metal = MAT_ROUGH.get(mat, (0.45, 0.0))
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    if mat == "Neon":
        bsdf.inputs["Emission Color"].default_value = (lin[0], lin[1], lin[2], 1)
        bsdf.inputs["Emission Strength"].default_value = 3.0
    return m


def make_object(name, geo, color, mat, coll, sharp_angle=48):
    vb = [tuple(C @ Vector(p)) for p in geo.v]
    me = bpy.data.meshes.new(name)
    me.from_pydata(vb, [], geo.f)
    me.validate(clean_customdata=False)
    me.update()
    me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    full = geo.n is not None and all(n is not None for n in geo.n) and len(geo.n) == len(me.vertices)
    if getattr(geo, "wn", 0):
        # weighted normals (hero lofts): per corner, area-weighted average of the faces within wn degrees
        me.update()
        cosl = math.cos(math.radians(geo.wn))
        pn = [p.normal.copy() for p in me.polygons]
        pa = [p.area for p in me.polygons]
        vp = [[] for _ in me.vertices]
        for p in me.polygons:
            for vi in p.vertices:
                vp[vi].append(p.index)
        cn = [None] * len(me.loops)
        for p in me.polygons:
            n0 = pn[p.index]
            for li in p.loop_indices:
                acc = Vector((0, 0, 0))
                for q in vp[me.loops[li].vertex_index]:
                    if pn[q].dot(n0) >= cosl:
                        acc += pn[q] * pa[q]
                cn[li] = tuple(acc.normalized()) if acc.length > 1e-12 else tuple(n0)
        me.normals_split_custom_set(cn)
    elif full:
        me.normals_split_custom_set_from_vertices([tuple(C @ Vector(n)) for n in geo.n])
    else:
        bm = bmesh.new()
        bm.from_mesh(me)
        lim = math.radians(sharp_angle)
        given = geo.n if (geo.n is not None and len(geo.n) == len(bm.verts)) else None
        bm.verts.ensure_lookup_table()
        for e in bm.edges:
            if given is not None and given[e.verts[0].index] is not None:
                continue  # cast surface: smooth everywhere, its own normals below
            if len(e.link_faces) == 2 and e.calc_face_angle(0) > lim:
                e.smooth = False
        bm.to_mesh(me)
        bm.free()
        if given is not None:
            # mixed piece: cast surface keeps its area-weighted normals, primitives keep auto (split) normals
            me.update()
            cn = [Vector(c.vector) for c in me.corner_normals]
            lv = [l.vertex_index for l in me.loops]
            for li, vi in enumerate(lv):
                if given[vi] is not None:
                    cn[li] = C @ Vector(given[vi])
            me.normals_split_custom_set([tuple(n) for n in cn])
    me.materials.append(get_material(color, mat))
    ob = bpy.data.objects.new(name, me)
    coll.objects.link(ob)
    return ob


def weapon_collection(wid):
    name = "W_" + wid
    c = bpy.data.collections.get(name)
    if c:
        for o in list(c.objects):
            me = o.data
            bpy.data.objects.remove(o)
            if me and me.users == 0:
                bpy.data.meshes.remove(me)
    else:
        c = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(c)
    return c


def build_one(wid, specs=None):
    specs = specs or json.load(open(SPECS))
    spec = dict(specs[wid], id=wid)
    LITE[0] = LIGHT.get(wid, {})
    BALL_K[0] = LITE[0].get("ball_seg", 1.0)
    if wid in HEROES:
        groups = HEROES[wid]()
    elif wid in EDITS:
        kept, extra = EDITS[wid](spec)
        groups = groups_from_spec(kept)
        for k, g in extra.items():
            if k in groups:
                # mixed normals cannot share one piece: angle-shaded parts get their own smooth normals
                if groups[k].n is None and g.n is not None:
                    g.n = None
            groups.setdefault(k, Geo()).add(g.v, g.f, g.n)
    else:
        groups = groups_from_spec(spec)
    coll = weapon_collection(wid)
    pieces = []
    order = sorted(groups.items(), key=lambda kv: -len(kv[1].v))
    for i, (k, geo) in enumerate(order):
        color, mat, tr = k
        name = "%s_%02d" % (wid, i + 1)
        make_object(name, geo, list(color), mat, coll)
        xs = [p[0] for p in geo.v]; ys = [p[1] for p in geo.v]; zs = [p[2] for p in geo.v]
        lo, hi = (min(xs), min(ys), min(zs)), (max(xs), max(ys), max(zs))
        pieces.append({
            "name": name, "color": list(color), "mat": mat, "transparency": tr, "tris": geo.tris(),
            "pos": [round((lo[j] + hi[j]) / 2, 4) for j in range(3)],
            "size": [round(hi[j] - lo[j], 4) for j in range(3)],
        })
    return {"id": wid, "kind": spec["kind"], "grip": spec["grip"], "muzzle": spec["muzzle"],
            "handle": spec["handle"], "pieces": pieces, "tris": sum(p["tris"] for p in pieces)}


def export_one(wid):
    coll = bpy.data.collections.get("W_" + wid)
    coll.hide_viewport = False  # hidden objects cannot be selected -> an empty GLB
    coll.hide_render = False
    bpy.ops.object.select_all(action='DESELECT')
    for o in coll.objects:
        o.hide_set(False)
        o.select_set(True)
    if not all(o.select_get() for o in coll.objects):
        raise RuntimeError("could not select every piece of " + wid)
    path = os.path.join(OUT, "SB_%s.glb" % wid)
    bpy.ops.export_scene.gltf(filepath=path, export_format='GLB', use_selection=True, export_yup=True,
                              export_apply=True, export_materials='EXPORT', export_normals=True,
                              export_texcoords=False, export_cameras=False, export_lights=False)
    return path


def build_all(ids=None, export=True):
    specs = json.load(open(SPECS))
    meta_path = os.path.join(ROOT, "meta.json")
    meta = json.load(open(meta_path)) if os.path.exists(meta_path) else {}
    for wid in (ids or sorted(specs.keys())):
        meta[wid] = build_one(wid, specs)
        if export:
            meta[wid]["glb"] = export_one(wid)
    json.dump(meta, open(meta_path, "w"), indent=1)
    return {k: meta[k]["tris"] for k in (ids or sorted(specs.keys()))}


# ------------------------------------------------------------------ rounded primitives for skin-kit parts

def build_primitives(export=True):
    coll = weapon_collection("Primitives")
    out = {}
    for name, bm in (("SB_RoundBlock", prim_block((1, 1, 1), 0.14, 3)),
                     ("SB_RoundWedge", prim_wedge((1, 1, 1), 0.10, 3))):
        a, b = bm_extract(bm)
        bm.free()
        g = Geo()
        g.add(a, b)
        make_object(name, g, [200, 200, 200], "SmoothPlastic", coll, sharp_angle=50)
        out[name] = g.tris()
    if export:
        coll.hide_viewport = False
        coll.hide_render = False
        bpy.ops.object.select_all(action='DESELECT')
        for o in coll.objects:
            o.hide_set(False)
            o.select_set(True)
        bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, "SB_Primitives.glb"), export_format='GLB',
                                  use_selection=True, export_yup=True, export_apply=True,
                                  export_materials='NONE', export_normals=True, export_texcoords=False)
    return out


# ------------------------------------------------------------------ skin kits as cast meshes (22.11.2026)
# WeaponSkinKits used to put 18-58 rounded blocks/wedges/balls over the smooth weapon. Each kit colour
# group is now fused into one surface the same way as the gun bodies (finer voxel, little smoothing, so
# spikes and crystal facets stay crisp): rings of bars become rings, wedge pairs become one spike, horn
# chains one horn, and overlapping glass no longer shows its inner faces.
# Input: kit_specs.json (game/tools/export_kits_json.luau). Output: kit_meta.json + glb/SB_Kits_<n>.glb.

KIT_SPECS = os.path.join(ROOT, "kit_specs.json")
KIT_TRIS = 4800
KIT_CAST = {"voxel": 0.018, "smooth_iter": 2, "smooth_fac": 0.5, "group_budget": 1100, "min_tris": 90,
            "density": 0.11, "fillet": 0.018}
KIT_MIN = 2.4 * KIT_CAST["voxel"]  # thinnest dimension the remesh keeps
KIT_PAD = 0.02                      # plates between this and KIT_MIN are thickened to KIT_MIN for the cast
KIT_BATCHES = [
    ["SeedPistol", "FartPistol", "BigBee", "SproutSMG", "PeaRifle"],
    ["ThornRifle", "PumpkinShotgun", "SharkGun", "CactusSniper"],
    ["SunflowerStaff", "FrostStaff", "StormStaff", "VineBow"],
    ["ThunderMallet", "ThistleMace", "RoseBlade", "Knife"],
]
RARITIES = ["Uncommon", "Rare", "Epic", "Legendary", "Mythic"]


def kit_geo_in(p):
    """near-sharp input geometry of one kit part for the cast, or None if it is too thin to cast"""
    s = list(p["size"])
    sh = p["shape"]
    if sh == "Cylinder":
        if min(s[1], s[2]) < KIT_PAD:
            return None
        d = max(min(s[1], s[2]), KIT_MIN)
        bm = prim_cyl(max(s[0], KIT_MIN), d, segs=32, bseg=1)
    elif sh == "Ball":
        if min(s) < KIT_PAD:
            return None
        bm = bmesh.new()
        bmesh.ops.create_uvsphere(bm, u_segments=24, v_segments=14, radius=max(min(s), KIT_MIN) / 2)
    else:
        if min(s) < KIT_PAD:
            return None
        s = [max(x, KIT_MIN) for x in s]
        bm = (prim_wedge if sh == "Wedge" else prim_block)(s, bev=0.0, seg=1)
    v, f = bm_extract(bm, part_matrix(p), p["pos"])
    bm.free()
    return v, f


def kit_groups(kit):
    groups, cast_in = {}, {}
    for p in kit["parts"]:
        k = gkey(p["color"], p.get("mat", "SmoothPlastic"), p.get("transparency", 0))
        groups.setdefault(k, Geo())
        g = kit_geo_in(p)
        if g:
            cast_in.setdefault(k, Geo()).add(*g)
        else:
            groups[k].add(*part_geo(p))
    # the whole kit stays within KIT_TRIS: the cast groups share it
    cfg = dict(KIT_CAST, group_budget=max(KIT_CAST["min_tris"], min(KIT_CAST["group_budget"], KIT_TRIS // max(1, len(cast_in)))))
    for k, cg in cast_in.items():
        vv, ff, nn, raw = cast_geo(cg, cfg=cfg)
        groups[k].add(vv, ff, nn)
    return {k: g for k, g in groups.items() if g.v}


def build_kit(key, kit):
    coll = weapon_collection("K_" + key)
    pieces = []
    order = sorted(kit_groups(kit).items(), key=lambda kv: -len(kv[1].v))
    for i, (k, geo) in enumerate(order):
        color, mat, tr = k
        name = "K_%s_%02d" % (key, i + 1)
        make_object(name, geo, list(color), mat, coll)
        xs = [p[0] for p in geo.v]; ys = [p[1] for p in geo.v]; zs = [p[2] for p in geo.v]
        lo, hi = (min(xs), min(ys), min(zs)), (max(xs), max(ys), max(zs))
        pieces.append({
            "name": name, "color": list(color), "mat": mat, "transparency": tr, "tris": geo.tris(),
            "pos": [round((lo[j] + hi[j]) / 2, 4) for j in range(3)],
            "size": [round(hi[j] - lo[j], 4) for j in range(3)],
        })
    return {"weapon": kit["weapon"], "rarity": kit["rarity"], "parts": len(kit["parts"]), "pieces": pieces,
            "tris": sum(p["tris"] for p in pieces)}


def export_kit_batch(n):
    bpy.ops.object.select_all(action='DESELECT')
    count = 0
    for wid in KIT_BATCHES[n]:
        for r in RARITIES:
            c = bpy.data.collections.get("W_K_%s_%s" % (wid, r))
            if not c:
                continue
            c.hide_viewport = False
            c.hide_render = False
            for o in c.objects:
                o.hide_set(False)
                o.select_set(True)
                count += 1
    path = os.path.join(OUT, "SB_Kits_%d.glb" % (n + 1))
    bpy.ops.export_scene.gltf(filepath=path, export_format='GLB', use_selection=True, export_yup=True,
                              export_apply=True, export_materials='EXPORT', export_normals=True,
                              export_texcoords=False, export_cameras=False, export_lights=False)
    return path, count


def build_kits(weapons=None, export=True):
    kits = json.load(open(KIT_SPECS, encoding="utf-8"))
    meta_path = os.path.join(ROOT, "kit_meta.json")
    meta = json.load(open(meta_path, encoding="utf-8")) if os.path.exists(meta_path) else {}
    for key in sorted(kits):
        if weapons and kits[key]["weapon"] not in weapons:
            continue
        if not kits[key]["parts"]:
            continue
        meta[key] = build_kit(key, kits[key])
    json.dump(meta, open(meta_path, "w", encoding="utf-8"), indent=1)
    out = {}
    if export:
        for n in range(len(KIT_BATCHES)):
            if not weapons or any(w in weapons for w in KIT_BATCHES[n]):
                out[n + 1] = export_kit_batch(n)
    return out

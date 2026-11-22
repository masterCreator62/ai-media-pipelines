# Sugar Bloom - hand-built Pea Rifle and Thorn Rifle (22.11.2026), exec'd by build_weapons.py.
# Hard-surface toy look like the Shark Gun hero: chamfered lofts with small support bevels and
# area-weighted normals (flat faces stay flat, edges read soft), real boolean cut-outs (ejection
# port, lightening slots, rail teeth, peep sight, muzzle ports), ribbed grip panels, a smooth wrist
# into the stock. Same colour+material groups as the old part lists, so Skins.recolor still works,
# and the same overall boxes, so skin kits (anchored on the old part list) keep their places.
# Roblox space: x right, y up, -z forward (muzzle), studs. Handle at the origin.
import bpy, bmesh, math
from mathutils import Matrix, Vector

V = Vector
WN = 62  # weighted-normal angle limit: chamfers and tubes smooth, 90-degree walls crisp


def hput(G, color, mat, vf, tr=0):
    verts, faces = vf
    k = gkey(color, mat, tr)
    g = G.get(k)
    if g is None:
        g = G[k] = Geo()
        g.wn = WN
    g.add(verts, faces)


# ------------------------------------------------------------------ profiles (x, y) CCW, support pairs at corners

def prof(hw, hh, ct=0.0, cb=0.0, r=0.018, cx=0.0, cy=0.0):
    c = []
    c += [(hw - cb, -hh), (hw, -hh + cb)] if cb > 0 else [(hw, -hh)]
    c += [(hw, hh - ct), (hw - ct, hh)] if ct > 0 else [(hw, hh)]
    c += [(-hw + ct, hh), (-hw, hh - ct)] if ct > 0 else [(-hw, hh)]
    c += [(-hw, -hh + cb), (-hw + cb, -hh)] if cb > 0 else [(-hw, -hh)]
    out, n = [], len(c)
    for i in range(n):
        P, A, B = V(c[i]), V(c[i - 1]), V(c[(i + 1) % n])
        ra, rb = min(r, (A - P).length * 0.3), min(r, (B - P).length * 0.3)
        a = P + (A - P).normalized() * ra
        b = P + (B - P).normalized() * rb
        out.append((a.x + cx, a.y + cy))
        out.append((b.x + cx, b.y + cy))
    return out


def prof_poly(pts, r=0.015):
    """arbitrary convex CCW polygon with support pairs at every corner"""
    out, n = [], len(pts)
    for i in range(n):
        P, A, B = V(pts[i]), V(pts[i - 1]), V(pts[(i + 1) % n])
        ra, rb = min(r, (A - P).length * 0.3), min(r, (B - P).length * 0.3)
        a = P + (A - P).normalized() * ra
        b = P + (B - P).normalized() * rb
        out += [(a.x, a.y), (b.x, b.y)]
    return out


def prof_circle(r, n=20, cx=0.0, cy=0.0):
    return [(cx + r * math.cos(2 * math.pi * k / n), cy + r * math.sin(2 * math.pi * k / n)) for k in range(n)]


def sgnpow(x, e):
    return math.copysign(abs(x) ** e, x)


# ------------------------------------------------------------------ lofts, tubes, booleans

def _ring(O, X, Y, pr):
    return [tuple(V(O) + V(X) * px + V(Y) * py) for (px, py) in pr]


def loft_frames(stations, caps=(True, True), soft=0.018):
    """stations: [(O, X, Y, profile)] all profiles with the same point count; caps get a soft 45-degree rim"""
    n = len(stations[0][3])
    verts, faces = [], []

    def add_ring(r):
        b = len(verts)
        verts.extend(r)
        return list(range(b, b + n))

    idx = [add_ring(_ring(*s)) for s in stations]
    for a, b in zip(idx, idx[1:]):
        for k in range(n):
            k2 = (k + 1) % n
            faces.append((a[k], a[k2], b[k2], b[k]))
    for end in (0, 1):
        if not caps[end]:
            continue
        s, s2 = (stations[0], stations[1]) if end == 0 else (stations[-1], stations[-2])
        O, X, Y, pr = s
        T = V(s[0]) - V(s2[0])
        T = T.normalized() if T.length > 1e-9 else V(X).cross(V(Y))
        cx = sum(p[0] for p in pr) / n
        cy = sum(p[1] for p in pr) / n
        size = min(max(p[0] for p in pr) - min(p[0] for p in pr), max(p[1] for p in pr) - min(p[1] for p in pr))
        sf = min(soft, 0.2 * size)
        sc = max(0.2, 1 - 2 * sf / size) if size > 1e-6 else 1
        inner = [(cx + (px - cx) * sc, cy + (py - cy) * sc) for px, py in pr]
        r_in = add_ring(_ring(V(O) + T * sf, X, Y, inner))
        r_out = idx[0] if end == 0 else idx[-1]
        for k in range(n):
            k2 = (k + 1) % n
            faces.append((r_out[k], r_out[k2], r_in[k2], r_in[k]))
        faces.append(tuple(r_in))
    return verts, fix_winding(verts, faces)


X0, Y0, Z0 = V((1, 0, 0)), V((0, 1, 0)), V((0, 0, 1))


def zloft(rows, caps=(True, True), soft=0.018):
    """straight loft along z: rows = [(z, profile)]"""
    return loft_frames([(V((0, 0, z)), X0, Y0, pr) for z, pr in rows], caps, soft)


def perp(T):
    a = X0 if abs(T.x) < 0.9 else Y0
    X = (a - T * a.dot(T)).normalized()
    return X, T.cross(X)


def cyl(p0, p1, r0, r1=None, n=20, soft=0.012, caps=(True, True), mids=()):
    """cylinder p0->p1; mids = [(t, r)] extra stations"""
    A, B = V(p0), V(p1)
    T = (B - A).normalized()
    X, Y = perp(T)
    r1 = r0 if r1 is None else r1
    st = [(0.0, r0)] + list(mids) + [(1.0, r1)]
    return loft_frames([(A + (B - A) * t, X, Y, prof_circle(r, n)) for t, r in st], caps, soft)


def path_frames(points, side=X0):
    """frames along a curve in a plane normal to `side`: X = side, Y = side x tangent"""
    out = []
    P = [V(p) for p in points]
    for i, p in enumerate(P):
        T = (P[min(i + 1, len(P) - 1)] - P[max(i - 1, 0)]).normalized()
        out.append((p, side, side.cross(T).normalized()))
    return out


def tube(points, r, nr=8, caps=True, closed=False, rfun=None):
    P = [V(p) for p in points]
    m = len(P)
    verts, faces = [], []
    N = None
    for i in range(m):
        if closed:
            T = (P[(i + 1) % m] - P[i - 1]).normalized()
        else:
            T = (P[min(i + 1, m - 1)] - P[max(i - 1, 0)]).normalized()
        if N is None:
            N, _ = perp(T)
        N = (N - T * N.dot(T)).normalized()
        Bv = T.cross(N)
        rr = rfun(i / (m - 1)) if rfun else r
        for k in range(nr):
            a = 2 * math.pi * k / nr
            verts.append(tuple(P[i] + (N * math.cos(a) + Bv * math.sin(a)) * rr))
    rings = m if closed else m - 1
    for i in range(rings):
        j = (i + 1) % m
        for k in range(nr):
            k2 = (k + 1) % nr
            faces.append((i * nr + k, i * nr + k2, j * nr + k2, j * nr + k))
    if caps and not closed:
        faces.append(tuple(range(nr)))
        faces.append(tuple((m - 1) * nr + k for k in range(nr)))
    return verts, fix_winding(verts, faces)


def ball(c, r, u=12, v=8, sx=1.0, sy=1.0, sz=1.0):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=u, v_segments=v, radius=r)
    for vt in bm.verts:
        vt.co = V((vt.co.x * sx, vt.co.y * sy, vt.co.z * sz))
    vv, ff = bm_extract(bm, None, c)
    bm.free()
    return vv, ff


def rbox(c, size, bev=0.02, seg=2, M=None):
    bm = prim_block(size, bev, seg)
    vv, ff = bm_extract(bm, M, c)
    bm.free()
    return vv, ff


def frame_m(X, Y, Z):
    return Matrix((tuple(X), tuple(Y), tuple(Z))).transposed()


def boolean(vf, cutters, op='DIFFERENCE'):
    verts, faces = vf
    if not cutters:
        return verts, faces
    sc = bpy.context.scene.collection
    me = bpy.data.meshes.new("_hb")
    me.from_pydata(verts, [], faces)
    me.update()
    ob = bpy.data.objects.new("_hb", me)
    sc.objects.link(ob)
    tmp = []
    for i, (cv, cf) in enumerate(cutters):
        m2 = bpy.data.meshes.new("_hc")
        m2.from_pydata(cv, [], cf)
        m2.update()
        o2 = bpy.data.objects.new("_hc", m2)
        sc.objects.link(o2)
        tmp.append((o2, m2))
        md = ob.modifiers.new("b%d" % i, 'BOOLEAN')
        md.operation = op
        md.solver = 'EXACT'
        md.object = o2
    dg = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(dg)
    m3 = ev.to_mesh()
    vv = [tuple(v.co) for v in m3.vertices]
    ff = [tuple(p.vertices) for p in m3.polygons]
    ev.to_mesh_clear()
    bpy.data.objects.remove(ob)
    bpy.data.meshes.remove(me)
    for o2, m2 in tmp:
        bpy.data.objects.remove(o2)
        bpy.data.meshes.remove(m2)
    return vv, ff


def slot_x(c, h, l, w=0.8, rr=None):
    """rounded slot cutter through x (height h along y, length l along z)"""
    rr = rr if rr is not None else 0.48 * min(h, l)
    return rbox(c, (w, h, l), rr, 2)


# ------------------------------------------------------------------ shared pieces

def grip(G, core_col, core_mat, panel_col, panel_mat, center, rake=14, t0=-0.44, t1=0.42, hw=0.15, hd=0.235, nst=12):
    """pistol grip: superellipse loft along the raked axis, finger grooves on the front, a flared butt,
    flat side panels with raised ribs"""
    R = rxm(math.radians(-rake))
    U, F = R @ Y0, R @ V((0, 0, -1))
    Cn = V(center)
    rows = []
    for i in range(nst):
        t = t0 + (t1 - t0) * i / (nst - 1)
        fl = max(0.0, (t0 + 0.1 - t) / 0.1)  # butt flare
        w, d = hw * (1 + 0.07 * fl), hd * (1 + 0.06 * fl)
        rip = 0.0
        if -0.33 <= t <= 0.21:
            win = math.sin(math.pi * (t + 0.33) / 0.54)
            rip = 0.022 * math.cos(2 * math.pi * (t - 0.12) / 0.18) * win
        pr = []
        n = 16
        for k in range(n):
            a = 2 * math.pi * k / n
            c, s = math.cos(a), math.sin(a)
            px = w * sgnpow(c, 2 / 3)
            pf = d * sgnpow(s, 2 / 3) + (rip * s * s if s > 0 else 0)
            pr.append((px, pf))
        rows.append((Cn + U * t, X0, F, pr))
    hput(G, core_col, core_mat, loft_frames(rows, soft=0.03))
    out = [(-0.17, -0.30), (0.10, -0.30), (0.14, -0.12), (0.13, 0.16), (0.09, 0.26), (-0.13, 0.26), (-0.185, 0.04)]
    for s in (1, -1):
        a, b = pillow(densify(out, 2), tuple(Cn + X0 * (s * (hw - 0.005))), tuple(F), tuple(U), tuple(X0), 0.05, 0.86)
        hput(G, panel_col, panel_mat, (a, fix_winding(a, b)))
        for v in (-0.20, -0.10, 0.0, 0.10):
            M = frame_m(X0, U, F)
            c = Cn + X0 * (s * (hw + 0.022)) + U * v + F * (-0.02 + 0.08 * (v + 0.2) * 0.25)
            hput(G, panel_col, panel_mat, rbox(tuple(c), (0.026, 0.026, 0.22), 0.0, 1, M))


def trigger_group(G, guard_col, dy):
    """rounded trigger guard loop and a curved brass trigger blade"""
    pts = [(0, 0.40 + dy, -0.68), (0, 0.30 + dy, -0.665), (0, 0.255 + dy, -0.585), (0, 0.245 + dy, -0.45),
           (0, 0.245 + dy, -0.33), (0, 0.262 + dy, -0.23), (0, 0.31 + dy, -0.15)]
    hput(G, guard_col, "Metal", tube(pts, 0.03, 6))
    tp = [(0, 0.405 + dy, -0.355), (0, 0.36 + dy, -0.37), (0, 0.315 + dy, -0.36), (0, 0.28 + dy, -0.335), (0, 0.262 + dy, -0.30)]
    hput(G, BRASS, "Metal", tube(tp, 0.026, 6, rfun=lambda t: 0.028 - 0.01 * t))


def leaf(G, col, mat, root, u, v, length=0.24, width=0.09, thick=0.03):
    o = [(0.0, 0.0), (0.25 * length, 0.5 * width), (0.6 * length, 0.55 * width), (length, 0.0),
         (0.6 * length, -0.45 * width), (0.25 * length, -0.4 * width)]
    U_, V_ = V(u).normalized(), V(v).normalized()
    W_ = U_.cross(V_).normalized()
    a, b = pillow(o, tuple(root), tuple(U_), tuple(V_), tuple(W_), thick, 0.55)
    hput(G, col, mat, (a, fix_winding(a, b)))


# ------------------------------------------------------------------ Pea Rifle

def pea_groups():
    WOOD, HWOOD = [140, 92, 52], [92, 58, 34]
    GM, DM, SIL = [52, 54, 60], [28, 28, 32], [160, 165, 176]
    GRN, PEA = [110, 200, 70], [150, 232, 92]
    G = {}

    # receiver: chamfered box, ejection port (right), long side flutes, rear taper into the stock
    # (g2_step lives in hero_guns2.py, exec'd after this file; resolved when build_one runs)
    rec = zloft([(0.40, g2_step(0.19, 0.17, 0.39, 0.70, 0.85, 0.07, 0.03)),
                 (0.30, g2_step(0.214, 0.19, 0.37, 0.70, 0.87, 0.075, 0.04)),
                 (-1.02, g2_step(0.214, 0.19, 0.37, 0.70, 0.87, 0.075, 0.04)),
                 (-1.16, g2_step(0.205, 0.18, 0.45, 0.70, 0.86, 0.07, 0.035)),
                 (-1.30, g2_step(0.19, 0.17, 0.54, 0.70, 0.83, 0.06, 0.03))])
    cuts = [rbox((0.215, 0.70, -0.38), (0.13, 0.15, 0.48), 0.035, 3)]
    for s in (1, -1):
        cuts.append(rbox((s * 0.215, 0.50, -0.50 if s > 0 else -0.45), (0.05, 0.055, 0.95 if s > 0 else 1.15), 0.024, 2))
    hput(G, GM, "Metal", boolean(rec, cuts))
    hput(G, GM, "Metal", zloft([(-0.70, prof(0.185, 0.02, 0.01, 0.01, cy=0.39)), (-0.80, prof(0.195, 0.06, 0.02, 0.03, cy=0.35)),
                                (-1.06, prof(0.195, 0.06, 0.02, 0.03, cy=0.35)), (-1.15, prof(0.185, 0.02, 0.01, 0.01, cy=0.39))], soft=0.01))
    # barrel (runs back through the forend slots), gas tube
    hput(G, GM, "Metal", cyl((0, 0.68, -1.25), (0, 0.68, -3.56), 0.09, n=16))
    hput(G, GM, "Metal", cyl((0, 0.92, -2.15), (0, 0.92, -3.26), 0.058, n=14))
    trigger_group(G, GM, 0.0)

    # dark metal: rail with cut teeth, peep sight, gas block, hooded front sight, ported muzzle brake
    rail = zloft([(0.30, prof(0.17, 0.075, 0.05, 0.012, cy=0.93)), (-1.20, prof(0.17, 0.075, 0.05, 0.012, cy=0.93))], soft=0.012)
    hput(G, DM, "Metal", boolean(rail, [rbox((0, 1.012, 0.15 - 0.2 * i), (0.5, 0.07, 0.075), 0.012, 1) for i in range(7)]))
    peep = zloft([(-1.17, prof(0.13, 0.09, 0.06, 0.012, cy=1.0)), (-1.33, prof(0.13, 0.09, 0.06, 0.012, cy=1.0))], soft=0.015)
    hput(G, DM, "Metal", boolean(peep, [cyl((0, 1.025, -1.10), (0, 1.025, -1.40), 0.042, n=14)]))
    hput(G, DM, "Metal", zloft([(-2.30, prof(0.14, 0.205, 0.06, 0.07, cy=0.785)), (-2.50, prof(0.14, 0.205, 0.06, 0.07, cy=0.785))], soft=0.015))
    hput(G, DM, "Metal", zloft([(-3.24, prof(0.07, 0.09, 0.03, 0.01, cy=0.86)), (-3.36, prof(0.07, 0.09, 0.03, 0.01, cy=0.86))], soft=0.012))
    hood = [(0.078 * math.cos(2 * math.pi * k / 16), 1.03 + 0.078 * math.sin(2 * math.pi * k / 16), -3.30) for k in range(16)]
    hput(G, DM, "Metal", tube(hood, 0.022, 6, closed=True))
    hput(G, DM, "Metal", rbox((0, 0.99, -3.30), (0.035, 0.13, 0.035), 0.012, 1))
    brake = cyl((0, 0.68, -3.52), (0, 0.68, -3.84), 0.135, n=16)
    hput(G, DM, "Metal", boolean(brake, [slot_x((0, 0.68, -3.625), 0.065, 0.075), slot_x((0, 0.68, -3.735), 0.065, 0.075),
                                         cyl((0, 0.68, -3.76), (0, 0.68, -3.95), 0.085, n=12)]))

    # wood: stock with a slim wrist and a pod-shaped lightening window, slotted forend
    stock = zloft([(0.30, prof(0.185, 0.235, 0.06, 0.03, cy=0.62)),
                   (0.48, prof(0.165, 0.20, 0.06, 0.03, cy=0.60)),
                   (0.66, prof(0.172, 0.235, 0.06, 0.03, cy=0.565)),
                   (0.90, prof(0.19, 0.30, 0.065, 0.03, cy=0.545)),
                   (1.12, prof(0.19, 0.34, 0.065, 0.03, cy=0.50)),
                   (1.32, prof(0.185, 0.355, 0.06, 0.03, cy=0.445)),
                   (1.50, prof(0.18, 0.365, 0.06, 0.03, cy=0.405))], soft=0.02)
    hput(G, WOOD, "Wood", boolean(stock, [slot_x((0, 0.40, 1.00), 0.15, 0.40)]))
    cheek = [(0.66, 0.62), (0.80, 0.585), (1.05, 0.585), (1.18, 0.64), (1.12, 0.755), (0.85, 0.775), (0.70, 0.72)]
    a_, b_ = pillow(densify(cheek, 2), (-0.188, 0, 0), (0, 0, 1), (0, 1, 0), (-1, 0, 0), 0.07, 0.6)
    hput(G, WOOD, "Wood", (a_, fix_winding(a_, b_)))
    fore = zloft([(-1.28, prof(0.19, 0.29, 0.08, 0.06, cy=0.73)),
                  (-1.40, prof(0.215, 0.32, 0.09, 0.07, cy=0.735)),
                  (-2.15, prof(0.215, 0.32, 0.09, 0.07, cy=0.735)),
                  (-2.30, prof(0.18, 0.26, 0.07, 0.05, cy=0.74))], soft=0.02)
    hput(G, WOOD, "Wood", boolean(fore, [slot_x((0, 0.655, -1.55 - 0.25 * i), 0.12, 0.18) for i in range(3)]
                                  ))

    # pistol grip (dark wood) with light-wood ribbed panels
    grip(G, HWOOD, "Wood", WOOD, "Wood", (0, -0.02, 0.02), nst=10)
    # rubber buttpad with grooves
    pad = zloft([(1.48, prof(0.19, 0.37, 0.065, 0.035, cy=0.405)), (1.585, prof(0.19, 0.37, 0.065, 0.035, cy=0.405))], soft=0.02)
    hput(G, DM, "SmoothPlastic", boolean(pad, [rbox((0, y, 1.59), (0.5, 0.032, 0.05), 0.012, 1) for y in (0.22, 0.405, 0.59)]))

    # bolt in the port + charging knob
    hput(G, SIL, "Metal", rbox((0.172, 0.70, -0.38), (0.05, 0.10, 0.40), 0.018, 2))
    hput(G, SIL, "Metal", cyl((0.17, 0.705, -0.22), (0.228, 0.705, -0.22), 0.022, n=10))
    hput(G, SIL, "Metal", ball((0.238, 0.705, -0.22), 0.032, 10, 7))

    # pea pod magazine: curved lens-section pod with a seam and a curled tip, peas bulging out
    path = [(0, 0.47, -0.93), (0, 0.32, -0.95), (0, 0.14, -0.99), (0, -0.05, -1.05), (0, -0.23, -1.11),
            (0, -0.39, -1.15), (0, -0.51, -1.14), (0, -0.59, -1.09), (0, -0.635, -1.03)]
    wid = [(0.150, 0.22), (0.152, 0.24), (0.156, 0.25), (0.152, 0.245), (0.144, 0.225), (0.126, 0.18), (0.095, 0.125),
           (0.06, 0.075), (0.025, 0.035)]
    fr = path_frames(path)
    rows, seam = [], []
    for (P, X, Y), (w, d) in zip(fr, wid):
        pr = []
        for k in range(14):
            a = 2 * math.pi * k / 14
            c, s = math.cos(a), math.sin(a)
            pr.append((w * sgnpow(c, 1.25), d * s))
        rows.append((P, X, Y, pr))
        seam.append(tuple(P + Y * (d * 0.985)))
    hput(G, GRN, "SmoothPlastic", loft_frames(rows, soft=0.02))
    hput(G, GRN, "SmoothPlastic", tube(seam[1:], 0.021, 6))
    # stem knob where the pod meets the receiver
    hput(G, GRN, "SmoothPlastic", ball((0, 0.40, -0.70), 0.06, 10, 7, 1.0, 1.0, 1.3))
    for s in (1, -1):
        for (y, z, r) in ((0.24, -0.965, 0.112), (-0.02, -1.035, 0.12), (-0.28, -1.12, 0.10)):
            hput(G, PEA, "SmoothPlastic", ball((s * 0.118, y, z), r, 8, 5))
    # the pea loaded in the muzzle and a vine curling round the barrel with two leaves
    hput(G, GRN, "SmoothPlastic", ball((0, 0.68, -3.86), 0.11, 14, 8))
    vine = []
    for i in range(22):
        t = i / 21
        a = math.radians(30) + t * 2 * math.pi * 1.6
        vine.append((0.125 * math.cos(a), 0.68 + 0.125 * math.sin(a), -2.58 - 0.6 * t))
    hput(G, GRN, "SmoothPlastic", tube(vine, 0.03, 5, rfun=lambda t: 0.032 - 0.012 * t))
    leaf(G, GRN, "SmoothPlastic", V((0.11, 0.74, -2.75)), (1, 0.6, 0.35), (0, 0.4, -1), 0.20, 0.085)
    leaf(G, GRN, "SmoothPlastic", V((-0.10, 0.62, -3.05)), (-1, -0.4, 0.3), (0, 0.5, -1), 0.17, 0.075)
    return G


# ------------------------------------------------------------------ Thorn Rifle

def thorn_groups():
    GM, DM, SIL = [84, 88, 98], [28, 28, 32], [160, 165, 176]  # GM lighter than the other rifles (22.11.2026), brightness < 0.5
    HAND, GRASS, THORN, NEON = [70, 112, 62], [104, 190, 74], [96, 70, 46], [210, 50, 60]
    G = {}

    # upper receiver with ejection port and forward assist, lower with magwell flare
    up = zloft([(0.32, g2_step(0.17, 0.15, 0.775, 0.93, 1.07, 0.06, 0.02)),
                (0.25, g2_step(0.19, 0.165, 0.745, 0.93, 1.095, 0.065, 0.02)),
                (-0.96, g2_step(0.19, 0.165, 0.745, 0.93, 1.095, 0.065, 0.02)),
                (-1.05, g2_step(0.185, 0.16, 0.76, 0.93, 1.08, 0.06, 0.02)),
                (-1.12, g2_step(0.17, 0.15, 0.79, 0.93, 1.06, 0.055, 0.02))])
    cuts = [rbox((0.195, 0.905, -0.36), (0.11, 0.13, 0.46), 0.03, 3)]
    hput(G, GM, "Metal", boolean(up, cuts))
    hput(G, GM, "Metal", cyl((0.17, 0.985, 0.06), (0.17, 0.985, 0.30), 0.048, n=12))
    hput(G, GM, "Metal", rbox((0.19, 0.985, -0.06), (0.06, 0.07, 0.12), 0.025, 1))  # brass deflector
    hput(G, SIL, "Metal", rbox((0.183, 0.905, -0.36), (0.02, 0.10, 0.40), 0.008, 1))  # dust cover in the port
    hput(G, GM, "Metal", rbox((-0.20, 0.64, -0.60), (0.03, 0.07, 0.12), 0.012, 1))  # bolt catch
    hput(G, GM, "Metal", cyl((0.19, 0.55, -0.56), (0.215, 0.55, -0.56), 0.03, n=10))  # mag release + fence
    for zf in (-0.495, -0.625):
        hput(G, GM, "Metal", rbox((0.20, 0.55, zf), (0.035, 0.10, 0.025), 0.008, 1))
    lo = zloft([(0.35, prof(0.17, 0.165, 0.02, 0.05, cy=0.61)),
                (0.26, prof(0.195, 0.205, 0.02, 0.06, cy=0.57)),
                (-0.55, prof(0.195, 0.225, 0.02, 0.07, cy=0.55)),
                (-0.92, prof(0.195, 0.19, 0.02, 0.06, cy=0.585)),
                (-1.03, prof(0.185, 0.14, 0.02, 0.05, cy=0.635))])
    hput(G, GM, "Metal", lo)
    hput(G, GM, "Metal", loft_frames([(V((0, y, -0.79)), X0, V((0, 0, 1)), prof(w, d, 0.04, 0.04)) for y, w, d in
                                      ((0.40, 0.165, 0.245), (0.335, 0.18, 0.262), (0.305, 0.172, 0.25))], soft=0.012))
    hput(G, GM, "Metal", cyl((0, 0.85, -1.05), (0, 0.85, -3.44), 0.08, n=14))
    trigger_group(G, GM, -0.07)

    # dark metal: picatinny rail (cut teeth), red-dot optic, A-frame front sight, birdcage, magazine, buffer tube
    hput(G, DM, "Metal", zloft([(0.30, prof(0.12, 0.04, 0.025, 0.015, cy=1.13)), (-2.30, prof(0.12, 0.04, 0.025, 0.015, cy=1.13))], soft=0.01))
    for i in range(11):
        hput(G, DM, "Metal", rbox((0, 1.185, 0.14 - 0.22 * i), (0.28, 0.04, 0.075), 0.0, 1))
    optic = cyl((0, 1.37, -0.36), (0, 1.37, -0.92), 0.13, 0.16, n=16, mids=[(0.1, 0.145), (0.84, 0.145)])
    hput(G, DM, "Metal", boolean(optic, [cyl((0, 1.37, -0.86), (0, 1.37, -0.98), 0.128, n=16)]))
    hput(G, DM, "Metal", zloft([(-0.46, prof(0.085, 0.07, 0.02, 0.01, cy=1.225)), (-0.76, prof(0.085, 0.07, 0.02, 0.01, cy=1.225))], soft=0.01))
    hput(G, DM, "Metal", cyl((0, 1.50, -0.62), (0, 1.545, -0.62), 0.045, n=12))
    hput(G, DM, "Metal", cyl((0.13, 1.37, -0.62), (0.19, 1.37, -0.62), 0.04, n=12))
    afr = loft_frames([(V((0, 0, -2.39)), X0, Y0, prof_poly([(0.075, 0.92), (0.035, 1.29), (-0.035, 1.29), (-0.075, 0.92)])),
                       (V((0, 0, -2.51)), X0, Y0, prof_poly([(0.075, 0.92), (0.035, 1.29), (-0.035, 1.29), (-0.075, 0.92)]))], soft=0.012)
    hput(G, DM, "Metal", boolean(afr, [cyl((0, 1.19, -2.30), (0, 1.19, -2.60), 0.026, n=12)]))
    hput(G, DM, "Metal", rbox((0, 1.19, -2.45), (0.018, 0.08, 0.018), 0.007, 1))
    hput(G, DM, "Metal", cyl((0, 0.85, -2.40), (0, 0.85, -2.50), 0.11, n=18))
    cage = cyl((0, 0.85, -3.42), (0, 0.85, -3.74), 0.12, n=12)
    ccut = [cyl((0, 0.85, -3.66), (0, 0.85, -3.85), 0.065, n=10)]
    for ang in (0, 90):
        M = rzm(math.radians(ang))
        ccut.append(rbox((0, 0.85, -3.60), (0.4, 0.045, 0.17), 0.021, 1, M))
    hput(G, DM, "Metal", boolean(cage, ccut))
    mpath = [(0, 0.52, -0.80), (0, 0.06, -0.785), (0, -0.40, -0.72)]
    mfr = path_frames(mpath)
    mrows = []
    for i, (P, X, Y) in enumerate(mfr):
        mrows.append((P, X, Y, prof(0.13, 0.20, 0.035, 0.035)))
    bot = mfr[-1]
    mrows.append((bot[0] + V((0, -0.01, 0.003)), bot[1], bot[2], prof(0.148, 0.222, 0.035, 0.035)))
    mrows.append((bot[0] + V((0, -0.055, 0.008)), bot[1], bot[2], prof(0.148, 0.222, 0.035, 0.035)))
    mag = loft_frames(mrows, soft=0.015)
    R6 = rxm(math.radians(-5))
    mcut = []
    for s in (1, -1):
        for dz in (0.0,):
            mcut.append(rbox((s * 0.135, 0.02, -0.77 + dz), (0.05, 0.62, 0.04), 0.018, 2, R6))
    hput(G, DM, "Metal", boolean(mag, mcut))
    hput(G, DM, "Metal", cyl((0, 0.85, 0.30), (0, 0.85, 1.25), 0.11, n=14))
    hput(G, DM, "Metal", cyl((0, 0.85, 0.33), (0, 0.85, 0.41), 0.135, n=14))

    # gray plastic: skeleton stock sliding on the tube, grip panels
    stock = zloft([(0.72, prof(0.14, 0.20, 0.07, 0.04, cy=0.77)),
                   (0.84, prof(0.16, 0.265, 0.075, 0.045, cy=0.705)),
                   (1.25, prof(0.165, 0.30, 0.075, 0.045, cy=0.68)),
                   (1.38, prof(0.165, 0.30, 0.075, 0.045, cy=0.68))], soft=0.02)
    hput(G, GM, "SmoothPlastic", boolean(stock, [slot_x((0, 0.555, 1.06), 0.14, 0.40), rbox((0, 0.985, 1.06), (0.08, 0.04, 0.42), 0.015, 2)]))
    grip(G, DM, "SmoothPlastic", GM, "SmoothPlastic", (0, -0.01, 0.02), t0=-0.37, hw=0.145, hd=0.225, nst=8)
    pad = zloft([(1.37, prof(0.175, 0.315, 0.065, 0.045, cy=0.68)), (1.475, prof(0.175, 0.315, 0.065, 0.045, cy=0.68))], soft=0.02)
    hput(G, DM, "SmoothPlastic", pad)

    # green handguard: octagon with lightening slots (barrel shows through)
    hg = zloft([(-1.10, prof(0.19, 0.19, 0.07, 0.07, cy=0.85)),
                (-1.19, prof(0.21, 0.21, 0.075, 0.075, cy=0.85)),
                (-2.41, prof(0.21, 0.21, 0.075, 0.075, cy=0.85)),
                (-2.50, prof(0.185, 0.185, 0.065, 0.065, cy=0.85))], soft=0.02)
    hcut = [slot_x((0, 0.85, -1.58 - 0.24 * i), 0.085, 0.14) for i in range(3)]
    hput(G, HAND, "SmoothPlastic", boolean(hg, hcut))

    # grass vine bands hugging the handguard, each with two leaves
    band_prof = prof(0.228, 0.228, 0.082, 0.082, r=0.03)
    for z in (-1.35, -2.25):
        pts = []
        for i, (x, y) in enumerate(band_prof):
            wob = 0.008 * math.sin(i * 1.7)
            pts.append((x, 0.85 + y, z + wob))
        hput(G, GRASS, "Grass", tube(pts, 0.04, 4, closed=True))
        leaf(G, GRASS, "Grass", V((0.20, 1.02, z)), (0.7, 0.55, 0.45), (0, 0.3, -1), 0.22, 0.085)
        leaf(G, GRASS, "Grass", V((-0.20, 0.69, z)), (-0.75, -0.35, 0.55), (0, 0.4, -1), 0.19, 0.075)

    # rose thorns: curved cones on the handguard flanks, hooked toward the muzzle
    for i, z in enumerate((-1.45, -1.57, -1.70, -1.82, -1.95, -2.07, -2.20, -2.32)):
        s = 1 if i % 2 == 0 else -1
        y = 0.965 if s > 0 else 0.735
        B = V((s * 0.17, y, z))
        D = V((s * 1.0, 0.32 * s, 0.15)).normalized()
        pts = [tuple(B + D * (0.272 * t) + V((0, 0.025 * s * t * t, -0.11 * t * t))) for t in (0.0, 0.3, 0.6, 1.0)]
        hput(G, THORN, "Wood", tube(pts, 0.05, 5, rfun=lambda t: 0.058 * (1 - t) ** 1.1 + 0.004))

    # red-dot lens, T charging handle
    hput(G, NEON, "Neon", cyl((0, 1.37, -0.85), (0, 1.37, -0.875), 0.126, n=16, soft=0.004))
    hput(G, SIL, "Metal", rbox((0, 1.0, 0.36), (0.40, 0.05, 0.075), 0.022, 1))
    hput(G, SIL, "Metal", rbox((0, 1.0, 0.31), (0.07, 0.04, 0.12), 0.015, 2))
    for s in (1, -1):
        hput(G, SIL, "Metal", rbox((s * 0.18, 1.0, 0.345), (0.05, 0.058, 0.09), 0.02, 1))
    return G


HEROES["PeaRifle"] = pea_groups
HEROES["ThornRifle"] = thorn_groups

# Sugar Bloom - hand-built Cactus Sniper, Fart Pistol, Pumpkin Shotgun, Big Bee (22.11.2026),
# exec'd by build_weapons.py after hero_rifles.py (uses its lofts, booleans, grip and trigger helpers).
# Same colour+material groups as the meta pieces of the cast models, same Handle / Muzzle / grip,
# overall boxes within 5 %, so skin kits (anchored on the old part lists) keep their places.
# Roblox space: x right, y up, -z forward (muzzle), studs. Handle at the origin.
import math
from mathutils import Vector

V = Vector


def g2_se(hw, hh, n=20, e=0.7, cx=0.0, cy=0.0):
    """superellipse profile (soft box)"""
    return [(cx + hw * sgnpow(math.cos(2 * math.pi * k / n), e), cy + hh * sgnpow(math.sin(2 * math.pi * k / n), e)) for k in range(n)]


def g2_lobe(R, lobes, depth, n, cx=0.0, cy=0.0, phase=0.0, p=1.4, sx=1.0, sy=1.0):
    """ribbed round profile: crests narrower than valleys (cactus stem, rubber bulb)"""
    out = []
    for k in range(n):
        a = 2 * math.pi * k / n
        f = ((1 + math.cos(lobes * (a - phase))) / 2) ** p
        r = R * (1 + depth * (2 * f - 1))
        out.append((cx + sx * r * math.cos(a), cy + sy * r * math.sin(a)))
    return out


def g2_step(hwl, hwh, yb, ys, yt, ct=0.06, cb=0.03, sh=0.03, r=0.015):
    """receiver section with a shoulder: wide lower body, narrower raised cover on top"""
    pts = [(hwl - cb, yb), (hwl, yb + cb), (hwl, ys), (hwh, ys + sh), (hwh, yt - ct), (hwh - ct, yt),
           (-(hwh - ct), yt), (-hwh, yt - ct), (-hwh, ys + sh), (-hwl, ys), (-hwl, yb + cb), (-(hwl - cb), yb)]
    return prof_poly(pts, r)


def g2_zrings(axis_y, rows, n=20, caps=(True, True), soft=0.012, ax=0.0):
    """round loft along z: rows = [(z, r)]"""
    return zloft([(z, prof_circle(r, n, ax, axis_y)) for z, r in rows], caps, soft)


def g2_cone(p0, p1, r0, r1=0.003, nr=3):
    return tube([p0, p1], r0, nr, rfun=lambda t: r0 + (r1 - r0) * t)


def g2_octa(c, r):
    c = V(c)
    vs = [c + V((r, 0, 0)), c + V((-r, 0, 0)), c + V((0, r, 0)), c + V((0, -r, 0)), c + V((0, 0, r)), c + V((0, 0, -r))]
    fs = [(0, 2, 4), (2, 1, 4), (1, 3, 4), (3, 0, 4), (2, 0, 5), (1, 2, 5), (3, 1, 5), (0, 3, 5)]
    return [tuple(v) for v in vs], fix_winding([tuple(v) for v in vs], fs)


def g2_hex(c, r, depth, axis=0):
    """hexagonal prism cutter along x (axis 0)"""
    pts = [(r * math.cos(math.pi / 3 * k), r * math.sin(math.pi / 3 * k)) for k in range(6)]
    x0, x1 = c[0] - depth / 2, c[0] + depth / 2
    vs = [(x0, c[1] + py, c[2] + pz) for pz, py in pts] + [(x1, c[1] + py, c[2] + pz) for pz, py in pts]
    fs = [tuple(range(6)), tuple(range(6, 12))] + [(k, (k + 1) % 6, 6 + (k + 1) % 6, 6 + k) for k in range(6)]
    return vs, fix_winding(vs, fs)


# ------------------------------------------------------------------ Cactus Sniper

def cactus_groups():
    GRN, DGRN, CRM = [72, 152, 82], [46, 112, 58], [246, 236, 200]
    DM, GM, SIL = [28, 28, 32], [52, 54, 60], [160, 165, 176]
    WOOD, HWOOD, PINK, YEL, LENS = [140, 92, 52], [92, 58, 34], [255, 120, 175], [255, 208, 48], [120, 210, 255]
    G = {}
    AY = 0.75  # barrel axis height

    # green receiver: shouldered section, sloped nose into the stem, ejection port, side flutes
    rec = zloft([(0.33, g2_step(0.165, 0.15, 0.48, 0.69, 0.84, 0.05, 0.03)),
                 (0.22, g2_step(0.20, 0.175, 0.43, 0.69, 0.875, 0.07, 0.035)),
                 (-0.84, g2_step(0.20, 0.175, 0.43, 0.69, 0.875, 0.07, 0.035)),
                 (-1.00, g2_step(0.19, 0.165, 0.51, 0.69, 0.86, 0.065, 0.035)),
                 (-1.14, g2_step(0.165, 0.15, 0.60, 0.69, 0.83, 0.055, 0.03))], soft=0.02)
    cuts = [rbox((0.205, 0.765, -0.06), (0.12, 0.13, 0.38), 0.035, 2), rbox((-0.205, 0.555, -0.42), (0.05, 0.05, 0.86), 0.022, 2)]
    hput(G, GRN, "SmoothPlastic", boolean(rec, cuts))

    # the stem: 8-ribbed cactus column with two pinched joints, dark-green joint collars
    joints = (-2.05, -3.15)

    def sc(z):
        s = 1.0 + 0.035 * math.sin(math.pi * min(1.0, max(0.0, (-1.06 - z) / 0.99))) ** 2 if z > -2.05 else 1.0 + 0.035 * math.sin(math.pi * min(1.0, max(0.0, (-2.05 - z) / 1.10))) ** 2
        for zj in joints:
            s -= 0.12 * math.exp(-((z - zj) / 0.075) ** 2)
        return s

    zs = [-1.06, -1.55]
    for zj in joints:
        zs += [zj + 0.11, zj, zj - 0.11]
    zs += [-2.60, -3.70, -4.18, -4.30]
    zs = sorted(set(round(z, 3) for z in zs), reverse=True)
    R = 0.152
    stem = zloft([(z, g2_lobe(R * sc(z) * (0.96 if z < -4.25 else 1.0), 8, 0.11, 24, 0, AY, math.pi / 8)) for z in zs], soft=0.02)
    hput(G, GRN, "SmoothPlastic", stem)
    for zj in joints:
        ring = [(x, y, zj) for x, y in g2_lobe(R * 1.005, 8, 0.11, 16, 0, AY, math.pi / 8)]
        hput(G, DGRN, "SmoothPlastic", tube(ring, 0.03, 4, closed=True))

    # areoles on the rib crests: a cream pad and three spines (main radial, two splayed)
    crests = [math.pi / 8 + k * math.pi / 4 for k in range(8)]
    row = 0
    z = -1.36
    while z > -4.12:
        near_joint = any(abs(z - zj) < 0.1 for zj in joints)
        if not near_joint:
            for k, a in enumerate(crests):
                if (k + row) % 2:
                    continue
                if z > -2.0 and math.sin(a) > 0.6:      # under the scope bell
                    continue
                if abs(z + 2.5) < 0.14 and math.sin(a) < -0.6:  # bipod clamp
                    continue
                Nr = V((math.cos(a), math.sin(a), 0))
                T = V((0, 0, -1))
                B = T.cross(Nr)
                P = V((0, AY, z)) + Nr * (R * sc(z) * 1.11)
                d = (Nr + T * 0.3).normalized()
                hput(G, CRM, "SmoothPlastic", g2_cone(tuple(P), tuple(P + d * 0.14), 0.017))
                for sb in (1, -1):
                    d2 = (Nr * 0.75 + B * (0.65 * sb) + T * 0.25).normalized()
                    hput(G, CRM, "SmoothPlastic", g2_cone(tuple(P), tuple(P + d2 * 0.085), 0.012))
        row += 1
        z -= 0.38

    # long spines exactly where skin kits rest (tips of the old part-list spines)
    for zt, tip in ((-2.27, (0.295, 0.842)), (-3.07, (-0.295, 0.842)), (-2.88, (0.0, 1.045))):
        a = math.atan2(tip[1] - AY, tip[0])
        k = min(range(8), key=lambda j: abs(math.atan2(math.sin(crests[j] - a), math.cos(crests[j] - a))))
        ca = crests[k]
        P0 = V((0, AY, zt)) + V((math.cos(ca), math.sin(ca), 0)) * (R * sc(zt) * 1.08)
        T1 = V((tip[0], tip[1], zt - 0.02))
        T1 = P0 + (T1 - P0) * 1.06
        hput(G, CRM, "SmoothPlastic", g2_cone(tuple(P0), tuple(T1), 0.02))

    # muzzle crown and the cactus flower: six petals round the bore, glowing centre
    hput(G, DM, "Metal", g2_zrings(AY, [(-4.24, 0.165), (-4.30, 0.185), (-4.50, 0.185), (-4.57, 0.165)], n=14))
    for k in range(5):
        a = math.pi / 2 + k * 2 * math.pi / 5
        u = V((math.cos(a), math.sin(a), -0.42)).normalized()
        v = V((-math.sin(a), math.cos(a), 0))
        w = u.cross(v)
        o = V((0.10 * math.cos(a), AY + 0.10 * math.sin(a), -4.575))
        pet = [(0, -0.035), (0.07, -0.07), (0.17, -0.072), (0.225, -0.03), (0.235, 0.0), (0.225, 0.03), (0.17, 0.072), (0.07, 0.07), (0, 0.035)]
        a_, b_ = pillow(pet, tuple(o), tuple(u), tuple(v), tuple(w), 0.045, 0.55)
        hput(G, PINK, "SmoothPlastic", (a_, fix_winding(a_, b_)))
    hput(G, YEL, "Neon", ball((0, AY, -4.62), 0.07, 10, 6))

    # magazine: raked box with grooves and a flared base plate
    mfr = path_frames([(0, 0.47, -0.50), (0, 0.27, -0.515), (0, 0.075, -0.535)])
    mrows = [(P, X, Y, prof(0.115, 0.215, 0.035, 0.035)) for P, X, Y in mfr]
    bot = mfr[-1]
    mrows.append((bot[0] + V((0, -0.008, 0.002)), bot[1], bot[2], prof(0.13, 0.235, 0.035, 0.035)))
    mrows.append((bot[0] + V((0, -0.05, 0.004)), bot[1], bot[2], prof(0.13, 0.235, 0.035, 0.035)))
    hput(G, DM, "Metal", loft_frames(mrows, soft=0.015))

    # scope: eyepiece bell, slim tube, objective bell with a recessed lens, rings on two clamp mounts
    SY = 1.26
    scope = g2_zrings(SY, [(0.47, 0.19), (0.40, 0.20), (0.20, 0.20), (0.11, 0.165), (-1.40, 0.165), (-1.56, 0.215), (-1.895, 0.22)], n=16)
    hput(G, DM, "Metal", boolean(scope, [cyl((0, SY, -1.86), (0, SY, -1.95), 0.185, n=16)]))
    hput(G, LENS, "Neon", cyl((0, SY, -1.855), (0, SY, -1.88), 0.186, n=16, soft=0.004))
    for zm in (-0.20, -1.20):
        hput(G, DM, "Metal", tube([(0.185 * math.cos(2 * math.pi * k / 12), SY + 0.185 * math.sin(2 * math.pi * k / 12), zm) for k in range(12)], 0.034, 4, closed=True))
        base = prof_poly([(0.10, 0.855), (0.075, 1.12), (-0.075, 1.12), (-0.10, 0.855)], 0.02)
        hput(G, DM, "Metal", zloft([(zm + 0.065, base), (zm - 0.065, base)], soft=0.012))
    # turrets
    hput(G, GM, "Metal", cyl((0, 1.40, -0.70), (0, 1.56, -0.70), 0.092, 0.075, n=12, mids=[(0.28, 0.092), (0.34, 0.078)]))
    hput(G, GM, "Metal", cyl((0.14, SY, -0.70), (0.32, SY, -0.70), 0.092, 0.075, n=12, mids=[(0.28, 0.092), (0.34, 0.078)]))

    # bipod: clamp under the stem, two-piece legs splayed out, rubber feet
    hput(G, DM, "Metal", rbox((0, 0.565, -2.5), (0.17, 0.10, 0.15), 0.035, 2))
    for s in (1, -1):
        hput(G, DM, "Metal", cyl((s * 0.06, 0.55, -2.5), (s * 0.17, 0.20, -2.5), 0.038, n=8))
        hput(G, DM, "Metal", cyl((s * 0.155, 0.25, -2.5), (s * 0.28, -0.09, -2.5), 0.027, n=8))
        hput(G, DM, "Metal", ball((s * 0.285, -0.11, -2.5), 0.045, 6, 4))

    # wood: sniper stock with a hooked toe and a lightening window; dark-wood cheek riser
    stock = zloft([(0.28, prof(0.17, 0.21, 0.06, 0.035, cy=0.64)),
                   (0.48, prof(0.15, 0.185, 0.055, 0.035, cy=0.605)),
                   (0.78, prof(0.16, 0.25, 0.06, 0.035, cy=0.53)),
                   (1.12, prof(0.175, 0.29, 0.06, 0.035, cy=0.49)),
                   (1.50, prof(0.18, 0.315, 0.06, 0.035, cy=0.475)),
                   (1.86, prof(0.18, 0.325, 0.06, 0.035, cy=0.475))], soft=0.02)
    hput(G, WOOD, "Wood", boolean(stock, [slot_x((0, 0.42, 1.05), 0.14, 0.42), slot_x((0, 0.13, 1.36), 0.16, 0.30)]))
    cheek = zloft([(0.64, prof(0.11, 0.05, 0.04, 0.02, cy=0.80)),
                   (0.72, prof(0.145, 0.085, 0.06, 0.02, cy=0.84)),
                   (1.28, prof(0.145, 0.085, 0.06, 0.02, cy=0.84)),
                   (1.36, prof(0.11, 0.05, 0.04, 0.02, cy=0.80))], soft=0.02)
    hput(G, HWOOD, "Wood", cheek)
    grip(G, HWOOD, "Wood", WOOD, "Wood", (0, -0.02, 0.02), t0=-0.37, nst=9)
    trigger_group(G, GM, 0.0)
    pad = zloft([(1.85, prof(0.185, 0.345, 0.065, 0.04, cy=0.458)), (1.95, prof(0.185, 0.345, 0.065, 0.04, cy=0.458))], soft=0.02)
    hput(G, DM, "SmoothPlastic", pad)

    # bolt: body in the port, bent handle, round knob
    hput(G, SIL, "Metal", rbox((0.17, 0.765, -0.06), (0.05, 0.10, 0.32), 0.018, 2))
    hput(G, SIL, "Metal", tube([(0.17, 0.79, 0.02), (0.27, 0.785, 0.035), (0.34, 0.75, 0.05)], 0.024, 6))
    hput(G, SIL, "Metal", ball((0.38, 0.735, 0.06), 0.075, 10, 7))
    return G


# ------------------------------------------------------------------ Fart Pistol

def fart_groups():
    BODY, DPUR, HPUR = [140, 92, 172], [110, 70, 140], [90, 56, 112]
    GLS, GM, DK = [170, 222, 90], [52, 54, 60], [28, 28, 32]
    PINK, PNK2, WHT, RED = [255, 120, 175], [220, 90, 140], [245, 245, 245], [210, 50, 60]
    G = {}
    AY = 0.65

    # body: a fat soft canister, tapering into the horn, side flutes
    body = zloft([(0.33, g2_se(0.20, 0.205, 24, 0.62, cy=AY)),
                  (0.26, g2_se(0.245, 0.255, 24, 0.62, cy=AY)),
                  (0.00, g2_se(0.26, 0.275, 24, 0.62, cy=AY)),
                  (-0.45, g2_se(0.255, 0.27, 24, 0.62, cy=AY)),
                  (-0.80, g2_se(0.25, 0.27, 24, 0.62, cy=AY)),
                  (-0.95, g2_se(0.235, 0.25, 24, 0.62, cy=AY)),
                  (-1.01, g2_se(0.20, 0.21, 24, 0.62, cy=AY))], soft=0.02)
    cuts = [rbox((s * 0.262, y, -0.56), (0.05, 0.034, 0.42), 0.016, 2) for s in (1, -1) for y in (0.50, 0.58)]
    hput(G, BODY, "SmoothPlastic", boolean(body, cuts))

    # top fin with three vent holes, running under the bubble collar
    fin = zloft([(0.02, prof(0.05, 0.05, 0.03, 0.01, cy=0.95)),
                 (-0.16, prof(0.058, 0.09, 0.035, 0.01, cy=0.99)),
                 (-0.70, prof(0.058, 0.115, 0.035, 0.01, cy=1.015)),
                 (-0.80, prof(0.05, 0.085, 0.03, 0.01, cy=0.985)),
                 (-0.85, prof(0.04, 0.05, 0.02, 0.01, cy=0.95))], soft=0.015)
    hput(G, DPUR, "SmoothPlastic", boolean(fin, [cyl((-0.2, 1.04, zz), (0.2, 1.04, zz), 0.03, n=10) for zz in (-0.32, -0.45, -0.58)]))

    # gas tank: collar with bolts, glass bubble in a three-strap cage, cloudy glowing gas inside
    BC = V((0, 1.36, 0.05))
    hput(G, GM, "Metal", cyl((0, 0.88, 0.05), (0, 1.07, 0.05), 0.25, 0.235, n=20, mids=[(0.5, 0.262)]))
    for k in range(6):
        a = 2 * math.pi * k / 6 + 0.3
        p0 = V((0.245 * math.cos(a), 0.975, 0.05 + 0.245 * math.sin(a)))
        hput(G, GM, "Metal", cyl(tuple(p0), tuple(p0 + V((math.cos(a), 0, math.sin(a))) * 0.035), 0.024, n=6))
    hput(G, GLS, "Glass", ball(tuple(BC), 0.41, 18, 11), 0.35)
    for k in range(3):
        a = 2 * math.pi * k / 3 + math.pi / 6
        pts = []
        for i in range(9):
            th = math.radians(140 - 140 * i / 8)
            rr = 0.428
            pts.append((rr * math.sin(th) * math.cos(a), BC.y + rr * math.cos(th), BC.z + rr * math.sin(th) * math.sin(a)))
        hput(G, GM, "Metal", tube(pts, 0.024, 6))
    hput(G, GM, "Metal", ball((0, BC.y + 0.425, BC.z), 0.042, 10, 6))
    for c, r in (((0, 1.34, 0.05), 0.19), ((0.08, 1.46, 0.0), 0.15), ((-0.07, 1.41, 0.13), 0.14), ((0.03, 1.27, -0.08), 0.13)):
        hput(G, GLS, "Neon", ball(c, r, 10, 7))

    # brass horn: root ring, slim throat, flared bell with a rolled lip, hollow inside
    hrow = [(-0.95, 0.135), (-1.16, 0.13), (-1.20, 0.165), (-1.27, 0.165), (-1.31, 0.13), (-1.50, 0.14), (-1.65, 0.17),
            (-1.78, 0.25), (-1.85, 0.31), (-1.90, 0.33), (-1.935, 0.342), (-1.952, 0.33), (-1.948, 0.305), (-1.936, 0.27), (-1.928, 0.25)]
    hput(G, [214, 170, 72], "Metal", zloft([(z, prof_circle(r, 20, 0, AY)) for z, r in hrow], soft=0.008))
    hput(G, DK, "SmoothPlastic", cyl((0, AY, -1.925), (0, AY, -1.94), 0.262, n=20, soft=0.004))
    trigger_group(G, GM, 0.0)

    # rubber squeeze bulb with ribs and a valve knob at the back
    brow = [(0.30, 0.17), (0.36, 0.205), (0.46, 0.225), (0.56, 0.218), (0.62, 0.20), (0.665, 0.15), (0.685, 0.09)]
    hput(G, PINK, "Fabric", zloft([(z, g2_lobe(r, 8, 0.06, 32, 0, AY, 0.0, 1.0)) for z, r in brow], soft=0.02))
    hput(G, PNK2, "Fabric", cyl((0, AY, 0.64), (0, AY, 0.71), 0.05, n=10))
    hput(G, PNK2, "Fabric", ball((0, AY, 0.72), 0.085, 10, 7))

    # pressure gauge on the right flank: white face, metal bezel, red needle, dark ticks
    GZ, GYc = -0.20, 0.68
    hput(G, WHT, "SmoothPlastic", cyl((0.245, GYc, GZ), (0.30, GYc, GZ), 0.165, n=20, soft=0.006))
    hput(G, GM, "Metal", tube([(0.30, GYc + 0.172 * math.sin(2 * math.pi * k / 20), GZ + 0.172 * math.cos(2 * math.pi * k / 20)) for k in range(20)], 0.022, 5, closed=True))
    na = math.radians(55)
    u = V((0, math.sin(na), -math.cos(na)))
    v = V((0, math.cos(na), math.sin(na)))
    a_, b_ = pillow([(-0.025, 0), (0, -0.014), (0.115, 0), (0, 0.014)], (0.305, GYc, GZ), tuple(u), tuple(v), (1, 0, 0), 0.012, 0.5)
    hput(G, RED, "SmoothPlastic", (a_, fix_winding(a_, b_)))
    hput(G, RED, "SmoothPlastic", cyl((0.30, GYc, GZ), (0.318, GYc, GZ), 0.022, n=8, soft=0.004))
    for k in range(5):
        a = math.radians(160 - 35 * k)
        hput(G, DK, "SmoothPlastic", rbox((0.303, GYc + 0.13 * math.sin(a), GZ - 0.13 * math.cos(a)), (0.012, 0.03, 0.012), 0.0, 1))

    grip(G, HPUR, "SmoothPlastic", DPUR, "SmoothPlastic", (0, -0.02, 0.02), t0=-0.37, hw=0.165, hd=0.235, nst=10)
    return G


# ------------------------------------------------------------------ Pumpkin Shotgun

def pumpkin_groups():
    PUMP, GM, HW, WOOD = [238, 132, 32], [52, 54, 60], [92, 58, 34], [140, 92, 52]
    RED, DKP, DKM = [210, 50, 60], [28, 28, 32], [28, 28, 32]
    GLOW, STEM, LEAF = [255, 220, 90], [58, 124, 50], [104, 190, 74]
    G = {}

    # receiver: shouldered, sloped front, ejection port, loading port, side flute
    rec = zloft([(0.32, g2_step(0.20, 0.18, 0.42, 0.70, 0.86, 0.06, 0.035)),
                 (0.24, g2_step(0.225, 0.20, 0.345, 0.70, 0.895, 0.075, 0.04)),
                 (-0.72, g2_step(0.225, 0.20, 0.345, 0.70, 0.895, 0.075, 0.04)),
                 (-0.84, g2_step(0.215, 0.19, 0.40, 0.70, 0.885, 0.07, 0.04)),
                 (-0.93, g2_step(0.18, 0.165, 0.48, 0.70, 0.86, 0.06, 0.035))], soft=0.02)
    cuts = [rbox((0.225, 0.735, -0.28), (0.12, 0.15, 0.42), 0.035, 2),
            rbox((0, 0.345, -0.47), (0.25, 0.09, 0.50), 0.035, 2),
            rbox((-0.225, 0.56, -0.32), (0.05, 0.05, 0.84), 0.022, 2)]
    hput(G, GM, "Metal", boolean(rec, cuts))
    hput(G, GM, "Metal", cyl((0, 0.85, -0.25), (0, 0.93, -0.25), 0.33, 0.31, n=24))  # pumpkin cup
    # barrel with a ventilated rib, choke ring, bead, barrel band to the magazine tube
    hput(G, GM, "Metal", cyl((0, 0.80, -0.85), (0, 0.80, -3.24), 0.12, n=16))
    choke = g2_zrings(0.80, [(-3.20, 0.13), (-3.24, 0.138), (-3.33, 0.138), (-3.35, 0.128)], n=16)
    hput(G, GM, "Metal", boolean(choke, [cyl((0, 0.80, -3.27), (0, 0.80, -3.45), 0.085, n=12)]))
    hput(G, GM, "Metal", zloft([(-0.95, prof(0.042, 0.014, 0.008, 0.004, cy=0.958)), (-3.18, prof(0.042, 0.014, 0.008, 0.004, cy=0.958))], soft=0.006))
    for i in range(12):
        hput(G, GM, "Metal", rbox((0, 0.935, -1.0 - 0.2 * i), (0.05, 0.04, 0.05), 0.0, 1))
    band = prof_poly([(0.13, 0.48), (0.13, 0.86), (-0.13, 0.86), (-0.13, 0.48)], 0.05)
    hput(G, GM, "Metal", zloft([(-2.95, band), (-3.05, band)], soft=0.02))
    hput(G, [214, 170, 72], "Metal", ball((0, 0.985, -3.17), 0.036, 8, 6))
    trigger_group(G, GM, 0.0)
    # magazine tube with an end cap
    hput(G, DKM, "Metal", cyl((0, 0.52, -0.88), (0, 0.52, -2.92), 0.10, n=14))
    hput(G, DKM, "Metal", cyl((0, 0.52, -2.92), (0, 0.52, -2.99), 0.112, 0.09, n=14))

    # pump: ridged wooden forend between dark-wood end bands and a middle band
    frow = []
    N = 19
    for i in range(N):
        t = i / (N - 1)
        r = 0.152 + 0.022 * math.sin(math.pi * t) - 0.012 * (0.5 + 0.5 * math.cos(2 * math.pi * 6 * t))
        frow.append((-1.42 - 0.76 * t, g2_se(r * 1.06, r, 14, 0.85, cy=0.52)))
    hput(G, WOOD, "Wood", zloft(frow, soft=0.012))
    for z in (-1.43, -1.80, -2.17):
        hput(G, HW, "Wood", g2_zrings(0.52, [(z + 0.03, 0.172), (z - 0.03, 0.172)], n=14, soft=0.012))

    # stock: drooping, slim wrist, buttpad with grooves; shell sleeve on the right flank
    def frames(path):
        P = [V(p) for p in path]
        out = []
        for i, p in enumerate(P):
            T = (P[min(i + 1, len(P) - 1)] - P[max(i - 1, 0)]).normalized()
            out.append((p, X0, T.cross(X0).normalized()))
        return out

    spath = [(0, 0.585, 0.26), (0, 0.555, 0.46), (0, 0.50, 0.80), (0, 0.44, 1.15), (0, 0.38, 1.46), (0, 0.345, 1.60)]
    sprof = [(0.185, 0.25), (0.162, 0.21), (0.178, 0.255), (0.19, 0.28), (0.19, 0.295), (0.19, 0.295)]
    srows = [(P, X, Y, prof(w, h, 0.06, 0.04)) for (P, X, Y), (w, h) in zip(frames(spath), sprof)]
    hput(G, WOOD, "Wood", loft_frames(srows, soft=0.02))
    pf = frames([(0, 0.38, 1.46), (0, 0.345, 1.60), (0, 0.325, 1.70)])
    prow = [(pf[1][0], pf[1][1], pf[1][2], prof(0.198, 0.31, 0.065, 0.045)), (pf[2][0], pf[2][1], pf[2][2], prof(0.198, 0.31, 0.065, 0.045))]
    hput(G, DKP, "SmoothPlastic", boolean(loft_frames(prow, soft=0.02),
                                          [rbox((0, 0.335 + dy, 1.705), (0.5, 0.03, 0.05), 0.012, 1, rxm(math.radians(10))) for dy in (-0.16, 0.0, 0.16)]))
    grip(G, HW, "Wood", WOOD, "Wood", (0, -0.02, 0.02), t0=-0.37, nst=10)
    for z in (0.45, 0.62, 0.79, 0.96):
        hput(G, RED, "SmoothPlastic", cyl((0.25, 0.36, z), (0.25, 0.69, z), 0.062, 0.038, n=8, mids=[(0.9, 0.058)]))
        hput(G, [214, 170, 72], "Metal", cyl((0.25, 0.29, z), (0.25, 0.37, z), 0.07, 0.064, n=8))
    hput(G, DKP, "SmoothPlastic", rbox((0.235, 0.50, 0.705), (0.16, 0.075, 0.72), 0.03, 2))

    # pumpkin: ribbed, dimpled, with a curved stem, a curly tendril and a leaf; glowing face
    v, f = lobed_ball((0, 1.08, -0.25), 0.49, 0.88, 8, 0.13, u=32, v=12)
    hput(G, PUMP, "SmoothPlastic", (v, fix_winding(v, f)))
    hput(G, STEM, "SmoothPlastic", tube([(0, 1.40, -0.25), (0, 1.53, -0.25), (0.025, 1.63, -0.225), (0.07, 1.71, -0.17)], 0.06, 7,
                                         rfun=lambda t: 0.062 - 0.026 * t))
    tend = []
    for i in range(14):
        t = i / 13
        a = t * 2 * math.pi * 1.4
        tend.append((-0.05 - 0.06 * t - 0.05 * math.cos(a) * t, 1.47 + 0.10 * t + 0.04 * math.sin(a), -0.25 + 0.05 * math.sin(a) * (0.4 + t)))
    hput(G, STEM, "SmoothPlastic", tube(tend, 0.016, 5, rfun=lambda t: 0.018 - 0.01 * t))
    lu = V((1, 0.15, 0.55)).normalized()
    lv = V((-0.5, 0.25, 0.85)).normalized()
    lv = (lv - lu * lv.dot(lu)).normalized()
    lo = [(0.0, 0.0), (0.06, 0.07), (0.13, 0.10), (0.19, 0.075), (0.25, 0.06), (0.33, 0.0), (0.25, -0.06), (0.19, -0.075), (0.13, -0.10), (0.06, -0.07)]
    a_, b_ = pillow(lo, (0.035, 1.56, -0.22), tuple(lu), tuple(lv), tuple(lu.cross(lv)), 0.03, 0.55)
    hput(G, LEAF, "SmoothPlastic", (a_, fix_winding(a_, b_)))
    for sx in (1, -1):
        a_, b_ = pillow([(-0.08, -0.05), (0.08, -0.05), (0.0, 0.08)], (sx * 0.15, 1.15, -0.715), (1, 0, 0), (0, 1, 0), (0, 0, 1), 0.05, 0.5)
        hput(G, GLOW, "Neon", (a_, fix_winding(a_, b_)))
    mouth = [(-0.20, 0.02), (-0.12, -0.04), (-0.06, 0.01), (0.0, -0.05), (0.06, 0.01), (0.12, -0.04), (0.20, 0.02),
             (0.14, -0.08), (0.0, -0.11), (-0.14, -0.08)]
    a_, b_ = pillow(mouth, (0, 0.97, -0.725), (1, 0, 0), (0, 1, 0), (0, 0, 1), 0.05, 0.4)
    hput(G, GLOW, "Neon", (a_, fix_winding(a_, b_)))
    return G


# ------------------------------------------------------------------ Big Bee

def bee_groups():
    GLS, DKM, YM, GM = [220, 240, 255], [28, 28, 32], [255, 208, 48], [52, 54, 60]
    DKP, HW, YP, SIL = [28, 28, 32], [92, 58, 34], [255, 208, 48], [160, 165, 176]
    G = {}
    AY, BY = 0.68, 0.78

    # receiver: shouldered, honeycomb cells pressed into the rear flanks
    rec = zloft([(0.22, g2_step(0.15, 0.13, 0.45, 0.66, 0.83, 0.05, 0.03)),
                 (0.14, g2_step(0.17, 0.15, 0.37, 0.66, 0.87, 0.06, 0.035)),
                 (-0.70, g2_step(0.17, 0.15, 0.37, 0.66, 0.87, 0.06, 0.035)),
                 (-0.80, g2_step(0.16, 0.14, 0.45, 0.66, 0.86, 0.055, 0.03)),
                 (-0.86, g2_step(0.14, 0.12, 0.55, 0.66, 0.84, 0.05, 0.03))], soft=0.02)
    cuts = []
    for s in (1, -1):
        for (zz, yy) in ((0.075, 0.49), (0.075, 0.605), (-0.01, 0.548)):
            cuts.append(g2_hex((s * 0.17, yy, zz), 0.048, 0.05))
    hput(G, GM, "Metal", boolean(rec, cuts))

    # abdomen: egg-shaped, rounded tail at the back, three black stripes proud of the surface
    arow = [(-0.10, 0.20), (-0.14, 0.29), (-0.20, 0.325), (-0.42, 0.338), (-0.60, 0.33), (-0.70, 0.32), (-0.77, 0.29), (-0.82, 0.20)]

    def ar(z):
        for (z0, r0), (z1, r1) in zip(arow, arow[1:]):
            if z1 <= z <= z0:
                return r0 + (r1 - r0) * (z - z0) / (z1 - z0)
        return 0.17

    hput(G, YM, "Metal", g2_zrings(AY, arow, n=24, soft=0.02))
    for z0 in (-0.24, -0.43, -0.62):
        rows = [(z0 + 0.05, ar(z0 + 0.05) + 0.006), (z0 + 0.035, ar(z0 + 0.035) + 0.014), (z0 - 0.035, ar(z0 - 0.035) + 0.014), (z0 - 0.05, ar(z0 - 0.05) + 0.006)]
        hput(G, DKM, "Metal", g2_zrings(AY, rows, n=24, caps=(False, False)))

    # thorax barrel with bulging yellow segment rings, toothed top rail, stinger muzzle
    hput(G, GM, "Metal", cyl((0, BY, -0.70), (0, BY, -2.46), 0.14, n=16))
    for z in (-1.0, -1.5, -2.0):
        hput(G, YM, "Metal", g2_zrings(BY, [(z + 0.07, 0.15), (z + 0.03, 0.168), (z - 0.03, 0.168), (z - 0.07, 0.15)], n=18, soft=0.01))
    rail = zloft([(-0.66, prof(0.06, 0.05, 0.02, 0.01, cy=0.94)), (-2.42, prof(0.06, 0.05, 0.02, 0.01, cy=0.94))], soft=0.01)
    hput(G, DKM, "Metal", boolean(rail, [rbox((0, 0.99, -0.78 - 0.2 * i), (0.2, 0.04, 0.075), 0.0, 1) for i in range(9)]))
    sting = g2_zrings(BY, [(-2.43, 0.12), (-2.47, 0.125), (-2.53, 0.118), (-2.60, 0.098), (-2.72, 0.072), (-2.84, 0.048), (-2.90, 0.036)], n=16, soft=0.006)
    hput(G, DKM, "Metal", sting)
    hput(G, DKM, "Metal", rbox((0, 0.95, 0.20), (0.10, 0.25, 0.15), 0.03, 2, rxm(math.radians(-25))))
    # silver gas rod with a guide collar
    hput(G, SIL, "Metal", cyl((0, 0.58, -0.70), (0, 0.58, -1.70), 0.05, n=10))
    hput(G, GM, "Metal", cyl((0, 0.58, -1.58), (0, 0.58, -1.64), 0.068, n=10))

    # antennae: elbowed feelers with round tips
    for s in (1, -1):
        hput(G, DKP, "SmoothPlastic", tube([(s * 0.03, 0.90, -2.20), (s * 0.055, 1.05, -2.26), (s * 0.085, 1.15, -2.30), (s * 0.13, 1.23, -2.40)], 0.022, 5))
        hput(G, DKP, "SmoothPlastic", ball((s * 0.135, 1.24, -2.415), 0.038, 8, 6))

    # wings: fore and hind on each side, with three veins each
    for sx in (1, -1):
        root = V((sx * 0.14, 1.0, -0.45))
        for (length, width, sweep, tilt) in ((0.90, 0.38, 18, 32), (0.64, 0.28, 50, 22)):
            out = V((sx * math.cos(math.radians(tilt)), math.sin(math.radians(tilt)), 0))
            back = V((0, 0, 1))
            u = (out * math.cos(math.radians(sweep)) + back * math.sin(math.radians(sweep))).normalized()
            v = (back - u * back.dot(u)).normalized()
            w = u.cross(v)
            outline = [(0.0, -0.06), (0.25 * length, -width * 0.42), (0.7 * length, -width * 0.5), (length, -width * 0.15),
                       (0.92 * length, width * 0.2), (0.55 * length, width * 0.32), (0.15 * length, width * 0.14)]
            a_, b_ = pillow(densify(outline, 3), tuple(root), tuple(u), tuple(v), tuple(w), 0.03, 0.72)
            hput(G, GLS, "Glass", (a_, fix_winding(a_, b_)), 0.45)
            for (e1, e2) in (((0.04, -0.02), (0.92, -0.10)), ((0.04, 0.0), (0.62, 0.22)), ((0.30, -0.06), (0.62, -0.38))):
                p0 = root + u * (e1[0] * length) + v * (e1[1] * width)
                p1 = root + u * (e2[0] * length) + v * (e2[1] * width)
                mid = (p0 + p1) / 2 + w * 0.004
                hput(G, GLS, "Glass", tube([tuple(p0), tuple(mid), tuple(p1)], 0.008, 4), 0.45)

    # grip: wood core, yellow ribbed panels, two black bands round it
    grip(G, HW, "Wood", YP, "SmoothPlastic", (0, -0.02, 0.02), t0=-0.37, hw=0.155, hd=0.235, nst=10)
    Rg = rxm(math.radians(-14))
    U, F = Rg @ Y0, Rg @ V((0, 0, -1))
    Cn = V((0, -0.02, 0.02))
    for t in (0.14, -0.16):
        pts = []
        for k in range(16):
            a = 2 * math.pi * k / 16
            px = 0.155 * 1.1 * sgnpow(math.cos(a), 2 / 3)
            pz = 0.235 * 1.05 * sgnpow(math.sin(a), 2 / 3)
            pts.append(tuple(Cn + U * t + X0 * px + F * pz))
        hput(G, DKP, "SmoothPlastic", tube(pts, 0.026, 5, closed=True))
    trigger_group(G, GM, 0.0)
    return G


HEROES["CactusSniper"] = cactus_groups
HEROES["FartPistol"] = fart_groups
HEROES["PumpkinShotgun"] = pumpkin_groups
HEROES["BigBee"] = bee_groups

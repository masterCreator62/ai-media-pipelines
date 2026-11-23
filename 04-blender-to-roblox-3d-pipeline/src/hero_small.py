# Sugar Bloom - hand-built Sprout SMG and Seed Pistol (22.11.2026), exec'd by build_weapons.py after hero_rifles.py.
# Same toy hard-surface recipe as hero_rifles.py: chamfered lofts with support bevels, area-weighted normals,
# boolean cut-outs (ejection ports, vents, serrations, grooves), ribbed grips. Same colour+material groups as
# the old part lists (Skins.recolor keeps working) and the same overall boxes, Handle at the origin,
# grip and muzzle unchanged, so skin kits anchored on the old part list keep their places.
# Motifs: Sprout SMG - a sprouting seedling on top, leaf-vein neon inlays, leaf vents in the top cover;
# Seed Pistol - a sunflower-seed slide (striped flanks, tapered nose, glowing seed inlay), sunflower medallions
# on the grip, a seed loaded in the muzzle.
# Roblox space: x right, y up, -z forward (muzzle), studs. Uses helpers from hero_rifles.py / build_weapons.py.
import math
from mathutils import Vector


def sm_torus_z(z, y, r, tr, n=18, nr=6):
    """ring around the z axis (barrel band)"""
    pts = [(r * math.cos(2 * math.pi * k / n), y + r * math.sin(2 * math.pi * k / n), z) for k in range(n)]
    return tube(pts, tr, nr, closed=True)


def sm_vert_grip(G, col, mat, x, z, y0, y1, hw, hd, ribs=3, nst=11):
    """vertical foregrip: superellipse loft, finger ribs on the front, flared foot"""
    rows = []
    for i in range(nst):
        t = i / (nst - 1)
        y = y0 + (y1 - y0) * t
        fl = max(0.0, (0.12 - t) / 0.12)
        w, d = hw * (1 + 0.12 * fl), hd * (1 + 0.10 * fl)
        rip = 0.0
        if 0.18 <= t <= 0.82:
            rip = 0.018 * math.cos(2 * math.pi * ribs * (t - 0.18) / 0.64) * math.sin(math.pi * (t - 0.18) / 0.64)
        pr = []
        for k in range(16):
            a = 2 * math.pi * k / 16
            c, s = math.cos(a), math.sin(a)
            pr.append((w * sgnpow(c, 2 / 3), d * sgnpow(s, 2 / 3) + (rip * s * s if s > 0 else 0)))
        rows.append((V((x, y, z)), X0, V((0, 0, -1)), pr))
    hput(G, col, mat, loft_frames(rows, soft=0.025))


# ------------------------------------------------------------------ Sprout SMG

def sprout_groups():
    GRN, DGRN, LEAF = [82, 150, 72], [58, 124, 50], [104, 190, 74]
    SIL = [160, 165, 176]
    G = {}

    # receiver (green): chamfered body, front taper; neon midrib grooves both sides, ejection port with the bolt,
    # charging slot (right), two lightening flutes (left)
    rec = zloft([(0.40, prof(0.185, 0.19, 0.07, 0.05, cy=0.68)),
                 (0.33, prof(0.215, 0.245, 0.08, 0.06, cy=0.645)),
                 (0.20, prof(0.222, 0.272, 0.08, 0.03, cy=0.62)),
                 (-1.12, prof(0.222, 0.272, 0.08, 0.03, cy=0.62)),
                 (-1.32, prof(0.212, 0.222, 0.08, 0.05, cy=0.67)),
                 (-1.50, prof(0.19, 0.195, 0.07, 0.04, cy=0.69))])
    cuts = [rbox((0.222, 0.70, -0.86), (0.12, 0.15, 0.40), 0.035, 3),
            rbox((0.222, 0.82, -0.40), (0.06, 0.05, 0.46), 0.022, 2),
            rbox((-0.222, 0.72, -0.40), (0.05, 0.05, 0.46), 0.022, 2),
            rbox((-0.222, 0.72, -0.98), (0.05, 0.05, 0.46), 0.022, 2)]
    for s in (1, -1):
        cuts.append(rbox((s * 0.222, 0.48, -0.58), (0.05, 0.075, 1.16), 0.03, 2))
    hput(G, GRN, "SmoothPlastic", boolean(rec, cuts))

    # neon leaf veins: midrib strip in the groove + three veins sweeping up toward the muzzle on each side
    for s in (1, -1):
        hput(G, LEAF, "Neon", rbox((s * 0.214, 0.48, -0.58), (0.03, 0.048, 1.12), 0.012, 1))
        for z in (-0.10, -0.45, -0.80):
            L = 0.22
            c = (s * 0.222, 0.48 + 0.5 * L * math.sin(math.radians(35)), z - 0.5 * L * math.cos(math.radians(35)))
            hput(G, LEAF, "Neon", rbox(c, (0.016, 0.026, L), 0.0, 1, rxm(math.radians(35))))

    # top cover (dark green) with herringbone leaf vents ahead of the sprout
    def arch(k, kh, cy):
        pts = [(0.20, -0.065), (0.20, 0.0), (0.145, 0.048), (0.05, 0.068), (-0.05, 0.068), (-0.145, 0.048), (-0.20, 0.0), (-0.20, -0.065)]
        return [(x, y + cy) for x, y in prof_poly([(x * k, -0.065 + (y + 0.065) * kh) for x, y in pts], 0.015)]
    top = zloft([(0.25, arch(0.84, 0.70, 0.955)), (0.17, arch(1.0, 1.0, 0.955)),
                 (-1.20, arch(1.0, 1.0, 0.955)), (-1.35, arch(0.80, 0.72, 0.955))], soft=0.015)
    vents = []
    for z in (-0.66, -0.86, -1.06):
        for s in (1, -1):
            vents.append(rbox((s * 0.085, 1.02, z), (0.05, 0.06, 0.17), 0.022, 2, rym(math.radians(s * 32))))
    hput(G, DGRN, "SmoothPlastic", boolean(top, vents))
    # the sprout: curved tapering stem with a bud
    stem = [(0, 0.98, -0.30), (0, 1.10, -0.305), (0, 1.21, -0.295), (0, 1.29, -0.275), (0, 1.33, -0.25)]
    hput(G, DGRN, "SmoothPlastic", tube(stem, 0.045, 8, rfun=lambda t: 0.048 - 0.016 * t))
    hput(G, DGRN, "SmoothPlastic", ball((0, 1.335, -0.245), 0.04, 10, 7, 1.0, 1.25, 1.0))
    # two seedling leaves
    for s in (1, -1):
        leaf(G, LEAF, "SmoothPlastic", V((s * 0.02, 1.25, -0.29)), (s * 1.0, 0.47, 0.0), (0, 0, -1), 0.31, 0.17, 0.035)

    # barrel shroud (gun metal) with side vents between dark bands, ported compensator
    shroud = cyl((0, 0.68, -1.42), (0, 0.68, -2.36), 0.18, n=20)
    hput(G, GUN, "Metal", boolean(shroud, [slot_x((0, 0.68, z), 0.09, 0.13) for z in (-1.775, -2.025)]))
    for z in (-1.65, -1.90, -2.15):
        hput(G, DARK, "Metal", sm_torus_z(z, 0.68, 0.178, 0.028, n=14))
    comp = cyl((0, 0.68, -2.33), (0, 0.68, -2.68), 0.11, n=16, mids=[(0.2, 0.118), (0.8, 0.118)])
    hput(G, DARK, "Metal", boolean(comp, [cyl((0, 0.68, -2.56), (0, 0.68, -2.80), 0.056, n=12),
                                          slot_x((0, 0.68, -2.45), 0.05, 0.07), slot_x((0, 0.68, -2.56), 0.05, 0.07)]))

    # stick magazine (dark metal) with side witness grooves, base plate (gun metal)
    mpath = [(0, 0.45, -0.955), (0, 0.0, -0.97), (0, -0.44, -1.02)]
    mrows = [(P, X, Y, prof(0.14, 0.20, 0.035, 0.035)) for (P, X, Y) in path_frames(mpath)]
    mag = loft_frames(mrows, soft=0.015)
    hput(G, DARK, "Metal", boolean(mag, [rbox((s * 0.14, -0.02, -0.98), (0.05, 0.56, 0.05), 0.02, 2) for s in (1, -1)]))
    hput(G, GUN, "Metal", zloft([(-0.78, prof(0.155, 0.05, 0.02, 0.02, cy=-0.47)),
                                 (-0.81, prof(0.17, 0.05, 0.025, 0.025, cy=-0.47)),
                                 (-1.23, prof(0.17, 0.05, 0.025, 0.025, cy=-0.47)),
                                 (-1.26, prof(0.155, 0.05, 0.02, 0.02, cy=-0.47))], soft=0.012))

    # vertical foregrip (dark plastic), rising into the shroud
    sm_vert_grip(G, DARK, "SmoothPlastic", 0.0, -1.60, -0.125, 0.53, 0.125, 0.135, nst=9)
    # magwell flare (green) round the top of the magazine
    hput(G, GRN, "SmoothPlastic", loft_frames([(V((0, y, -0.965)), X0, V((0, 0, 1)), prof(w, d, 0.04, 0.04)) for y, w, d in
                                               ((0.40, 0.17, 0.245), (0.33, 0.185, 0.262), (0.30, 0.177, 0.252))], soft=0.012))

    # wire stock: two round rails and a rising strut (gun metal), grooved butt pad (dark plastic)
    for s in (1, -1):
        hput(G, GUN, "Metal", tube([(s * 0.12, 0.72, 0.30), (s * 0.12, 0.72, 0.75), (s * 0.12, 0.715, 1.02), (s * 0.12, 0.70, 1.20)],
                                   0.045, 8))
    sp = [V((0, 0.44, 0.36)), V((0, 0.33, 0.70)), V((0, 0.47, 1.20))]
    hput(G, GUN, "Metal", tube([tuple(sp[0] * (1 - t) ** 2 + sp[1] * 2 * t * (1 - t) + sp[2] * t * t) for t in [i / 6 for i in range(7)]], 0.045, 8))
    pad = zloft([(1.155, prof(0.15, 0.285, 0.07, 0.06, cy=0.52)), (1.18, prof(0.16, 0.30, 0.075, 0.065, cy=0.52)),
                 (1.285, prof(0.16, 0.30, 0.075, 0.065, cy=0.52))], soft=0.02)
    hput(G, DARK, "SmoothPlastic", boolean(pad, [rbox((0, y, 1.29), (0.45, 0.03, 0.05), 0.012, 1) for y in (0.38, 0.52, 0.66)]))

    # charging handle knob (silver) + bolt face in the port
    hput(G, SIL, "Metal", cyl((0.19, 0.82, -0.30), (0.34, 0.82, -0.30), 0.03, n=10))
    hput(G, SIL, "Metal", ball((0.355, 0.82, -0.30), 0.045, 10, 7))
    hput(G, SIL, "Metal", rbox((0.180, 0.70, -0.86), (0.05, 0.11, 0.34), 0.018, 2))

    trigger_group(G, GUN, -0.03)
    grip(G, DARK, "SmoothPlastic", GUN, "SmoothPlastic", (0, -0.02, 0.02), hw=0.15, hd=0.23)
    return G


# ------------------------------------------------------------------ Seed Pistol

def sm_seed_slide_prof(kw=1.0, kt=1.0, cy=0.80):
    """slide section: flat flanks, sunflower-seed rounded crown; kw scales width, kt the crown height"""
    b = -0.18
    pts = [(0.18, b), (0.18, 0.07), (0.14, 0.155), (0.06, 0.18), (-0.06, 0.18), (-0.14, 0.155), (-0.18, 0.07), (-0.18, b)]
    out = [(x * kw, b + (y - b) * kt) for x, y in pts]
    return [(x, y + cy) for x, y in prof_poly(out, 0.018)]


def seed_groups():
    FR, WOOD, HWOOD = [70, 122, 62], [140, 92, 52], [92, 58, 34]
    PETAL, SEEDC, KNOB, LEAF = [255, 208, 48], [90, 55, 25], [40, 40, 40], [104, 190, 74]
    G = {}

    # slide (gun metal): seed-shaped crown, tapered nose, slanted rear serrations, two seed stripes per flank,
    # ejection port top-right
    sl = zloft([(0.325, sm_seed_slide_prof(0.82, 0.74)),
                (0.26, sm_seed_slide_prof(1.0, 1.0)),
                (-0.70, sm_seed_slide_prof(1.0, 1.0)),
                (-1.10, sm_seed_slide_prof(0.97, 0.93)),
                (-1.30, sm_seed_slide_prof(0.92, 0.82)),
                (-1.425, sm_seed_slide_prof(0.82, 0.68))], soft=0.02)
    cuts = [rbox((0.105, 0.985, -0.24), (0.17, 0.13, 0.30), 0.03, 2)]
    for s in (1, -1):
        for z in (0.22, 0.13, 0.04, -0.05):
            cuts.append(rbox((s * 0.18, 0.82, z), (0.05, 0.24, 0.035), 0.015, 1, rxm(math.radians(-12))))
        cuts.append(rbox((s * 0.18, 0.73, -0.78), (0.045, 0.032, 0.86), 0.015, 2))
        cuts.append(rbox((s * 0.18, 0.865, -0.70), (0.045, 0.032, 0.70), 0.015, 2))
    hput(G, GUN, "Metal", boolean(sl, cuts))

    # dark metal: barrel hood in the port, crowned muzzle with a bore, skeleton hammer
    hput(G, DARK, "Metal", rbox((0.06, 0.925, -0.24), (0.24, 0.08, 0.28), 0.03, 2))
    mz = cyl((0, 0.80, -1.38), (0, 0.80, -1.70), 0.10, n=18, mids=[(0.85, 0.10)], soft=0.02)
    hput(G, DARK, "Metal", boolean(mz, [cyl((0, 0.80, -1.55), (0, 0.80, -1.80), 0.05, n=12)]))
    ham = rbox((0, 0.92, 0.36), (0.10, 0.16, 0.10), 0.035, 2, rxm(math.radians(-30)))
    hput(G, DARK, "Metal", boolean(ham, [cyl((-0.1, 0.95, 0.375), (0.1, 0.95, 0.375), 0.024, n=10)]))

    # the seed loaded in the muzzle (seed brown)
    hput(G, SEEDC, "SmoothPlastic", ball((0, 0.80, -1.63), 0.045, 10, 7, 1.0, 1.0, 1.5))

    # sights (dark plastic): front post, notched rear sight
    hput(G, DARK, "SmoothPlastic", rbox((0, 0.95, -1.32), (0.06, 0.10, 0.08), 0.02, 2))
    rear = rbox((0, 1.02, 0.20), (0.24, 0.10, 0.08), 0.02, 2)
    hput(G, DARK, "SmoothPlastic", boolean(rear, [rbox((0, 1.07, 0.20), (0.05, 0.08, 0.2), 0.012, 1)]))

    # glowing seed inlay on the crown (leaf-green neon)
    o = densify([(0.0, 0.0), (0.07, 0.062), (0.25, 0.088), (0.46, 0.072), (0.64, 0.0), (0.46, -0.072), (0.25, -0.088), (0.07, -0.062)], 2)
    a, b = pillow(o, (0, 0.976, -0.42), (0, 0, -1), (1, 0, 0), (0, 1, 0), 0.04, 0.6)
    hput(G, LEAF, "Neon", (a, fix_winding(a, b)))

    # frame (green): dust cover with accessory-rail grooves underneath
    fr = zloft([(0.255, prof(0.13, 0.12, 0.03, 0.06, cy=0.50)),
                (0.20, prof(0.15, 0.14, 0.03, 0.07, cy=0.50)),
                (-0.70, prof(0.15, 0.14, 0.03, 0.07, cy=0.50)),
                (-0.98, prof(0.15, 0.125, 0.03, 0.07, cy=0.515)),
                (-1.095, prof(0.135, 0.105, 0.03, 0.06, cy=0.53))], soft=0.02)
    hput(G, FR, "SmoothPlastic", boolean(fr, [rbox((0, 0.36, -0.72 - 0.11 * i), (0.4, 0.045, 0.05), 0.012, 1) for i in range(3)]))

    # raised seed emblems on both frame flanks
    for s in (1, -1):
        so = densify([(0.0, 0.0), (0.05, 0.045), (0.17, 0.062), (0.30, 0.045), (0.38, 0.0), (0.30, -0.045), (0.17, -0.062), (0.05, -0.045)], 2)
        a, b = pillow(so, (s * 0.15, 0.50, -0.38), (0, 0, -1), (0, 1, 0), (s, 0, 0), 0.03, 0.55)
        hput(G, FR, "SmoothPlastic", (a, fix_winding(a, b)))

    # takedown knob (right)
    hput(G, KNOB, "SmoothPlastic", ball((0.19, 0.80, -0.25), 0.08, 12, 8, 0.95, 1.0, 1.0))

    # grip (dark wood core, light wood ribbed panels) and a raked base plate following the butt
    gc = V((0, -0.03, 0.03))
    grip(G, HWOOD, "Wood", WOOD, "Wood", tuple(gc), hw=0.15, hd=0.235)
    R = rxm(math.radians(-14))
    U, F = R @ Y0, R @ V((0, 0, -1))
    hput(G, GUN, "Metal", loft_frames([(gc + U * t, X0, F, prof(w, d, 0.03, 0.03)) for t, w, d in
                                       ((-0.505, 0.165, 0.235), (-0.495, 0.18, 0.25), (-0.425, 0.18, 0.25), (-0.415, 0.165, 0.235))], soft=0.012))

    # sunflower medallions on both grip sides: ten neon petals round a domed seed-brown centre
    for s in (1, -1):
        c = V((s * 0.20, 0.02, 0.02))
        W = V((s, 0, 0))
        for k in range(10):
            ang = 2 * math.pi * (k + 0.5 * (s < 0)) / 10
            u = V((0, math.cos(ang), math.sin(ang)))
            leaf(G, PETAL, "Neon", c + u * 0.05, u, W.cross(u), 0.10, 0.062, 0.022)
        hput(G, SEEDC, "SmoothPlastic", ball(tuple(c + W * 0.008), 0.075, 12, 8, 0.36, 1.0, 1.0))

    trigger_group(G, GUN, 0.0)
    # squared front of the trigger guard (where the old guard post stood)
    hput(G, GUN, "Metal", rbox((0, 0.31, -0.665), (0.06, 0.13, 0.055), 0.022, 2))
    return G


HEROES["SproutSMG"] = sprout_groups
HEROES["SeedPistol"] = seed_groups

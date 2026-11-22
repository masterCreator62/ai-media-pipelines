# Preview renders of one weapon collection (Blender, EEVEE). Usage after exec():
#   preview("SharkGun", "shark_v2")  -> renders right side, left side, 3/4 front into the renders folder
import bpy, math, os
from mathutils import Vector

RENDERS = r"H:\RobloxSweetGarden\renders\weapons-smooth-2026-11-20"
os.makedirs(RENDERS, exist_ok=True)


def _setup():
    sc = bpy.context.scene
    sc.render.engine = 'BLENDER_EEVEE'
    sc.render.resolution_x, sc.render.resolution_y = 1280, 800
    w = sc.world or bpy.data.worlds.new("W")
    sc.world = w
    w.use_nodes = True
    bg = w.node_tree.nodes.get("Background")
    bg.inputs[0].default_value = (0.32, 0.36, 0.42, 1)
    cam = bpy.data.objects.get("Cam")
    if not cam:
        cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam"))
        sc.collection.objects.link(cam)
    sc.camera = cam
    for name, loc, e in (("Key", (4, -3, 5), 900), ("Fill", (-5, 1, 2), 350), ("Rim", (0, 6, 3), 500), ("Fill2", (-4, -4, 3), 300)):
        l = bpy.data.objects.get(name)
        if not l:
            l = bpy.data.objects.new(name, bpy.data.lights.new(name, 'AREA'))
            sc.collection.objects.link(l)
        l.data.energy, l.data.size, l.location = e, 3, loc
        l.rotation_euler = (Vector((0, -1.5, 1)) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    return sc, cam


def preview(wid, tag, views=("right", "left", "front34")):
    sc, cam = _setup()
    for c in bpy.data.collections:
        if c.name.startswith("W_"):
            vis = c.name == "W_" + wid
            c.hide_render = not vis
            c.hide_viewport = not vis
    obs = bpy.data.collections["W_" + wid].objects
    lo = Vector((1e9, 1e9, 1e9)); hi = -lo
    for o in obs:
        for v in o.data.vertices:
            p = o.matrix_world @ v.co
            lo = Vector(map(min, lo, p)); hi = Vector(map(max, hi, p))
    ctr = (lo + hi) / 2
    ext = hi - lo
    # fit horizontally (length along blender y) and vertically (blender z) for a 50 mm lens, 16:10 frame
    d = 1.2 * max(max(ext.y, ext.x) / (2 * math.tan(math.radians(19.8))), ext.z / (2 * math.tan(math.radians(12.6))))
    cam.data.lens = 50
    spots = {"right": Vector((d, 0, 0.1 * d)), "left": Vector((-d, 0, 0.1 * d)),
             "front34": Vector((-0.6 * d, 0.8 * d, 0.35 * d)), "back34": Vector((0.6 * d, -0.8 * d, 0.35 * d)),
             "top": Vector((0.01, 0, d))}
    out = []
    for v in views:
        cam.location = ctr + spots[v]
        cam.rotation_euler = (ctr - cam.location).to_track_quat('-Z', 'Y').to_euler()
        path = os.path.join(RENDERS, "blender_%s_%s.png" % (tag, v))
        sc.render.filepath = path
        bpy.ops.render.render(write_still=True)
        out.append(path)
    return out

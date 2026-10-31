"""WELD-X non-destructive workcell visual enhancement for Blender 4.x.

Run: blender -b --python tools/enhance_workcell.py -- --input /path/to/demo_robotic_welding_workcell.glb --output /path/to/WELDX_Industrial_Cell_V1.blend
Markers require explicit anchors; no robot/fixture transforms are modified.
"""
import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

PREFIX = "WELDX_"
COLLECTIONS = ("WELDX_BRANDING", "WELDX_BASE_PLACEMENT", "WELDX_WELD_ANNOTATIONS", "WELDX_PRESENTATION")

def args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser()
    p.add_argument("--input", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--anchors", type=Path, help="JSON explicit world-space points; see docs/workcell.md")
    p.add_argument("--render-dir", type=Path, help="Optional PNG previews, render requires working Blender renderer")
    return p.parse_args(argv)

def collection(name):
    c = bpy.data.collections.get(name)
    if not c:
        c = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(c)
    return c

def place(obj, coll):
    for old in list(obj.users_collection):
        old.objects.unlink(obj)
    coll.objects.link(obj)
    return obj

def material(name, rgba, metallic=0.0):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.diffuse_color = rgba
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = rgba
        bsdf.inputs["Metallic"].default_value = metallic
    return m

def cube(name, center, dims, mat, coll):
    bpy.ops.mesh.primitive_cube_add(size=1, location=center)
    o = bpy.context.object
    o.name = name
    o.dimensions = dims
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    o.data.materials.append(mat)
    return place(o, coll)

def text_object(name, content, center, size, mat, coll, rotation=None):
    cu = bpy.data.curves.new(name, "FONT")
    cu.body = content
    cu.size = size
    cu.extrude = 0.0006
    ob = bpy.data.objects.new(name, cu)
    coll.objects.link(ob)
    ob.location = center
    if rotation is not None:
        ob.rotation_euler = rotation
    ob.data.materials.append(mat)
    return ob

def disk(name, center, radius, mat, coll):
    bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=radius, depth=0.006, location=center)
    o = bpy.context.object
    o.name = name
    o.data.materials.append(mat)
    return place(o, coll)

def point(value, key):
    if not isinstance(value, list) or len(value) != 3 or not all(isinstance(v, (int, float)) for v in value):
        raise ValueError(f"{key} must be [x,y,z] in world-space meters")
    return Vector(value)

def bounds(objects):
    pts = [o.matrix_world @ Vector(corner) for o in objects if o.type == "MESH" for corner in o.bound_box]
    if not pts:
        raise RuntimeError("GLB has no mesh bounds")
    return Vector([min(p[i] for p in pts) for i in range(3)]), Vector([max(p[i] for p in pts) for i in range(3)])

def camera(name, pos, target, coll):
    data = bpy.data.cameras.new(name)
    obj = bpy.data.objects.new(name, data)
    coll.objects.link(obj)
    obj.location = pos
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()
    data.lens = 35
    return obj

def main():
    a = args()
    if a.input.suffix.lower() != ".glb":
        raise ValueError("Expected a .glb input file")
    if not a.input.is_file():
        raise FileNotFoundError(a.input)
    if a.input.resolve() == a.output.resolve():
        raise ValueError("Output must not overwrite input")
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.gltf(filepath=str(a.input))
    imported = tuple(bpy.context.scene.objects)
    initial = {o.as_pointer(): tuple(tuple(row) for row in o.matrix_world) for o in imported}
    lo, hi = bounds(imported)
    center = (lo + hi) / 2
    extent = hi - lo
    scale = max(extent)
    for name in COLLECTIONS:
        collection(name)
    brand = collection(COLLECTIONS[0])
    bases = collection(COLLECTIONS[1])
    seams = collection(COLLECTIONS[2])
    presentation = collection(COLLECTIONS[3])
    white = material("WELDX_White", (0.92, 0.96, 1, 1))
    blue = material("WELDX_Blue", (0.04, 0.3, 0.85, 1))
    yellow = material("WELDX_Yellow", (0.95, 0.68, 0.03, 1))
    green = material("WELDX_Green", (0.05, 0.7, 0.25, 1))
    dark = material("WELDX_Dark", (0.018, 0.029, 0.045, 1), 0.25)
    # The sign is a floating exhibition overlay outside the bounding box,
    # NOT a claimed real mounting point on an unidentified GLB cabinet.
    sign_loc = (center.x, lo.y - 0.10 * scale, center.z + 0.25 * extent.z)
    cube("WELDX_Exhibition_Sign_Back", sign_loc, (0.58*scale, 0.012*scale, 0.13*scale), dark, brand)
    text_object("WELDX_Main_Sign", "WELD-X", (sign_loc[0]-0.26*scale, sign_loc[1]-0.01*scale, sign_loc[2]-0.005*scale),
                0.075*scale, white, brand, (math.pi/2, 0, 0))
    # Explicit, externally surveyed/user-selected anchors only.
    anchor_data = json.loads(a.anchors.read_text()) if a.anchors else {}
    enabled = []
    for key, color in (("original", blue), ("candidate_01", yellow), ("candidate_02", yellow), ("recommended", green)):
        if key in anchor_data.get("bases", {}):
            pos = point(anchor_data["bases"][key], key)
            disk(f"WELDX_Base_{key}", pos, 0.025*scale, color, bases)
            enabled.append(key)
    for seam_name, markers in anchor_data.get("seams", {}).items():
        for label in ("approach", "start", "end", "retreat"):
            if label in markers:
                pos = point(markers[label], seam_name + "." + label)
                disk("WELDX_" + seam_name + "_" + label, pos, 0.007*scale, yellow, seams)
    distance = max(2.2 * scale, 1.0)
    camera("WELDX_CAM_01_OVERVIEW", center + Vector((distance, -distance, 0.8*distance)), center, presentation)
    camera("WELDX_CAM_02_WORKPIECE", center + Vector((0.45*distance, -0.7*distance, 0.5*distance)), center, presentation)
    camera("WELDX_CAM_03_COMMISSIONING", center + Vector((-0.8*distance, -0.8*distance, 0.7*distance)), center, presentation)
    bpy.context.scene.camera = bpy.data.objects["WELDX_CAM_01_OVERVIEW"]
    bpy.context.scene.render.engine = "BLENDER_EEVEE_NEXT" if bpy.app.version >= (4, 2, 0) else "BLENDER_EEVEE"
    bpy.context.scene.render.resolution_x = 1280
    bpy.context.scene.render.resolution_y = 720
    bpy.context.scene.render.resolution_percentage = 100
    unchanged = all(tuple(tuple(row) for row in o.matrix_world) == initial[o.as_pointer()] for o in imported)
    if not unchanged:
        raise AssertionError("Imported object transform changed")
    a.output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(a.output))
    report = {"input": str(a.input), "output": str(a.output), "imported_objects": len(imported),
              "bounds_scene_units": [list(lo), list(hi)], "scene_units_verified_meters": False,
              "imported_transforms_unchanged": unchanged, "base_marker_keys": enabled,
              "collections": list(COLLECTIONS),
              "limitations": ["GLB dimensions are not independently calibrated to meters",
                              "Markers are illustrative and require validated user anchors",
                              "Welding feasibility, collision safety, and ROS/Gazebo synchronization not tested"]}
    report_path = a.output.with_suffix(".report.json")
    report_path.write_text(json.dumps(report, indent=2))
    if a.render_dir:
        a.render_dir.mkdir(parents=True, exist_ok=True)
        for i, name in enumerate(("WELDX_CAM_01_OVERVIEW", "WELDX_CAM_02_WORKPIECE", "WELDX_CAM_03_COMMISSIONING"), 1):
            bpy.context.scene.camera = bpy.data.objects[name]
            bpy.context.scene.render.filepath = str(a.render_dir / f"CAM_0{i}.png")
            bpy.ops.render.render(write_still=True)
    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    main()

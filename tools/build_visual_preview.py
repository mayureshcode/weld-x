#!/usr/bin/env python3
"""NON-COLLIDABLE Gazebo visual preview of WELD-X_final.glb.

Preserves original binary source. Excludes the decorative robot and second
scene branch; the positioner remains a STATIC visual, not a joint model.
"""
from __future__ import annotations
import argparse
from copy import deepcopy
import hashlib
from html import escape
import json
from pathlib import Path
import struct
import sys

JSON_CHUNK = 0x4E4F534A


def split_glb(source: Path) -> tuple[bytes, dict]:
    raw = source.read_bytes()
    if len(raw) < 20:
        raise ValueError("Source GLB is too short")
    magic, version, length = struct.unpack_from("<4sII", raw)
    if magic != b"glTF" or version != 2 or length != len(raw):
        raise ValueError("Expected complete glTF 2.0 binary")
    chunks, offset = [], 12
    while offset + 8 <= len(raw):
        size, kind = struct.unpack_from("<II", raw, offset)
        offset += 8
        if offset + size > len(raw):
            raise ValueError("Bad GLB chunk boundary")
        chunks.append((kind, raw[offset:offset + size]))
        offset += size
    if offset != len(raw) or not chunks or chunks[0][0] != JSON_CHUNK:
        raise ValueError("GLB JSON chunk missing or malformed")
    document = json.loads(chunks[0][1].decode("utf-8"))
    nodes = document["nodes"]
    names = [n.get("name", "") for n in nodes]

    def unique(name):
        matches = [i for i, item in enumerate(names) if item == name]
        if len(matches) != 1:
            raise ValueError(f"Expected one {name}, found {len(matches)}")
        return matches[0]

    workcell = unique("WELDX_WORKCELL_ROOT")
    robot = unique("WELDX_ROBOT_ROOT")
    positioner = unique("WELDX_POSITIONER_ROOT")

    def reachable(root):
        found, pending = set(), [root]
        while pending:
            i = pending.pop()
            if i in found:
                continue
            if i < 0 or i >= len(nodes):
                raise ValueError("Invalid node index")
            found.add(i)
            pending.extend(nodes[i].get("children", []))
        return found

    scene_index = document.get("scene", 0)
    scene = document["scenes"][scene_index]
    roots = [i for i in scene.get("nodes", []) if workcell in reachable(i)]
    if len(roots) != 1:
        raise ValueError("Ambiguous primary workcell scene")
    if robot not in reachable(workcell) or positioner not in reachable(workcell):
        raise ValueError("Robot or positioner outside main workcell")
    parents = [i for i, n in enumerate(nodes) if robot in n.get("children", [])]
    if len(parents) != 1:
        raise ValueError("Ambiguous robot parent; refusing duplicate robot")

    result = deepcopy(document)
    result["scenes"][scene_index]["nodes"] = roots
    parent = parents[0]
    result["nodes"][parent]["children"] = [
        i for i in nodes[parent]["children"] if i != robot
    ]
    # Static CAD preview: do not attempt to play/interpret Blender animations.
    result.pop("animations", None)
    payload = json.dumps(result, separators=(",", ":"), ensure_ascii=False).encode()
    payload += b" " * ((-len(payload)) % 4)
    chunks = [(JSON_CHUNK, payload)] + chunks[1:]
    total = 12 + sum(8 + len(blob) for _, blob in chunks)
    output = bytearray(struct.pack("<4sII", b"glTF", 2, total))
    for kind, blob in chunks:
        output += struct.pack("<II", len(blob), kind) + blob
    info = {
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "exported_sha256": hashlib.sha256(output).hexdigest(),
        "original_scene_roots": len(scene.get("nodes", [])),
        "exported_scene_roots": len(roots),
        "decorative_robot_excluded": True,
        "positioner_static_visual_only": True,
        "collision_geometry_included": False,
        "valid_for_robotics_execution": False,
        "coordinate_note": "Candidate +90 degree X-axis conversion: inspect in Gazebo",
    }
    return bytes(output), info


def world_sdf(mesh: Path) -> str:
    uri = escape(mesh.resolve().as_uri())
    return f'''<?xml version="1.0"?>
<sdf version="1.9"><world name="weldx_cell">
  <physics name="physics" type="ignored"><max_step_size>0.001</max_step_size><real_time_factor>1</real_time_factor></physics>
  <plugin filename="gz-sim-physics-system" name="gz::sim::systems::Physics"/>
  <plugin filename="gz-sim-user-commands-system" name="gz::sim::systems::UserCommands"/>
  <plugin filename="gz-sim-scene-broadcaster-system" name="gz::sim::systems::SceneBroadcaster"/>
  <light name="key" type="directional"><pose>0 0 6 0 0 0</pose><diffuse>1 1 1 1</diffuse><specular>0.4 0.4 0.4 1</specular><direction>-0.4 -0.4 -1</direction><cast_shadows>true</cast_shadows></light>
  <scene><ambient>0.5 0.5 0.5 1</ambient><background>0.06 0.07 0.08 1</background><shadows>true</shadows></scene>
  <model name="ground"><static>true</static><pose>0 0 -0.1 0 0 0</pose><link name="ground"><collision name="ground"><geometry><box><size>15 15 0.2</size></box></geometry></collision><visual name="ground"><geometry><box><size>15 15 0.2</size></box></geometry><material><diffuse>0.15 0.17 0.19 1</diffuse></material></visual></link></model>
  <model name="weldx_vnext_visual_preview"><static>true</static><pose>0 0 0 1.57079632679 0 0</pose><link name="shell"><visual name="cad_shell"><geometry><mesh><uri>{uri}</uri><scale>1 1 1</scale></mesh></geometry></visual></link></model>
</world></sdf>
'''


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("--output-dir", type=Path, default=Path("assets_vnext/exports"))
    args = parser.parse_args()
    try:
        data, info = split_glb(args.source)
        args.output_dir.mkdir(parents=True, exist_ok=True)
        glb = args.output_dir / "weldx_shell_preview.glb"
        sdf = args.output_dir / "weldx_visual_preview.sdf"
        report = args.output_dir / "weldx_visual_preview_report.json"
        glb.write_bytes(data)
        sdf.write_text(world_sdf(glb))
        report.write_text(json.dumps(info, indent=2) + "\n")
    except (OSError, KeyError, IndexError, ValueError, TypeError, struct.error) as exc:
        print(f"Visual-preview generation refused: {exc}", file=sys.stderr)
        return 2
    print(f"Visual-only preview: {sdf}\n{json.dumps(info, indent=2)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

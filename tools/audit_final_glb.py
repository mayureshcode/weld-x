#!/usr/bin/env python3
"""Read-only structural gate for the source WELD-X GLB (no Blender dependency).

It does not infer robot kinematics from animation curves and never changes the
binary source. Its output is evidence for, not a substitute for, mechanical
link mapping and simulation validation.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys

ROBOT = "WELDX_ROBOT_ROOT"
POSITIONER = "WELDX_POSITIONER_ROOT"
WORKCELL = "WELDX_WORKCELL_ROOT"


def parse_glb(path: Path) -> tuple[dict, str]:
    data = path.read_bytes()
    if len(data) < 20:
        raise ValueError("GLB too short")
    magic, version, length = struct.unpack_from("<4sII", data)
    if magic != b"glTF" or version != 2 or length != len(data):
        raise ValueError("Invalid GLB v2 header/size")
    off = 12
    document = None
    while off + 8 <= len(data):
        size, chunk_type = struct.unpack_from("<II", data, off)
        off += 8
        if off + size > len(data):
            raise ValueError("Invalid GLB chunk length")
        if chunk_type == 0x4E4F534A:
            if document is not None:
                raise ValueError("Multiple JSON chunks")
            document = json.loads(data[off:off + size].decode("utf-8"))
        off += size
    if off != len(data) or document is None:
        raise ValueError("Truncated GLB or missing JSON chunk")
    return document, hashlib.sha256(data).hexdigest()


def analyze(document: dict, digest: str) -> dict:
    nodes = document.get("nodes", [])
    scenes = document.get("scenes", [])
    if not isinstance(nodes, list) or not scenes:
        raise ValueError("GLB contains no valid node graph/scenes")
    children = {i: n.get("children", []) for i, n in enumerate(nodes)}
    for i, descendants in children.items():
        if any(not isinstance(j, int) or j < 0 or j >= len(nodes) for j in descendants):
            raise ValueError(f"Invalid child reference on node {i}")
    names = [n.get("name", "") for n in nodes]

    def descendants(index: int) -> set[int]:
        found, visiting = set(), set()
        def walk(i: int) -> None:
            if i in visiting:
                raise ValueError("Cycle in glTF node tree")
            if i in found:
                return
            visiting.add(i)
            found.add(i)
            for child in children[i]:
                walk(child)
            visiting.remove(i)
        walk(index)
        return found

    scene_index = document.get("scene", 0)
    if not isinstance(scene_index, int) or scene_index >= len(scenes):
        raise ValueError("Invalid selected scene")
    scene_roots = scenes[scene_index].get("nodes", [])
    reachable = set()
    for root in scene_roots:
        if not isinstance(root, int) or root < 0 or root >= len(nodes):
            raise ValueError("Invalid scene root")
        reachable.update(descendants(root))

    warnings = []
    roots = {}
    for label in (WORKCELL, ROBOT, POSITIONER):
        matches = [i for i, n in enumerate(names) if n == label and i in reachable]
        roots[label] = matches
        if len(matches) != 1:
            warnings.append(f"Expected one {label}, found {len(matches)}")
    robot_nodes = descendants(roots[ROBOT][0]) if len(roots[ROBOT]) == 1 else set()
    positioner_nodes = descendants(roots[POSITIONER][0]) if len(roots[POSITIONER]) == 1 else set()
    workcell_nodes = descendants(roots[WORKCELL][0]) if len(roots[WORKCELL]) == 1 else set()
    if robot_nodes & positioner_nodes:
        warnings.append("Robot and positioner hierarchies overlap")
    extras = reachable - workcell_nodes
    if extras:
        warnings.append("Secondary scene branch found; inspect before export")
    animated = set()
    for animation in document.get("animations", []):
        for channel in animation.get("channels", []):
            idx = channel.get("target", {}).get("node")
            if isinstance(idx, int):
                animated.add(idx)
    unclassified = sorted(animated & workcell_nodes - robot_nodes - positioner_nodes)
    if unclassified:
        warnings.append("Animated workcell nodes outside robot/positioner need manual ownership")
    static_nodes = workcell_nodes - robot_nodes - positioner_nodes
    mesh_count = lambda group: sum("mesh" in nodes[i] for i in group)
    duplicates = [name for name in names if name.startswith((ROBOT + ".", WORKCELL + ".", POSITIONER + "."))]
    if duplicates:
        warnings.append("Duplicated named root(s) present")

    return {
        "sha256": digest,
        "nodes": len(nodes),
        "meshes": len(document.get("meshes", [])),
        "materials": len(document.get("materials", [])),
        "animations": len(document.get("animations", [])),
        "scene_roots": [{"index": i, "name": names[i]} for i in scene_roots],
        "primary_roots": roots,
        "visual_mesh_counts": {
            "robot": mesh_count(robot_nodes),
            "positioner": mesh_count(positioner_nodes),
            "static_candidate": mesh_count(static_nodes),
            "other_scene_branches": mesh_count(extras),
        },
        "unclassified_animation_nodes": [
            {"index": i, "name": names[i]} for i in unclassified
        ],
        "duplicate_named_roots": duplicates,
        "warnings": warnings,
        "ready_for_automatic_static_export": not warnings,
        "kinematics_verified": False,
        "gazebo_collision_verified": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("glb", type=Path)
    parser.add_argument("--report", type=Path, help="JSON report destination")
    parser.add_argument("--strict", action="store_true",
                        help="return 2 when the export gates find warnings")
    args = parser.parse_args()
    try:
        document, digest = parse_glb(args.glb)
        report = analyze(document, digest)
    except (OSError, ValueError, KeyError, TypeError, struct.error) as error:
        print(f"WELD-X GLB audit failed: {error}", file=sys.stderr)
        return 2
    result = json.dumps(report, indent=2)
    print(result)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(result + "\n")
    return 2 if args.strict and report["warnings"] else 0


if __name__ == "__main__":
    sys.exit(main())

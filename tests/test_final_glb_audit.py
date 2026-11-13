"""Synthetic tests: this auditor never claims that a GLB is a physical robot."""
import json
from pathlib import Path
import struct
import tempfile
import unittest
from tools.audit_final_glb import analyze, parse_glb

class GLBAuditTests(unittest.TestCase):
    def fixture(self):
        return {
            "scene": 0,
            "scenes": [{"nodes": [0]}],
            "nodes": [
                {"name": "WELDX_WORKCELL_ROOT", "children": [1, 2, 3]},
                {"name": "WELDX_ROBOT_ROOT", "children": [4]},
                {"name": "WELDX_POSITIONER_ROOT", "children": [5]},
                {"name": "wall", "mesh": 0},
                {"name": "robot_link", "mesh": 1},
                {"name": "disc", "mesh": 2},
            ],
            "meshes": [{}, {}, {}],
            "animations": [{"channels": [{"target": {"node": 4, "path": "rotation"}}]}],
        }

    def test_clean_partition_is_only_structural(self):
        report = analyze(self.fixture(), "example")
        self.assertEqual(report["visual_mesh_counts"],
                         {"robot": 1, "positioner": 1,
                          "static_candidate": 1, "other_scene_branches": 0})
        self.assertTrue(report["ready_for_automatic_static_export"])
        self.assertFalse(report["kinematics_verified"])
        self.assertFalse(report["gazebo_collision_verified"])

    def test_unclassified_animated_node_blocks_export(self):
        sample = self.fixture()
        sample["animations"][0]["channels"].append(
            {"target": {"node": 3, "path": "rotation"}})
        report = analyze(sample, "example")
        self.assertFalse(report["ready_for_automatic_static_export"])
        self.assertEqual(report["unclassified_animation_nodes"][0]["name"], "wall")

    def test_secondary_root_blocks_auto_export(self):
        sample = self.fixture()
        sample["scenes"][0]["nodes"].append(6)
        sample["nodes"].append({"name": "Sketchfab_model.001", "mesh": 3})
        sample["meshes"].append({})
        report = analyze(sample, "example")
        self.assertFalse(report["ready_for_automatic_static_export"])
        self.assertEqual(report["visual_mesh_counts"]["other_scene_branches"], 1)

    def test_glb_header_and_json_bounds(self):
        doc = self.fixture()
        raw = json.dumps(doc).encode()
        raw += b" " * ((-len(raw)) % 4)
        data = struct.pack("<4sII", b"glTF", 2, 20 + len(raw))
        data += struct.pack("<II", len(raw), 0x4E4F534A) + raw
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "fixture.glb"
            path.write_bytes(data)
            document, digest = parse_glb(path)
            self.assertEqual(document["nodes"], doc["nodes"])
            self.assertEqual(len(digest), 64)
            path.write_bytes(data[:-4])
            with self.assertRaises(ValueError):
                parse_glb(path)

if __name__ == "__main__":
    unittest.main()

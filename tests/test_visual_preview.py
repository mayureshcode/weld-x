"""Non-ROS tests for the VNext visual-only GLB partitioner."""
import json
from pathlib import Path
import struct
import tempfile
import unittest
import xml.etree.ElementTree as ET
from tools.build_visual_preview import split_glb, world_sdf

class PreviewTests(unittest.TestCase):
    def glb(self):
        doc = {
            "scene": 0, "scenes": [{"nodes": [0, 5]}],
            "nodes": [
                {"name": "Sketchfab_model", "children": [1]},
                {"name": "WELDX_WORKCELL_ROOT", "children": [2, 3, 4]},
                {"name": "WELDX_ROBOT_ROOT", "children": [6]},
                {"name": "WELDX_POSITIONER_ROOT", "children": [7]},
                {"name": "wall", "mesh": 0},
                {"name": "Sketchfab_model.001", "mesh": 1},
                {"name": "robot_visual", "mesh": 2},
                {"name": "positioner_visual", "mesh": 3},
            ],
            "meshes": [{}, {}, {}, {}],
            "animations": [{"channels": [{"target": {"node": 6, "path": "rotation"}}]}]
        }
        payload = json.dumps(doc).encode()
        payload += b" " * (-len(payload) % 4)
        raw = struct.pack("<4sII", b"glTF", 2, 20 + len(payload))
        raw += struct.pack("<II", len(payload), 0x4E4F534A) + payload
        return raw

    def test_excludes_decorative_robot_and_extra_branch(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder) / "scene.glb"
            p.write_bytes(self.glb())
            data, evidence = split_glb(p)
            size = struct.unpack_from("<I", data, 12)[0]
            doc = json.loads(data[20:20 + size].decode("utf-8"))
            self.assertEqual(doc["scenes"][0]["nodes"], [0])
            self.assertEqual(doc["nodes"][1]["children"], [3, 4])
            self.assertNotIn("animations", doc)
            self.assertEqual(evidence["decorative_robot_excluded"], True)
            self.assertFalse(evidence["valid_for_robotics_execution"])

    def test_sdf_has_no_shell_collision(self):
        sdf = world_sdf(Path("/tmp/fake.glb"))
        root = ET.fromstring(sdf)
        self.assertEqual(root.find(".//world").attrib["name"], "weldx_cell")
        self.assertIsNone(root.find(".//model[@name='weldx_vnext_visual_preview']//collision"))
        self.assertIn("1.57079632679", sdf)

    def test_corrupt_binary_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder) / "broken.glb"
            p.write_bytes(self.glb()[:-1])
            with self.assertRaises(ValueError):
                split_glb(p)


if __name__ == "__main__":
    unittest.main()

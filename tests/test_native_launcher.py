"""Offline smoke checks of the native launcher; not a Gazebo acceptance test."""
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "start_weldx.sh"


class NativeLauncherTests(unittest.TestCase):
    def test_shell_parses(self):
        result = subprocess.run(["bash", "-n", str(SCRIPT)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_help_does_not_require_ros(self):
        result = subprocess.run(["bash", str(SCRIPT), "--help"], cwd=ROOT,
                                capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--dashboard-only", result.stdout)
        self.assertIn("--no-gui", result.stdout)

    def test_bad_option_rejected_without_launching(self):
        result = subprocess.run(["bash", str(SCRIPT), "--not-an-option"], cwd=ROOT,
                                capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 2)

    def test_root_entrypoint_and_default_visual_preview(self):
        wrapper = ROOT / 'start_weldx.sh'
        result = subprocess.run(['bash', '-n', str(wrapper)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('scripts/start_weldx.sh', wrapper.read_text())
        launcher = SCRIPT.read_text()
        self.assertIn('MODE=visual-preview', launcher)
        self.assertIn('--simulation|--baseline', launcher)
        self.assertIn('build_visual_preview.py', launcher)
        self.assertNotIn('MODE=simulation\\nGUI=1', launcher)

    def test_portability_and_process_scope(self):
        launch = (ROOT / "ros_ws/src/weldx_bringup/launch/cell.launch.py").read_text()
        cell = (ROOT / "robotics/cell.py").read_text()
        adapter = (ROOT / "robotics/adapter.py").read_text()
        self.assertIn("WELDX_GENERATED_DIR", launch)
        self.assertIn("WELDX_GENERATED_DIR", cell)
        self.assertIn("WELDX_PROJECT_ROOT", adapter)
        self.assertNotIn("'/workspace/.runtime/generated", cell)
        script = SCRIPT.read_text()
        self.assertNotIn("killall", script)
        self.assertIn("--robotics", script)
        self.assertIn("ros2 control list_controllers", script)


if __name__ == "__main__":
    unittest.main()

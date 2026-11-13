#!/usr/bin/env bash
# No simulation or motion commands. Offline static checks and unit tests.
set -Eeuo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
bash -n scripts/start_weldx.sh
python3 -m compileall -q weldx robotics tests tests_robotics tools/audit_final_glb.py tools/build_visual_preview.py ros_ws/src/weldx_bringup/launch
python3 -m unittest tests.test_native_launcher tests.test_final_glb_audit tests.test_visual_preview -v
if command -v node >/dev/null; then
  node --check dashboard/app.js
  node --check dashboard/scene.js
else
  echo "Node not found: skipped JavaScript syntax checks" >&2
fi
echo "Static WELD-X checks complete. Native ROS acceptance is NOT included."

#!/usr/bin/env bash
set -euo pipefail

# Run from a checked-out weld-x repository on Ubuntu 24.04.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "WELD-X source: $ROOT"
echo "Branch: $(git branch --show-current)"
python3 --version
if ! python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3,12) else 1)'; then
  echo "Python 3.12+ required" >&2
  exit 2
fi

if [ ! -d .venv ]; then python3 -m venv .venv; fi
source .venv/bin/activate
python -m pip install -e .
python -m unittest discover -v
python -m compileall -q weldx tests
if command -v node >/dev/null 2>&1; then node --check dashboard/app.js; else echo "Node missing: browser script syntax not checked"; fi

GLB="$ROOT/assets/source/demo_robotic_welding_workcell.glb"
if [ -f "$GLB" ]; then
  echo '582e97563443be6e3fae4880a72d5442510ebccb8f3b379a2e745b521c23185f  assets/source/demo_robotic_welding_workcell.glb' | sha256sum -c -
else
  echo "GLB absent: place the original file at $GLB before Blender conversion."
fi

echo
echo "Start dashboard with:"
echo "  source .venv/bin/activate"
echo "  python -m weldx.server --config examples/job_01.json --audit .runtime/audit.jsonl"
echo "  open http://127.0.0.1:8765 locally"
echo
echo "With Blender installed, generate the non-destructive workcell scene:"
echo "  blender -b --python tools/enhance_workcell.py -- --input assets/source/demo_robotic_welding_workcell.glb --output outputs/WELDX_Industrial_Cell_V1.blend --render-dir outputs/previews"
echo
echo "WARNING: running this dashboard does NOT run ROS 2, Gazebo, MoveIt 2 or robotic execution."

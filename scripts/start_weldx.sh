#!/usr/bin/env bash
# WELD-X single entry point. Visual UI + read-only ROS telemetry by default.
# --simulation additionally starts an EXPLICIT, existing ROS 2 simulation launch.
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
MODE="${1:---visual}"
if [[ "$MODE" != "--visual" && "$MODE" != "--simulation" ]]; then
  echo "Usage: bash scripts/start_weldx.sh [--visual|--simulation]" >&2; exit 2
fi
GLB="assets/source/demo_robotic_welding_workcell.glb"
if [[ ! -f "$GLB" ]]; then
  echo "Missing original GLB: $ROOT/$GLB" >&2
  echo "Copy your uploaded GLB to this path; see docs/live-workcell.md." >&2; exit 2
fi
EXPECTED="582e97563443be6e3fae4880a72d5442510ebccb8f3b379a2e745b521c23185f"
ACTUAL="$(sha256sum "$GLB" | awk '{print $1}')"
if [[ "$ACTUAL" != "$EXPECTED" ]]; then
  echo "GLB checksum mismatch; refusing to display unidentified source asset" >&2; exit 2
fi
if [[ -f /opt/ros/jazzy/setup.bash ]]; then
  set +u; source /opt/ros/jazzy/setup.bash; set -u
fi
if ! command -v python3 >/dev/null || ! python3 -c 'import sys;assert sys.version_info>=(3,12)' 2>/dev/null; then
  echo "Python 3.12+ required (Ubuntu 24.04)" >&2; exit 2
fi
if ! command -v npm >/dev/null; then echo "Node.js and npm required" >&2; exit 2; fi
if [[ ! -f node_modules/three/build/three.module.js ]]; then
  echo "Installing pinned local Three.js package (internet required only for first installation)..."
  npm install --no-audit --no-fund --ignore-scripts
fi
if [[ ! -d .venv ]]; then python3 -m venv --system-site-packages .venv; fi
source .venv/bin/activate
if ! python -c "import pydantic;import weldx" >/dev/null 2>&1; then
  python -m pip install -e .
fi
mkdir -p .runtime
# Never reuse stale joint samples from earlier ROS sessions.
rm -f .runtime/ros_telemetry.json
pids=()
cleanup(){
  trap - EXIT INT TERM
  for pid in "${pids[@]}"; do kill "$pid" 2>/dev/null || true; done
  for pid in "${pids[@]}"; do wait "$pid" 2>/dev/null || true; done
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
if [[ "$MODE" == "--simulation" ]]; then
  if [[ -z "${WELDX_ROS_LAUNCH_PACKAGE:-}" || -z "${WELDX_ROS_LAUNCH_FILE:-}" ]]; then
    echo "Simulation launch not configured. Set WELDX_ROS_LAUNCH_PACKAGE and WELDX_ROS_LAUNCH_FILE" >&2
    echo "The WELD-X repository does not yet have a commissioned ABB IRB120 simulator." >&2
    exit 2
  fi
  if ! command -v ros2 >/dev/null; then echo "ROS 2 Jazzy not available" >&2; exit 2; fi
  echo "Launching configured simulator: $WELDX_ROS_LAUNCH_PACKAGE / $WELDX_ROS_LAUNCH_FILE"
  ros2 launch "$WELDX_ROS_LAUNCH_PACKAGE" "$WELDX_ROS_LAUNCH_FILE" >.runtime/simulation.log 2>&1 &
  pids+=("$!")
fi
if python -c "import rclpy; from sensor_msgs.msg import JointState; from tf2_msgs.msg import TFMessage" >/dev/null 2>&1; then
  echo "Starting read-only ROS 2 bridge..."
  python scripts/ros_telemetry.py --output .runtime/ros_telemetry.json >.runtime/telemetry.log 2>&1 &
  pids+=("$!")
else
  echo "ROS 2 packages unavailable: 3D GLB remains inspectable but live telemetry is offline."
fi
PORT="${WELDX_PORT:-8765}"
python -m weldx.server --port "$PORT" --config examples/job_01.json --audit .runtime/audit.jsonl \
  --workcell "$GLB" --telemetry .runtime/ros_telemetry.json &
pids+=("$!")
echo
echo "WELD-X console: http://127.0.0.1:$PORT"
echo "Mode: $MODE. Viewer loads static original GLB; ROS telemetry never authorizes motion."
echo "Stop all launcher-owned processes with Ctrl+C."
wait "${pids[-1]}"

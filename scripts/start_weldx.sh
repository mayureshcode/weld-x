#!/usr/bin/env bash
# WELD-X native Ubuntu session. All components launched from ONE command.
# Simulation-only: does not command motion or connect physical drivers.
set -Eeuo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
MODE=visual-preview
GUI=1
for arg in "$@"; do
 case "$arg" in
  --simulation|--baseline) MODE=simulation ;;
  --dashboard-only) MODE=dashboard-only; GUI=0 ;;
  --visual-preview) MODE=visual-preview ;;
  --no-gui) GUI=0 ;;
  -h|--help)
   echo "Usage: ./start_weldx.sh [--visual-preview|--baseline] [--no-gui|--dashboard-only]"
   echo "Options: WELDX_PYTHON, WELDX_PORT, WELDX_JOB_CONFIG, WELDX_OPEN_BROWSER=0"
   echo "Default: latest visual-only workcell; use --baseline for legacy validated robot/cell."
   exit 0 ;;
  *) echo "Unknown argument: $arg" >&2; exit 2 ;;
 esac
done
export ROS_DOMAIN_ID=189 GZ_PARTITION=weldx_virtual
export WELDX_PROJECT_ROOT="$ROOT" WELDX_GENERATED_DIR="$ROOT/.runtime/generated"
PORT="${WELDX_PORT:-8765}"
CONFIG="${WELDX_JOB_CONFIG:-examples/commissioning_two_seam.json}"
[[ "$PORT" =~ ^[0-9]+$ ]] || { echo "Invalid port" >&2; exit 2; }
[[ -f "$CONFIG" ]] || { echo "Job config missing: $CONFIG" >&2; exit 2; }
LOG="$ROOT/.runtime/launcher_logs"
mkdir -p "$LOG" "$WELDX_GENERATED_DIR"
ROS_PID="" GUI_PID="" API_PID=""
cleanup(){
 trap - EXIT INT TERM
 echo "Stopping only launcher-owned WELD-X processes..."
 if [[ -n "$API_PID" ]]; then kill -TERM "$API_PID" 2>/dev/null || true; fi
 if [[ -n "$GUI_PID" ]]; then kill -TERM "$GUI_PID" 2>/dev/null || true; fi
 if [[ -n "$ROS_PID" ]]; then kill -INT "$ROS_PID" 2>/dev/null || true; fi
 for pid in "$API_PID" "$GUI_PID" "$ROS_PID"; do
  if [[ -n "$pid" ]]; then wait "$pid" 2>/dev/null || true; fi
 done
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

if [[ -f /opt/ros/jazzy/setup.bash ]]; then
 set +u
 source /opt/ros/jazzy/setup.bash
 set -u
elif [[ "$MODE" != dashboard-only ]]; then
 echo "ROS 2 Jazzy not installed" >&2; exit 2
fi
if [[ "$MODE" != dashboard-only ]]; then
 OVERLAY=""
 for path in "$ROOT/ros_ws/install_native/local_setup.bash" "$ROOT/ros_ws/install/local_setup.bash"; do
  if [[ -f "$path" ]]; then OVERLAY="$path"; break; fi
 done
 [[ -n "$OVERLAY" ]] || { echo "Build ros_ws first (no native ROS overlay)." >&2; exit 2; }
 set +u
 source "$OVERLAY"
 set -u
 for pkg in weldx_description weldx_bringup; do
  ros2 pkg prefix "$pkg" >/dev/null || { echo "Missing ROS package: $pkg" >&2; exit 2; }
 done
 command -v gz >/dev/null || { echo "Gazebo CLI not found." >&2; exit 2; }
fi

PY="${WELDX_PYTHON:-}"
if [[ -z "$PY" ]]; then
 if [[ -x "$ROOT/.venv-ros/bin/python" ]]; then PY="$ROOT/.venv-ros/bin/python"
 elif [[ -x "$ROOT/.venv/bin/python" ]]; then PY="$ROOT/.venv/bin/python"
 else echo "Create a Python venv first; see docs/native-startup.md" >&2; exit 2
 fi
fi
[[ -x "$PY" ]] || { echo "Invalid WELDX_PYTHON: $PY" >&2; exit 2; }
"$PY" -c 'from pydantic import model_validator; import weldx' || {
 echo "Backend dependencies missing. Run $PY -m pip install -e ." >&2; exit 2;
}
if [[ "$MODE" == simulation ]]; then
 "$PY" -c 'import rclpy,numpy,scipy,control_msgs,moveit_msgs' || {
  echo "Missing ROS adapter dependencies in $PY; see docs/native-startup.md" >&2; exit 2;
 }
fi
if python3 - "$PORT" <<'PORTCHECK'
import socket,sys
with socket.socket() as s:
 s.settimeout(.3)
 sys.exit(0 if s.connect_ex(("127.0.0.1",int(sys.argv[1])))==0 else 1)
PORTCHECK
then
 echo "Port $PORT already occupied: close old dashboard first." >&2; exit 2
fi

if [[ "$MODE" == visual-preview ]]; then
 SOURCE="$ROOT/assets_vnext/source/WELD-X_final.glb"
 if [[ ! -f "$SOURCE" ]]; then
  echo "Missing newest GLB: $SOURCE" >&2; exit 2
 fi
 echo "Generating VNext visual-only scene (positioner static; no CAD collision)..."
 python3 "$ROOT/tools/build_visual_preview.py" "$SOURCE" --include-visual-robot --output-dir "$ROOT/assets_vnext/exports" >"$LOG/preview-export.log" 2>&1 || {
  tail -40 "$LOG/preview-export.log" >&2; exit 1
 }
 export WELDX_WORLD_SDF="$ROOT/assets_vnext/exports/weldx_visual_preview.sdf"
 export WELDX_HIDE_SIM_ROBOT_VISUALS=1
 echo "Visual preview world: $WELDX_WORLD_SDF"
 echo "Custom GLB robot visible in its authored static pose; old simulated ABB meshes hidden."
elif [[ "$MODE" == simulation ]]; then
 unset WELDX_WORLD_SDF WELDX_HIDE_SIM_ROBOT_VISUALS
fi

if [[ "$MODE" != dashboard-only ]]; then
 echo "Starting Gazebo server, controllers, MoveIt..."
 ros2 launch weldx_bringup cell.launch.py >"$LOG/ros.log" 2>&1 &
 ROS_PID=$!
 ready=0
 for ((attempt=1; attempt<=90; attempt++)); do
  if ! kill -0 "$ROS_PID" 2>/dev/null; then
   echo "ROS launch crashed:" >&2; tail -40 "$LOG/ros.log" >&2; exit 1
  fi
  controllers="$(timeout 5 ros2 control list_controllers 2>/dev/null || true)"
  nodes="$(timeout 5 ros2 node list 2>/dev/null || true)"
  if grep -Eq 'joint_trajectory_controller[[:space:]].*[[:space:]]active' <<<"$controllers" &&
     grep -Eq 'joint_state_broadcaster[[:space:]].*[[:space:]]active' <<<"$controllers" &&
     grep -q '/move_group' <<<"$nodes"; then
   ready=1; break
  fi
  sleep 2
 done
 if [[ "$ready" -ne 1 ]]; then
  echo "ROS controllers or MoveIt not ready; refusing false-positive startup." >&2
  tail -50 "$LOG/ros.log" >&2; exit 1
 fi
 echo "Controllers and MoveIt are available."
 if [[ "$GUI" -eq 1 ]]; then
  gz sim -g >"$LOG/gazebo-gui.log" 2>&1 &
  GUI_PID=$!
 fi
fi
ARGS=(--config "$CONFIG" --audit "$ROOT/.runtime/flagship-audit.jsonl" --port "$PORT")
if [[ "$MODE" == simulation ]]; then ARGS+=(--robotics); fi
"$PY" -m weldx.server "${ARGS[@]}" >"$LOG/api.log" 2>&1 &
API_PID=$!
up=0
for ((i=1;i<=60;i++)); do
 if ! kill -0 "$API_PID" 2>/dev/null; then
  echo "API exited:" >&2; tail -60 "$LOG/api.log" >&2; exit 1
 fi
 if curl --noproxy '*' --max-time 2 -fsS "http://127.0.0.1:$PORT/api/state" >/dev/null 2>&1; then
  up=1; break
 fi
 sleep 1
done
if [[ "$up" -ne 1 ]]; then
 echo "API readiness failed:" >&2; tail -60 "$LOG/api.log" >&2; exit 1
fi
echo "WELD-X dashboard: http://127.0.0.1:$PORT"
echo "Logs: $LOG | Mode: $MODE"
echo "Virtual-only; no motion commanded. Approval gates remain enabled."
if [[ "$MODE" == visual-preview ]]; then
 echo "VISUAL PREVIEW: new GLB robot and positioner are STATIC; ROS collisions may not align with visuals."
 echo "No CAD collision model or verified new joint mapping. Dashboard execution remains LOCKED."
fi
if [[ "$GUI" -eq 1 && "${WELDX_OPEN_BROWSER:-1}" == 1 ]] && command -v xdg-open >/dev/null; then
 xdg-open "http://127.0.0.1:$PORT" >/dev/null 2>&1 || true
fi
while :; do
 for pid in "$ROS_PID" "$GUI_PID" "$API_PID"; do
  if [[ -n "$pid" ]] && ! kill -0 "$pid" 2>/dev/null; then
   echo "A launcher-owned process exited. Inspect $LOG" >&2; exit 1
  fi
 done
 sleep 2
done

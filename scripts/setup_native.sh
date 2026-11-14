#!/usr/bin/env bash
# One-time, user-scoped native setup. Do not run with sudo.
# Installs into THIS checkout only; leaves the older ~/weld-x-project intact.
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
[[ "${EUID:-$(id -u)}" -ne 0 ]] || { echo "Do not run setup as root." >&2; exit 2; }
if [[ ! -f /opt/ros/jazzy/setup.bash ]]; then
  echo "ROS 2 Jazzy not found. Install ROS/MoveIt/Gazebo first." >&2
  exit 2
fi
for program in python3 colcon; do
  command -v "$program" >/dev/null || { echo "Missing $program; install it first." >&2; exit 2; }
done
set +u
source /opt/ros/jazzy/setup.bash
set -u
mkdir -p assets_vnext/source
SOURCE="$ROOT/assets_vnext/source/WELD-X_final.glb"
LEGACY="${WELDX_SOURCE_ASSET:-$HOME/weld-x-project/assets_vnext/source/WELD-X_final.glb}"
if [[ ! -f "$SOURCE" && -f "$LEGACY" ]]; then
  echo "Copying final visual GLB from existing checkout without modifying it..."
  cp -- "$LEGACY" "$SOURCE"
fi
if [[ ! -s "$SOURCE" ]]; then
  echo "Final GLB not found at $SOURCE" >&2
  echo "Copy it there (or set WELDX_SOURCE_ASSET=/path/to/WELD-X_final.glb)." >&2
  exit 2
fi
python3 tools/audit_final_glb.py "$SOURCE" --report "$ROOT/.runtime/asset-structure.json" || {
 echo "Source GLB failed structural parsing. Refusing incomplete installation." >&2
 exit 1
}
echo "Verifying source-licensed robot meshes (does not overwrite unknown edits)..."
python3 tools/fetch-robot-assets.py
echo "Building WELD-X native ROS workspace..."
(
  cd ros_ws
  # --log-base is a colcon GLOBAL option, so it MUST precede 'build'.
  colcon --log-base log_native build --base-paths src --build-base build_native \
    --install-base install_native --symlink-install
)
set +u
source "$ROOT/ros_ws/install_native/local_setup.bash"
set -u
for pkg in weldx_description weldx_bringup; do
  ros2 pkg prefix "$pkg" >/dev/null || { echo "Missing installed ROS package $pkg" >&2; exit 1; }
done
echo "Preparing isolated ROS-visible project Python environment..."
if [[ ! -d .venv-ros ]]; then
  python3 -m venv --system-site-packages .venv-ros
fi
.venv-ros/bin/python -m pip install -e .
.venv-ros/bin/python -c 'from pydantic import model_validator; import weldx,rclpy,numpy,scipy,control_msgs,moveit_msgs' || {
  echo "Missing ROS/Python dependencies. See docs/native-startup.md." >&2
  exit 1
}
echo
echo "Native WELD-X setup complete. Next launch is ONE command:"
echo "  cd $ROOT && ./start_weldx.sh"
echo "Preview only: visual CAD shell has no collision mesh or positioner control."

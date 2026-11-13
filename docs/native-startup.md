# WELD-X native Ubuntu single-command session

> **Engineering status:** launcher and path portability are implemented; native
> Gazebo/MoveIt/dashboard integration requires on-device verification. The source
> `WELD-X_final.glb` is **not yet** a ROS-controlled articulated workcell.
> No physical welding, safety certification or autonomous execution is claimed.

## Why one command?

The ROS launch file deliberately starts the Gazebo **server** (`gz sim -s`)
so spawning, ROS controllers and MoveIt can initialize. The new wrapper starts
the matching Gazebo GUI (`gz sim -g`) **automatically** on the same
`GZ_PARTITION=weldx_virtual`, then runs the actual ROS adapter and the local
dashboard. These are still separate processes internally, but the operator
uses one command and a single ownership/shutdown scope.

## Preserving a dirty native checkout

The existing `~/weld-x-project` and nested `~/weld-x-project/weld-x`
contain uncommitted work. Do NOT `git reset --hard`, discard their changes,
or pull this branch over them. To inspect the published revision separately:

```bash
cd ~/weld-x-project
git fetch origin
git worktree add -b review/weldx-flagship ../weld-x-flagship \
  origin/feat/weldx-flagship-native-integration
cd ../weld-x-flagship
```

That creates an **independent source checkout**, not an operating ROS overlay.
Build its ROS packages and supply their licensed meshes before running it.
Don't copy an install overlay with stale absolute paths across checkouts.

## Native dependencies and build

Ubuntu 24.04, ROS 2 Jazzy, Gazebo Harmonic, MoveIt 2, ros_gz_sim,
ros_gz_bridge and gz_ros2_control are prerequisites. Use your existing
package manager or ROS setup; avoid changing system Python with pip.

```bash
cd ~/weld-x-flagship
source /opt/ros/jazzy/setup.bash
# If missing, obtain ABB-derived source meshes according to
# third_party/abb/NOTICE.md and tools/fetch-robot-assets.py.
python3 tools/fetch-robot-assets.py

cd ros_ws
colcon build --base-paths src --build-base build_native \
  --install-base install_native --log-base log_native --symlink-install
cd ..
source ros_ws/install_native/local_setup.bash

# Separate from system ROS and from any existing .venv.
python3 -m venv --system-site-packages .venv-ros
.venv-ros/bin/python -m pip install -e .
.venv-ros/bin/python -c 'import pydantic,rclpy,numpy,scipy,control_msgs,moveit_msgs'
```

If NumPy/SciPy are missing, install Ubuntu's `python3-numpy` and
`python3-scipy` packages before creating the `--system-site-packages` venv,
or install compatible versions **into the isolated venv**. Never use
`sudo pip install` into the ROS Python interpreter.

## Run

```bash
cd ~/weld-x-flagship
./start_weldx.sh
```

This performs dependency checks, refuses a preoccupied dashboard port,
starts the Gazebo server/ROS controllers/MoveIt, waits for active controllers
and the `move_group` node, starts the Gazebo GUI, and waits for the API.
The default preview keeps the API fail-closed without `--robotics`; only
`--baseline` enables the real robotics adapter for the prototype world.
The browser opens at `http://127.0.0.1:8765`. All startup and backend errors
are logged to `.runtime/launcher_logs/`.

Additional modes:

```bash
./start_weldx.sh --visual-preview  # visual-only GLB CAD shell, NO execution authority
./start_weldx.sh --no-gui
./start_weldx.sh --dashboard-only
WELDX_OPEN_BROWSER=0 ./start_weldx.sh
WELDX_JOB_CONFIG=benchmarks/recovery_v1/configuration.json ./start_weldx.sh
```

`--dashboard-only` is explicitly fail-closed without robotics;
it is for UI diagnostics only. The default example is the existing
`examples/commissioning_two_seam.json` integration fixture, not a signed
manufacturing procedure. For production safety, external physical actuation
requires a **separate, formally reviewed safety system**.

## Verify (no automatic motion)

```bash
bash tools/verify_native.sh
source /opt/ros/jazzy/setup.bash
source ros_ws/install_native/local_setup.bash
export ROS_DOMAIN_ID=189 GZ_PARTITION=weldx_virtual
ros2 control list_controllers
ros2 node list | grep move_group
ros2 topic echo /joint_states --once
curl -fsS http://127.0.0.1:8765/api/state | head -c 400
```

To validate actual joint movement, use the separate **simulation-only**
trajectory acceptance test after confirming controllers and collision
planning scene are ready. A dashboard that renders does not prove robot
kinematics, collision fidelity, or execution readiness.

## Remaining blocker — final graphite/amber GLB

The supplied `WELD-X_final.glb` currently resides locally under
`assets_vnext/source/` and is intentionally not pushed as a 30 MB Git
binary. It includes independent robot and positioner animation, plus a
possible duplicate robot branch. It cannot safely replace the ABB-derived
URDF's six separate links without measured axes and link-frame alignment.
Next: partition static cell vs robot vs positioner, establish calibrated
world/robot transforms, author simplified collision geometry, expose
independently controllable positioner joints, and verify Gazebo/MoveIt
agreement. Never add the entire animated source as a second static robot.

## Shutdown

Use Ctrl+C in the launcher terminal. Only its recorded child PIDs are
signaled; it does not use `killall` or terminate unrelated projects.
Before starting, stop **old** manually launched WELD-X sessions to avoid
port, domain and scene-writer conflicts.

## Structural audit of your final GLB

```bash
python3 tools/audit_final_glb.py assets_vnext/source/WELD-X_final.glb \\
  --report assets_vnext/reports/structure.json
# Use --strict in the actual export/release gate; nonzero flags ambiguity.
python3 tools/audit_final_glb.py assets_vnext/source/WELD-X_final.glb --strict
```

The audit is **read-only**; it reports scene roots, duplicate branches, animated
nodes outside named robot/positioner roots and whether a partition is safe for
*automatic* export. The final customized GLB is known to contain a second
small branded-robot branch and other animated subassemblies; it should fail a
strict partition gate until ownership and exclusions are reviewed. The audit
never asserts calibrated URDF joints or valid Gazebo collision geometry.

## Latest enclosure preview (no commissioning authority)

The final source GLB is local and is **not included in the Git repository**.
In the independent `~/weld-x-flagship` worktree:

```bash
mkdir -p assets_vnext/source
cp ~/weld-x-project/assets_vnext/source/WELD-X_final.glb assets_vnext/source/
bash scripts/start_weldx.sh --visual-preview
```

This automatically generates `assets_vnext/exports/weldx_shell_preview.glb`,
`weldx_visual_preview.sdf`, and a JSON report. The GLB source remains unchanged;
the decorative GLB robot and extra branded scene branch are excluded. The full
positioner is only a **static appearance**, and the existing ROS robot still
uses the previously verified ABB-derived kinematic model. The preview applies
a *candidate* +90 degree X-axis glTF-to-Gazebo orientation; visually inspect
scale/position and do not treat it as calibrated.

**Hard restrictions:** no CAD wall collisions or positioner controllers are
present in this mode. The launcher deliberately runs the dashboard without
`--robotics` to keep execution locked. This mode is for inspecting the final
appearance and ROS model coexistence only, not collision-safe robot movement.
Use `--baseline` (alias `--simulation`) for the legacy robot/controller acceptance
and continue the mechanical link-frame integration as the next release gate.

## Operator command (after one-time native setup)

Run from the **flagship worktree** (not the dirty legacy checkout):

```bash
cd ~/weld-x-flagship
./start_weldx.sh
```

This defaults to **the latest WELD-X_final.glb visual preview**, not the old
prototype. It internally starts both Gazebo server and GUI, ROS controllers,
MoveIt, and localhost dashboard. For the old, controller-validated prototype
cell instead use `./start_weldx.sh --baseline`. The preview does not have
CAD collision or a controllable positioner, and the browser execution route
remains deliberately disabled. Stop the whole session using Ctrl+C.

Both launch scripts are tracked as executable. If your local filesystem
strips executable permissions, run `bash start_weldx.sh` instead.

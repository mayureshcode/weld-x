# WELD-X / live workcell console and one-command Ubuntu launcher

## Exact status, October 2026

The original uploaded welding-cell GLB has been integrated into an interactive browser **visual viewer** (orbit, zoom, isometric/front/top camera presets). The current GLB is a static, non-rigged scene with generic mesh node names; no mapping from those nodes to a calibrated ABB IRB120 joint hierarchy has been established.

A new **read-only ROS 2 Jazzy telemetry bridge** subscribes to `/joint_states`, `/tf`, and `/tf_static`, publishes an atomic local snapshot, and the dashboard polls it once a second. It shows the actual received joint names/angles and number of TF frame relationships. The bridge is intentionally separate from the trusted commissioning robotics adapter. **Received telemetry does not mean collision validation, synchronized planning scene, or safe robot execution**.

### What a single command can start now

From this branch, on Ubuntu 24.04:

```bash
# Prerequisites: Python >=3.12, Node 20+, npm, and original 34 MB GLB
# For ROS telemetry: source a ROS 2 Jazzy installation with sensor_msgs/tf2_msgs
# If needed, first install missing system dependencies with apt.
mkdir -p assets/source
cp /path/to/demo_robotic_welding_workcell.glb assets/source/
bash scripts/start_weldx.sh --visual
```

This one command:
1. Confirms the GLB SHA-256 identity.
2. Installs the pinned Three.js package locally on first run (internet required first time).
3. Sets up a Python virtual environment and WELD-X dependencies if needed.
4. Starts the read-only ROS topic monitor when ROS is available.
5. Starts the existing fail-closed WELD-X backend and dashboard on loopback port 8765.
6. Stops all child processes when terminated.

Open **http://127.0.0.1:8765**. No public listener and no external CDN. The 3D model is the genuine source asset; scale and any relationship to Gazebo are not yet calibrated.

### Simulation and robot startup — conditional

A **verified existing robot-and-world ROS launch** is not included in this branch. If you have independently installed and verified one on your Ubuntu system, it can be started by the same launcher:

```bash
export WELDX_ROS_LAUNCH_PACKAGE=your_verified_ros_package
export WELDX_ROS_LAUNCH_FILE=your_verified_launch_file.launch.py
bash scripts/start_weldx.sh --simulation
```

The launcher invokes `ros2 launch` and starts the viewer/telemetry backend together. Missing launch configuration is a **hard error**, not a pretend simulator. An arbitrary installed robot launch is not proof that this GLB model/fixture is aligned with the robot in Gazebo or MoveIt.

### Exact missing work for fully live robot articulation

To implement moving robot geometry consistently across Gazebo and the dashboard, obtain:
- A source-verified ABB IRB120 URDF/Xacro or SDF with actual link meshes, joint names, limits and transforms, controller config, and licensing.
- A surveyed GLB-to-REP-103 world transform and scene unit calibration; identify the decorative robot so the real model doesn't appear twice.
- Fixed fixture/workpiece frames and tested welding seam coordinates; simplified collision meshes for Gazebo/MoveIt.
- An actual Gazebo Harmonic world spawn, controller manager, joint-state feedback, and MoveIt 2 configuration.
- A trusted `weldx` robotics adapter implementing synchronise/validate/execute, including timeouts and feedback, before any placement can qualify.
- A browser scene rig driven by verified joint-state link transforms, **not rotations applied to arbitrary GLB meshes**.

Until then, the viewer is *static geometry + live telemetry*, not an articulated virtual commissioning twin.

### Verification

```bash
python -m unittest discover -v
python -m compileall -q weldx tests scripts/ros_telemetry.py
node --check dashboard/app.js
node --check dashboard/workcell.js
npm ls three
```

For actual visual verification, run `bash scripts/start_weldx.sh --visual` on Ubuntu and inspect the workcell, browser console, and connection status. Confirm changing physical/simulator joint readings in the telemetry panel **only** when ROS messages are truly arriving. Test removal of the ROS publisher: after ~3 s the backend must report disconnected.

This branch's logic has not been executed against a native Gazebo/ROS/MoveIt environment in the current authoring environment. A repository UI revision and code import are not equivalent to successful end-to-end industrial commissioning.

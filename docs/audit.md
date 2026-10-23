> Historical orchestration checkpoint document. For the current real robotics integration, measured results and remaining blockers, see [Phase 2](phase2/README.md).

# Milestone 0 — environment and baseline audit

## Authority and workspace

User authorized creation of a new project. GitHub authenticated account: `mayureshcode`. Created private `mayureshcode/weld-x`. Local authoritative workspace: `/data/weld-x` (real path `/vercel/sandbox/data/weld-x`), branch `main`. Initial `/data` contained no project and was not a Git repository. No pre-existing project files, branches or local changes were overwritten. Local parent `node_modules` was not modified.

## Observed host

- Amazon Linux 2023.12, x86_64; kernel `6.18.49`.
- 2 CPUs; 4.2 GiB RAM; no swap; approximately 23 GiB disk free at audit.
- Python 3.13.15, GCC 11.5.0, Node 24.22.1, Git 2.49.0, make.
- Installed Pydantic 2.14.1; Python stdlib unittest used.
- No command found: ros2, gazebo, gz, ign, colcon, cmake, MoveIt setup assistant.
- No `/opt/ros`; no relevant installed ROS/Gazebo/MoveIt RPMs found.
- No command found: Docker, Podman, nerdctl, Apptainer, Singularity, QEMU system emulator, Xvfb, nvidia-smi.
- Checked Docker/Podman sockets, `/dev/kvm`, `/dev/dri`, `/dev/nvidia0`: absent.
- rclpy, scipy, pytest, fastapi, uvicorn, pybullet, pinocchio absent. NumPy and Pydantic available.
- Chromium actually resolves to `/usr/local/bin/chromium`; initial distro-path assumption failed and was corrected.
- No local gh CLI, GH_TOKEN, GITHUB_TOKEN or GitHub credential files. GitHub access is via the connected MCP integration, verified by `get_me` and successful private repository creation.

## Existing implementation

None was available locally. Consequently no pre-existing ROS launch, mesh, URDF, controller, dashboard or test result could be reused. Baseline test count before creation: zero (not a passing robotics baseline).

## Reference robot source assessment

Inspected `ros-industrial/abb` at commit **45f4769d826cf3ac62a65495f2db67b78b0c81df**:

- [README](https://github.com/ros-industrial/abb/blob/45f4769d826cf3ac62a65495f2db67b78b0c81df/README.md): ROS 1 distribution branches and Catkin instructions; community-supported, not OEM support.
- [IRB 120 package.xml](https://github.com/ros-industrial/abb/blob/45f4769d826cf3ac62a65495f2db67b78b0c81df/abb_irb120_support/package.xml): version 1.5.0, Apache-2.0 declaration, Catkin build dependency and ROS 1 dependencies including rviz/roslaunch/industrial_robot_client. Its own description requires verification for the intended robot configuration.
- [IRB 120 Xacro macro](https://github.com/ros-industrial/abb/blob/45f4769d826cf3ac62a65495f2db67b78b0c81df/abb_irb120_support/urdf/irb120_3_58_macro.xacro): six revolute joints; separate visual/collision STL references; inertial definitions and fixed flange/tool0 frames.

Static source observations (radians, metres, radians/second):

| Joint | Origin xyz | Axis | Lower / upper | Velocity |
|---|---|---|---|---|
| joint_1 | 0,0,0 | 0,0,1 | -2.87979 / 2.87979 | 4.36332 |
| joint_2 | 0,0,0.29 | 0,1,0 | -1.91986 / 1.91986 | 4.36332 |
| joint_3 | 0,0,0.27 | 0,1,0 | -1.91986 / 1.22173 | 4.36332 |
| joint_4 | 0,0,0.07 | 1,0,0 | -2.79253 / 2.79253 | 5.58505 |
| joint_5 | 0.302,0,0 | 0,1,0 | -2.094395 / 2.094395 | 5.58505 |
| joint_6 | 0.072,0,0 | 1,0,0 | -6.98132 / 6.98132 | 7.33038 |

All effort limits in that macro are zero. They must not be copied into a dynamics/controller model without engineering review. tool0 includes a +90-degree pitch transform. Mesh references are not proof the collision meshes load or approximate the actual installation sufficiently.

**PROVISIONAL:** no Xacro expansion, mesh validation, FK/IK comparison, self-collision review, controller integration, spawn or trajectory execution ran. No alternate robot was substituted and no third-party model was vendored. The upstream package is a source candidate, not a Jazzy-ready installation.

## Compatibility decision

Do not install ROS 1 packages into this host or pretend that a dashboard animation is a simulator. No existing supported container route was found. Continue independently testable orchestration work. Native robotics acceptance requires a compatible accessible runtime; existing GitHub connectivity alone is not access to an Ubuntu simulation machine. No remote simulator/Actions robotics run was performed.

## Expected changed areas and verification

New project only: `weldx/`, `tests/`, `examples/`, `dashboard/`, `docs/`, `evidence/`, project metadata and core CI. Verify with unittest, compileall, JS syntax checks and real local HTTP/browser tests. Simulation acceptance remains gated on model verification, actual joint feedback, collision-aware complete-job execution and held-out robustness records.

## Observed publication permission boundary

Repository creation and Contents API writes succeeded. A Git data batch including `.github/workflows/core.yml` returned HTTP 403 `Resource not accessible by personal access token`. An otherwise identical batch excluding the workflow succeeded. Therefore source/evidence publication is verified, but workflow configuration publication is blocked with this connection. No workflow write workaround was attempted; the definition is local/archive only. No remote CI execution is claimed.

# Phase 3 reproduction and delivery

Use the existing `engineering/robotics-integration` checkout; do not merge into main or edit protected jobs to obtain a pass. [Phase 2 installation](../phase2/runbook.md) documents pinned ABB assets and the project-local Ubuntu 24.04 bootstrap. Native target: Ubuntu 24.04, ROS 2 Jazzy, Gazebo Harmonic, MoveIt 2 and gz_ros2_control. The verified Amazon Linux host uses a privileged project-local Ubuntu chroot, not a full VM or security boundary. No physical driver is supported.

## Launch

From repository root, separate terminals:

```bash
bash tools/in-ubuntu /workspace/tools/ros-env ros2 launch weldx_bringup cell.launch.py
bash tools/in-ubuntu /workspace/tools/ros-env /opt/weldx-venv/bin/python -m weldx.server \
  --robotics --config benchmarks/recovery_v1/configuration.json \
  --audit .runtime/phase3-dashboard.jsonl --port 8766
```

Open `http://127.0.0.1:8766` on that machine. This is not a deployed public service. Use a fresh audit filename for an independent run; the journal protects a single writer. The actual Gazebo GUI/software-rendered visual inspection command remains:

```bash
bash tools/in-ubuntu /workspace/tools/ros-env bash /workspace/tools/gazebo-visual.sh
```

Phase 2 includes actual GUI screenshots; Phase 3 rechecks robot feedback and the live browser viewer, not a new native-GUI acceptance claim. Do not run competing scene writers.

## Tests and experiments

Run sequentially with the simulator active and dashboard stopped for all scene/motion tests:

```bash
bash tools/in-ubuntu /opt/weldx-venv/bin/python -m unittest discover -s tests -t . -v
bash tools/in-ubuntu /workspace/tools/ros-env /opt/weldx-venv/bin/python -m unittest discover -s tests_robotics -t . -v
bash tools/in-ubuntu /workspace/tools/ros-env /opt/weldx-venv/bin/python -m robotics.nominal_suite --output-dir evidence/phase3
bash tools/in-ubuntu /workspace/tools/ros-env /opt/weldx-venv/bin/python -m robotics.benchmark --output-dir evidence/phase3/recovery-v1
bash tools/in-ubuntu /workspace/tools/ros-env /opt/weldx-venv/bin/python -m robotics.benchmark --config examples/commissioning_two_seam.json --output-dir evidence/phase3/strict
bash tools/in-ubuntu /workspace/tools/ros-env /opt/weldx-venv/bin/python -m robotics.policy_benchmark
python3 tools/analyze-policy-results.py
```

The policy runner freezes all seeds/scenarios before evaluation, verifies protected input hashes, compares selections on one shared pool per job/seed, and labels direct nominal execution as a **non-authorizing integration harness**. It is not a successful approval workflow. Per-policy wall-time and human manual performance are not measured. Use a new evidence directory/checkpoint for independent experiments instead of overwriting historical results; the current CLIs' fixed experiment paths intentionally reproduce their named run.

After those tests finish, start a fresh dashboard as above. The local browser acceptance test needs host Python Playwright and `/usr/local/bin/chromium` (installed in the verified environment):

```bash
python3 tools/browser-phase3-test.py
```

It runs real detection/search, selects actual candidate/scenario evidence, checks planned-path links, mobile layout, approval/application/execution denial and visible backend disconnection. It does **not** approve a nonqualifying candidate. Failed UI attempts, if any, must remain preserved.

## Demonstration expectations

1. Detect: nominal job can plan, but mandatory boundary failures reject robustness.
2. Search: bounded tested placements populate the real map. Inspect original/selected placement, source failures, actual planned TCP paths and explicitly predicted ×50 residual.
3. Sensitivity: counts distinguish screen failures, unknown/unrun tests and observed jobs. MC empirical rate is unavailable when unexecuted, not 0%.
4. No solution: no qualifying candidate means no recommendation, approval or execution authorization. Direct API attempts must also be denied.
5. Positive nominal motion: the separate five-job harness executes actual trajectories through ros2_control and records feedback. This does not bypass commissioning approval or demonstrate robustness.
6. Positive uncertainty plumbing: the +0.1 mm fixture-X integration fixture executes all seven segments and restores the scene. One hand-picked integration fixture is not the prescribed MC experiment.

Recovery-v1 is expected to fail under its unchanged assumptions; base relocation cannot correct arbitrary independent fixture error. Do not silently change ±0.5 mm assumptions, 1 mm tolerance, yaw/calibration envelopes, 99% target or budgets. A separately versioned measurement experiment requires explicit authorization and justified declared residuals. Exact engineer approval is still required if a future candidate qualifies.

## Fault recovery / shutdown

Stop only launch/dashboard processes owned by this run using Ctrl+C or their recorded PIDs. Do not use killall. Source/model/controller changes invalidate fingerprints: restart the backend and fully revalidate. A failed application consumes approval, invalidates authorization and records unconfirmed state; inspect live readback and obtain fresh approval, never reuse an old token. If restoration or feedback is unknown, execution stays blocked. Follow the existing bounded budgets; do not omit restoration time to claim a speedup.

Full JSON/JSONL is in the delivery archive. Remote `*.gz.b64` copies decode with Python `gzip.decompress(base64.b64decode(path.read_bytes()))`; `evidence/phase3/storage-manifest.json` records exact SHA256 and source paths. No remote CI or main merge is asserted.

The release launch disables MoveIt's unused internal execution route; the intended direct, exact-gated ros2_control action remains the sole WELD-X execution route. Verify with `ros2 param get /move_group allow_trajectory_execution` (expected false). The original and repeated MoveIt shutdown faults and post-attempt regression logs remain in Phase 3 evidence. The execution-route parameter is not a demonstrated teardown fix; directory names `post-teardown-fix` record the attempted hypothesis, not a passing shutdown.

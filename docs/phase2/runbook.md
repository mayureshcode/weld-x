# Reproduce the verified virtual tests

## Requirements and isolation

Verified host: x86-64 Amazon Linux 2023, two CPUs, approximately 4.2 GiB RAM, no GPU/swap. The target robotics userspace is Ubuntu 24.04.3 under `.runtime/ubuntu-rootfs`, about 5.1 GiB after installation. This is an opt-in privileged chroot/mount-namespace fallback, **not a security boundary or full VM**. Host networking/PIDs are shared; only trusted project commands belong here. Host apt configuration is untouched. No physical robot driver is installed or supported. Use an otherwise unused ROS domain; `tools/ros-env` sets domain 47, LOCALHOST discovery and Gazebo partition `weldx_virtual`.

First checkout (the GitHub file API may not preserve executable bits):

```bash
chmod +x tools/in-ubuntu tools/ros-env tools/*.sh
python3 tools/fetch-robot-assets.py
bash tools/bootstrap-rootfs.sh
bash tools/in-ubuntu bash /workspace/tools/bootstrap-robotics.sh
bash tools/in-ubuntu bash -c 'source /opt/ros/jazzy/setup.bash; cd /workspace/ros_ws; colcon build --base-paths src --executor sequential'
```

The Ubuntu archive SHA256 and all original ABB STL SHA256 values are pinned and checked. Asset downloads preserve modified files rather than overwriting them. Bootstrap refuses to run without the project-rootfs marker. ROS apt metadata is signature-verified using the official key; this host's ROS HTTPS endpoint failed hostname verification, so the official signed HTTP apt transport was used, without disabling signature checks. Apt repositories can change; the actual full package inventory is recorded in evidence, not a promise of bit-for-bit future installs.

## Run real robotics and dashboard

Terminal 1:
```bash
bash tools/in-ubuntu /workspace/tools/ros-env ros2 launch weldx_bringup cell.launch.py
```

Terminal 2:
```bash
bash tools/in-ubuntu /workspace/tools/ros-env /opt/weldx-venv/bin/python -m weldx.server \
  --robotics --config benchmarks/recovery_v1/configuration.json \
  --audit .runtime/recovery-dashboard.jsonl --port 8766
```

Open `http://127.0.0.1:8766`. This address is local to the running machine; no public deployment is implied. Run detection, inspect source diagnostics, run bounded search and inspect actual map points. For the declared benchmark, expect **no robust recommendation**, not approval/execute availability. The execute control and backend remain gated. The default server without `--robotics` remains unavailable/fail-closed and does not substitute a mock.

For an actual Gazebo GUI using software rendering:
```bash
bash tools/in-ubuntu /workspace/tools/ros-env bash /workspace/tools/gazebo-visual.sh
```
The script owns an Xvfb display `:77` and starts Gazebo's real GUI. It was visually inspected with llvmpipe. Xvfb is not a shared interactive desktop; screenshot evidence is in the delivery archive. On a native engineering desktop, launch the Gazebo GUI against the same server/partition using its desktop display. Do not assume the Notion browser can show a native GUI.

## Tests (run one motion/scene-writing test at a time)

```bash
bash tools/in-ubuntu /opt/weldx-venv/bin/python -m unittest discover -s tests -t . -v
bash tools/in-ubuntu /workspace/tools/ros-env /opt/weldx-venv/bin/python -m unittest discover -s tests_robotics -t . -v
bash tools/in-ubuntu /workspace/tools/ros-env /opt/weldx-venv/bin/python -m robotics.nominal --execute
bash tools/in-ubuntu /workspace/tools/ros-env /opt/weldx-venv/bin/python -m robotics.nominal_suite
bash tools/in-ubuntu /workspace/tools/ros-env /opt/weldx-venv/bin/python -m robotics.diagnostic_tests
bash tools/in-ubuntu /workspace/tools/ros-env /opt/weldx-venv/bin/python -m robotics.benchmark
```

The first test discovery command must include `-t .`; an earlier invocation without it failed relative imports and is preserved in the logs. Nominal execution CLIs are explicitly labeled integration test harnesses, not the commissioning authorization endpoint. The browser test additionally needs host Python Playwright/Chromium; it was run in this environment, not installed by the robotics bootstrap.

`tools/browser-workflow-test.py` tests connected detection/search/map/source selection/mobile layout and denial on unknown/failed evidence; it requires the dashboard on port 8766 and no competing motion/scene test. It deliberately aborts API requests at the end to verify the disconnected UI.

## Shutdown, restart and recovery

Use Ctrl+C on the process you launched. Launch owns its ROS/Gazebo child processes; the GUI script owns its Xvfb. Do not use killall, remove unrelated workspaces or kill unrelated ROS nodes. A single journal has a writer lock, but separate diagnostic processes must still be serialized; concurrent scene writers are not supported.

A source/model/controller dependency change invalidates adapter readiness and requires backend restart plus fresh revalidation. A restart never restores prior execution authorization. Physical installation changes require engineer approval of an exact recommendation; approval is consumed on application and cannot authorize a different version. The final revalidation path must confirm actual Gazebo and MoveIt state, controller health and exact trajectory binding. No robust candidate exists for the present benchmarks; do not manufacture approval to bypass that result.

Direct Gazebo `set_pose` acknowledgement did **not** relocate the world-anchored robot. The supported virtual procedure is remove/respawn with the exact fixed-anchor origin, reinitialize controllers, and verify live base-link pose twice. The Python Gazebo transport synchronous request beside pose subscriptions caused real timeouts; service requests now run in bounded separate `gz service` processes. Failed attempts and successful restoration evidence are retained.

## Evidence locations

The delivery archive includes source assets, screenshots, full JSON/JSONL records and failed attempts. GitHub includes compact reports plus lossless `*.gz.b64` text copies of large authoritative records. Decode any such file using `gzip.decompress(base64.b64decode(path.read_bytes()))` in Python; the adjacent manifest supplies the original SHA256. `benchmarks/recovery_v1/evidence-storage.json` contains the exact full-validation decode command. The live status endpoint is only a presentation summary; explicit evidence/audit inspection retrieves the original complete record.

# WELD-X Studio — 3D-first dashboard

## Scope

This redesign transforms the WELD-X dashboard into an industrial digital-twin
workstation with a large 3D viewport, robot joint inspector, camera presets,
planning workflow, optimization plots, diagnostics and audit records. It
preserves all existing command/API IDs and the fail-closed commissioning gates.

The generated image in the overview is **decorative AI concept art**. It
is bundled locally as `dashboard/assets/weldx-hero.webp` and labeled as such.
It is not a Gazebo screenshot, calibration or physical evidence.

## Two explicitly different 3D modes

### Default `./start_weldx.sh`

`WELDX_VIEW_MODE=glb-preview`. The native launcher exports the local
`assets_vnext/source/WELD-X_final.glb` to
`assets_vnext/exports/weldx_shell_preview.glb` and loads it with the
vendored Three.js r160 `GLTFLoader` from
`/assets/workcell-preview.glb`.

This includes the **customized robot and positioner visually**, not two
robots; it is a **static snapshot** of the supplied GLB. Camera orbit, zoom
and presets operate on the actual visual asset. It does not imply ROS
articulation, correct link frames, collision fidelity, or executed plans.
The backend is deliberately started without `--robotics`; execution remains
locked. The inspector shows em dashes instead of fabricated joint angles.

### `./start_weldx.sh --baseline`

`WELDX_VIEW_MODE=live-urdf`. This mode uses the actual runtime-generated
ABB-derived URDF and observed ROS joint states and cell poses. The dashboard
can update the *provisional* 3D URDF robot from `/api/telemetry` and display
the measured joint values when feedback is fresh. When stale or disconnected,
the model freezes and the indicator switches to **stale**, not a false live
status. Cached MoveIt TCP paths are labeled as planned evidence only.

**The custom GLB robot is NOT yet linked to the URDF six-link chain.**
This requires transforming its mesh assemblies into correctly aligned link
frames and validating origins, axes, joint limits, collisions and feedback
in Gazebo/MoveIt. No camera streaming, physical welding, or real robot motion
from the illustrated model is claimed in this release.

## How to run in your existing worktree

Stop the existing WELD-X launcher in its terminal with Ctrl+C.

```bash
cd ~/weld-x-flagship
git pull --ff-only
./start_weldx.sh
```

Open `http://127.0.0.1:8765`. The new 3D viewport may initially load
a large exported GLB, so wait for the scene status to say
`SOURCE GLB PREVIEW`. Do not interpret an empty viewport as an initialized
model. Click **Top**, **Side**, **Isometric**, and **Focus robot**; use
**Expand view** for an immersive workspace. The browser receives only
localhost resources; no CDN, analytics or cloud upload is required.

No ROS rebuild is necessary for these dashboard/backend static changes.
If you want to confirm joint movement in the previous validated world,
stop the first session, then:

```bash
./start_weldx.sh --baseline
```

The 3D model changes to the live provisional URDF robot; the six measured
joint values update only while `/api/telemetry` reports fresh ROS feedback.
Run authorized simulation-only acceptance tests separately—this dashboard
does not command motion on its own.

## Test and evidence collection

Offline core checks run in GitHub Actions. For a browser test against the
**currently running** local WELD-X process, install Playwright separately
if needed (`python3 -m pip install playwright` inside an appropriate test
environment, and `python3 -m playwright install chromium`), then:

```bash
python3 tools/browser-studio-smoke.py
```

This read-only test exercises the actual GLB load, camera presets,
expand/restore, static/ROS labeling, command-lock state, and mobile overflow.
It writes screenshots and a JSON report under
`.runtime/studio-smoke/`. **This test has not yet run on the target laptop.**

## Presentation and safety principles

- The actual GLB occupies the main viewport, not a screenshot.
- AI art is used only in the decorative overview.
- Preview positions are not advertised as measured Gazebo states.
- Planned TCP paths are not animated robot execution.
- Controller health, approval, motion and e-stop semantics remain owned by
  the existing backend. A browser view can never bypass an approval gate.
- The dashboard is a development demonstrator, not certified industrial HMI.
- Independently calibrated robot and positioner articulation is the next gate.

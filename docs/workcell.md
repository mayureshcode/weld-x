# WELD-X workcell visual enhancement

## Scope and evidence

This feature branch contains a **non-destructive Blender 4.x enhancement script**, not a validated welding digital twin. The script imports an existing GLB into a clean Blender scene and adds a WELD-X exhibition sign and three overview/inspection cameras. It **only** adds base-position or weld annotations when explicit anchor coordinates are supplied. No existing robot, fixture, or imported geometry transforms are changed.

### Input asset

User-provided file: `demo_robotic_welding_workcell.glb` (about 34 MB). This binary GLB is **not included in this GitHub branch**. Place it in `assets/source/` locally (avoid claiming it was uploaded). Inspection with `trimesh` found 181 mesh geometries and 240 scene graph nodes, approximate scene bounds `[-1, -0.025, -2.2]` to `[5.6, 2.333, 2.3]`. These values are scene units, **not verified meters**, and generic node names do not prove which mesh represents the robot, fixture, or floor.

## Running on a machine with Blender

```bash
mkdir -p assets/source outputs
# Copy your original demo_robotic_welding_workcell.glb to assets/source/
blender -b --python tools/enhance_workcell.py -- \
  --input assets/source/demo_robotic_welding_workcell.glb \
  --output outputs/WELDX_Industrial_Cell_V1.blend \
  --render-dir outputs/previews
```

Outputs: `WELDX_Industrial_Cell_V1.blend`, a JSON report beside it, and optionally three PNG camera renders. Preview rendering requires a working Blender graphics/render environment; running it in background mode may render via CPU.

## Optional survey anchors

**Do not use approximate anchors to claim technical feasibility.** After opening the source GLB, first measure and verify the asset-to-ROS coordinate-frame mapping, robot base and fixture positions, workpiece points, collision dimensions, mounting surfaces, and correct scene units. You may then create a local JSON file:

```json
{
  "bases": {
    "original": [0.0, 0.0, 0.0],
    "candidate_01": [0.4, 0.0, 0.0],
    "recommended": [0.2, 0.1, 0.0]
  },
  "seams": {
    "SEAM_01": {
      "approach": [0.0, 0.0, 0.0],
      "start": [0.0, 0.0, 0.0],
      "end": [0.0, 0.0, 0.0],
      "retreat": [0.0, 0.0, 0.0]
    }
  }
}
```

**These are schema examples only, not coordinates from the GLB.** Use `--anchors /path/to/verified_anchors.json` only after replacing every sample number with surveyed scene-space coordinates. The script stores markers separately under `WELDX_BASE_PLACEMENT` and `WELDX_WELD_ANNOTATIONS`; hide or omit those collections in simulator exports.

## What must be verified before industry claims

1. Verify GLB axes, units, and fixed world-to-cell/robot-base transforms with a measured reference.
2. Confirm the robot model corresponds to the simulation URDF (currently provisional ABB IRB120); do not simulate an additional decorative arm.
3. Generate simplified collision assets and a planning scene for the **real workcell topology**, not visual mesh collision assumptions.
4. Define actual fixture/workpiece seam coordinates and TCP orientations in an agreed coordinate frame.
5. Connect the existing failure-aware orchestration to real IK, MoveIt 2 collision and trajectory validation, and Gazebo execution feedback.
6. Perform multi-seam complete-job robust placement testing; reject unsolved or unverified candidates.
7. Implement simulated functional interlocks and verification evidence. Do not equate this with certified industrial safety.

## Safe re-runs

The script begins with an empty working Blender scene and imports the source GLB once. It does **not** edit or overwrite the input GLB. It refuses to write to the same path as the input. Run a new process to recreate the enhanced scene deterministically. The sign is an exhibition overlay, not a surveyed physical cabinet installation.

## Current limitations

- Blender is not installed in the execution environment used to author this change; **no .blend output or preview render has been executed/verified here**.
- The source binary is not committed to GitHub by this change.
- No validated robot placement, seam geometry, functional E-stop, interlocked gate, live HMI, or Gazebo integration is implemented in this script.
- The main WELD-X repository's prior simulation/testing claims must be assessed separately.

# WELD-X robotics integration checkpoint

**Status: partial virtual commissioning implementation, not a completed recovery demonstration.**
The original `main` checkpoint `8344af53d1d7451f878081f389ccc598c7db6558` is preserved. Substantial work lives on `engineering/robotics-integration`. Local Git is a source mirror of the MCP-published checkpoint, not an authenticated clone with identical commit ancestry. Remote publication uses the authorized GitHub connection.

## What was actually verified

- Project-local Ubuntu 24.04.3 userspace on the Amazon Linux host; ROS 2 Jazzy, Gazebo Harmonic 8.15.0, MoveIt core 2.12.4, gz_ros2_control 1.2.20 and ros_gz_sim 1.0.24.
- ABB IRB120 source kinematics from immutable upstream commit `45f4769d826cf3ac62a65495f2db67b78b0c81df`; six axes, source joint limits, real visual/collision meshes, KDL, OMPL, FCL, joint feedback and trajectory controller.
- Actual Gazebo motion, independent FK cross-check, seven ordered segments of a two-seam job, and five separately defined nominal jobs executed successfully. These are nominal integration tests, **not robustness-qualified commissioning approvals**.
- A complete small-fixture-error trial executed all seven segments through the actual uncertainty pipeline. This single integration fixture is not a Monte Carlo reliability estimate.
- Real environmental/self-collision rejection, unreachable IK rejection, reversible exact base relocation with controller reinitialization and live Gazebo pose readback, software cancellation and observed hold.
- Existing orchestration integrity tests and new boundary-evidence tests pass. See the exact command/result ledger.
- A connected web viewer uses the actual runtime URDF, licensed source meshes and observed Gazebo joint feedback. It does not animate a separate success sequence.

## Proposed recovery benchmark: rejected, not accepted

The user's strict job remains byte-for-byte unchanged. Its fixture error of ±2 mm cannot be corrected by relocating the robot to meet a 1 mm TCP requirement under this open-loop model.

`benchmarks/recovery_v1/configuration.json` is separate and versioned. The user authorized proposed **simulation assumptions** of ±0.5 mm per planar base axis and ±0.5 mm per fixture translation axis; these are **not measured physical specifications**. The Euclidean TCP tolerance remains 1 mm. Other yaw and calibration mismatch terms were retained, not silently reduced.

Predeclared design: 60 mandatory boundary scenarios and 100 seeded Monte Carlo scenarios per source (400 MC total) per phase; separate search/held-out seeds, 99% empirical MC target. All 60 boundary scenarios were screened on actual model-based nominal trajectories. Twenty necessary-condition violations rejected the benchmark before Monte Carlo acceptance:

| Source | Boundary scenarios screened | Confirmed violations | Complete-job successes claimed |
|---|---:|---:|---:|
| Base installation | 8 | 4 | 0 |
| Fixture/workpiece | 10 | 2 | 0 |
| TCP calibration mismatch | 10 | 2 | 0 |
| Combined | 32 | 12 | 0 |

Screen survivors are **unknown**, not passed boundary jobs. No benchmark MC jobs were executed after mandatory boundary rejection, so no 99% success rate is reported. This early rejection does not claim full perturbed execution coverage.

Reasons include retained ±0.01 rad base yaw (a recorded failure was 3.635 mm), retained per-axis ±1 mm TCP calibration mismatch (the corner is 1.732 mm), fixture translation/yaw combinations (1.120 mm in a recorded case), and opposed base/fixture translation extremes (1.500 mm). Even with yaw/calibration errors removed, independent ±0.5 mm component bounds do not guarantee a 1 mm Euclidean relative-position bound in all combinations. No real sensor, registration or compensation mechanism exists in this implementation. Simulator ground truth initializes experiments and collision scenes; it is not described as a measurement system. The weld trajectories remain fixed under perturbation.

A 1 picometre/radian arithmetic comparison guard avoids floating-point false rejection at an exactly equal boundary; it does not change input tolerances. The first roundoff-affected report and the corrected rerun are both retained.

## Acceptance still missing

No candidate for these declared jobs has passed all mandatory robustness gates. Therefore no genuine corrective recommendation was approved, no engineer approval was fabricated, and no successful **Detect → Search → Map → Recommend → Approve → Apply → Revalidate → Execute** recovery is claimed. Approval/version integrity and bounded recovery have isolated tests; a successful real-robotics recovery remains unverified. The supported behavior is rejection/stop, not silent tolerance relaxation.

No physical welding, ABB dynamics calibration, production reliability, global search optimality, continuous collision guarantee or industrial safety certification is claimed. CI publication is not verified; the available GitHub permission previously rejected workflow-file writes. Main is not merged or overwritten.

See [engineering report](final-report.md), [runbook](runbook.md), [architecture and contracts](architecture.md), [acceptance ledger](acceptance.md), and [risk/decision log](risks.md).

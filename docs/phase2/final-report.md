# WELD-X — verified integration delivery, not full commissioning acceptance

## Executive outcome

The repository now contains a real ROS 2 Jazzy / Gazebo Harmonic / MoveIt implementation, actual ABB-model simulation and multi-seam execution, a connected observed-joint 3D dashboard, bounded placement search, uncertainty failure evidence, approval/version gates and reproducible test tooling. **The full mission is not complete:** neither declared benchmark has a robustness-qualified placement, and a successful approved recovery workflow is not demonstrated.

The strict job is preserved unchanged. The separately versioned recovery v1 benchmark is rejected, not tuned to pass. Its proposed ±0.5 mm base-X/Y and fixture-X/Y/Z assumptions are not validated physical specifications. The Euclidean TCP requirement remains 1.0 mm; retained yaw and calibration terms were not silently changed. There is no real measurement or compensation mechanism.

## Repository and publication

- Repository: https://github.com/mayureshcode/weld-x
- Working branch: `engineering/robotics-integration`.
- Original remote main checkpoint: `8344af53d1d7451f878081f389ccc598c7db6558`; no main merge or force push.
- GitHub writes use the authorized connection. Successful remote commit receipts are in `evidence/phase2/publication.json`; no CI success is claimed.
- Local Git is a preserved source mirror with different ancestry, not an authenticated clone of the remote history.

## Architecture and implementation

Two ament packages supply the robot, torch, fixture/workpiece, worlds, ros2_control configuration, SRDF, KDL and MoveIt bringup. Python robotics modules use actual planning/scene services and the trajectory-controller action. The existing immutable configuration, exact identity, hard-gated validation, seeded experiments, bounded search, approval/application/revalidation and hash-linked audit core is retained.

Base placement is synchronized by exact fixed-anchor respawn, controller reinitialization and repeated live Gazebo pose readback, plus matching MoveIt scene transforms and FK verification. A service acknowledgement alone was experimentally insufficient. Dependency changes invalidate runtime readiness, and stale or incomplete evidence cannot authorize execution. Long-running work is observable/cancellable; no arbitrary shell API exists.

The web scene renders licensed source meshes and actual observed joint/cell poses. Its candidate map, source records, comparison, diagnostics and audit use backend evidence. Incomplete candidates remain distinct from failures. Approval is not fabricated when no candidate qualifies. Source/asset licensing and immutable hashes are retained.

See [architecture](architecture.md), [acceptance/requirements ledger](acceptance.md), [decisions/risks](risks.md) and [reproduction runbook](runbook.md).

## Measured verification

- **55/55 core tests passed**: `core-regression-final.log`. Labeled doubles test orchestration; they are not robotics evidence.
- **18/18 real robotics integration tests passed**: `robotics-regression-final.log`, with clean final ROS callback teardown.
- **Five of five nominal jobs executed** in actual Gazebo: straight butt, parallel seams, L-corner, raised short and angled torch. Final wall times and complete observed segment records are in `nominal-suite.json`; nominal tests do not qualify robustness or engineer approval.
- The primary two-seam job executed all seven ordered logical segments. Recorded maximum in-motion TCP tracking error after the controller fix was 0.1915 mm. Returned weld speed was independently limited to approximately 9.524 mm/s under the declared 10 mm/s cap.
- An actual full seven-segment +0.1 mm fixture-X trial passed. It is one integration fixture, **not a Monte Carlo reliability estimate**.
- Actual FCL self-collision, infeasible IK, exact base relocation/restoration, controller cancellation and feedback were tested. Cancellation evidence reports action status 5 and observed sampled holding, not certified safety.
- `dashboard-workflow-tests.json` is the authoritative connected-browser result, covering actual detection/search, evidence-linked selection, mobile layout, complete-record inspection, direct unauthorized-execution denial and disconnection fault behavior. The final run passed all ten listed checks with no JavaScript errors; its 16-candidate search stopped on the declared candidate budget after 117.983 s, with no qualifying recommendation. Failed prior attempts are retained rather than presented as passes. Status polling measured 678,059 bytes / 0.234 s in one final request, versus the earlier observed 22,140,267-byte response; this is a diagnostic measurement, not a controlled throughput benchmark.

Exact commands are in the runbook and acceptance ledger. Full source SHA256 values are in `source-sha256.json`; experiment seeds/scenarios were frozen before evaluation.

## Recovery benchmark result and causal limits

Predeclared recovery v1 design: 60 mandatory boundaries; 100 Monte Carlo trials per source, four sources, separate search/held-out seeds `20261023` / `20261123`; empirical target 99%. **Twenty of sixty boundary screens violate constraints**, so the benchmark is rejected. Surviving screens are unknown, not successful complete jobs. **Zero benchmark MC jobs ran after hard boundary rejection; no MC success rate is available.**

Confirmed causes include retained base yaw, retained per-axis calibration mismatch, combined fixture/yaw error, and opposed independent base/fixture translation corners. A permitted combined translation alone produces a 1.5 mm Euclidean relative displacement, exceeding 1 mm. Base relocation cannot compensate an unmeasured independent fixture error. This is evidence for engineering review, not proof of statistical causal attribution or global search optimality.

The full frozen evidence JSON is bundled in the delivery archive; a lossless gzip/base64 form and decode instruction are also published to GitHub to fit the authorized text-file interface. The strict job SHA256 is `341cec92b298f74383556a9512b7d2308cb372a587a04231f8612adef449f280`.

## Reproduction and resource limits

Use the commands in [runbook](runbook.md): pinned asset fetch → project-local Ubuntu bootstrap → dependency installation → colcon build → `cell.launch.py` → dashboard with `--robotics`. Dashboard address is localhost:8766 on the running machine, not a public deployment. Fresh GitHub checkouts must fetch the SHA256-verified STL assets; the archive bundles them.

Actual userspace versions: Ubuntu 24.04.3, Gazebo Sim 8.15.0, MoveIt core 2.12.4, gz_ros2_control 1.2.20, ros_gz_sim 1.0.24. Full package inventories are recorded. The host has two CPUs, about 4.2 GiB RAM and no GPU/swap; rootfs uses about 5.1 GiB. Software GUI rendering was visually checked, with observed RTF around 0.35–0.45 in that setting. Headless testing requested RTF 3, not a guaranteed real-time rate. CPU and rendering contention affect runtimes; these are not controlled cross-method performance benchmarks.

The privileged private-mount chroot shares host networking/PIDs and is not a security boundary. Serialize scene writers. Stop only owned launch processes; no killall cleanup is required.

## Modified-file summary

`robotics/`, `ros_ws/src/`, `tools/`, `tests_robotics/`, `benchmarks/`, `third_party/` and `docs/phase2/` provide new integration components. `weldx/engine.py`, `robustness.py`, `server.py`, dashboard source, API/boundary tests and documentation pointers were updated. Source models, manifests and test logs accompany this report. Original examples and historical documents are preserved; runtime/build outputs are ignored.

## Remaining acceptance and precise recovery path

1. **Blocking engineering requirement:** obtain evidence-supported uncertainty bounds or design/validate an explicit measurement and compensation mechanism. Do not simply reduce terms after seeing the results. If authorized specifications change, preregister recovery v2 and preserve strict/v1 failures.
2. Run every mandatory boundary as a complete observed job, then the frozen search/held-out Monte Carlo design with adequate compute. Report sample counts/confidence limits; do not equate simulated success with production probability.
3. Only a qualifying candidate may trigger an actual engineer approval. Apply its exact version, synchronize both representations, revalidate held-out complete-job evidence, then execute and retain the audit. That successful approved recovery is currently **not verified**.
4. Complete alternative-method/manual benchmark comparisons; no significance or ranking performance advantage is claimed yet.
5. Complete planned-trajectory and uncertainty-source scene overlays and richer sensitivity comparisons. Current live 3D/seam/candidate views are not those missing features.
6. Validate physical dynamics/collision exclusions if seeking stronger model fidelity; add conditioning and distance instrumentation if required. Current collision checks are discrete and ABB physical fidelity remains provisional.
7. Arrange workflow-write permission for CI, run it, and review/merge the working branch only after engineering acceptance. Neither CI nor a main merge has been performed.

No physical robot, real welding, industrial certification, continuous collision proof or globally optimal placement is claimed.

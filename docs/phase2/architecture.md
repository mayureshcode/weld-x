# Robotics integration architecture and contracts

The existing immutable configuration, SHA256 identity, Journal, Engine, Plan/Check/Execution and HTTP security boundaries are retained. Core-only Python remains independently testable; importing the default server does not import ROS.

| Boundary | Implementation / actual interface |
|---|---|
| Versioned configuration | `weldx/model.py`; SI metres/radians/seconds; world REP-103, fixed-XYZ RPY; exact job segment IDs |
| Robot / cell | `weldx_description`, `weldx_bringup`; pinned six-axis ABB source, separate visual and collision meshes, actual torch/TCP, fixed fixture/workpiece/floor |
| Model-based planning | `robotics/cell.py`; MoveIt `GetPositionIK`, `GetPositionFK`, `GetMotionPlan`, `GetCartesianPath`; KDL, OMPL, FCL |
| Scene synchronization | `ApplyPlanningScene`, Gazebo entity commands and live `Pose_V`; fixed-anchor respawn, exact base/fixture/workpiece readback and controller reinitialization |
| Nominal validation | Complete ordered segments; full Cartesian fractions, independent TCP residuals/speed, source joint bounds, reported velocity/acceleration, discrete FCL states with world padding |
| Robustness | Same nominal joint commands; `perturbation.py`, `preflight.py`, `uncertain_execution.py`; necessary violations reject, potential successes require actual complete perturbed execution within budget |
| Search | Bounded lazy space-spreading grid, then local refinement; hard nominal/robust gates before deterministic ranking; no global optimality claim |
| Approval/recovery | Existing exact candidate/origin/job/version approval; consumed application, exact runtime revalidation; bounded attempt/time/recovery counters and audit |
| Execution | `/joint_trajectory_controller/follow_joint_trajectory`; actual feedback, in-motion and endpoint TCP/joint tracking, complete ordered segment observations |
| Web integration | Same-origin loopback API; background task and cooperative cancellation; no arbitrary shell input; allowlisted module/STL assets and read-only runtime model/telemetry |
| Web scene | Locally vendored Three.js; runtime URDF transforms and observed joints, actual cell poses; declared seam overlays and explicitly labeled candidate mounting previews |
| Evidence | JSON/JSONL and logs; hash-linked journal, exact config/scenario seeds/versions; raw failed attempts preserved, not tamper-proof certification |

## Frames and uncertainties

Base installation translations are world X/Y; base yaw is world Z and mounting height is fixed. Fixture error is a rigid assembly transform about the nominal fixture origin. The workpiece's attachment transform to the fixture is preserved, not independently guessed. Calibration mismatch is a virtual actual-TCP translation/yaw in the nominal TCP local frame. It is not a link-length, mass, thermal deformation or compliance model.

Tests verify independent FK vs MoveIt, world-axis translation propagation, equal-error cancellation, opposed independent errors, local TCP calibration offsets and workpiece motion under fixture rotation. There is **no real measurement/registration/compensation mechanism**. Experiment ground truth configures perturbed geometry and collision checking; nominal welding commands are not replanned with perfect knowledge of error. A separate safety-checked reset motion can return the simulator to the stored trajectory's start before a trial; it is not a weld-path compensation algorithm.

## Controller and timing defects found and fixed

MoveIt's returned Cartesian timing did not honor the requested speed in the observed installation. Uniform conservative retiming independently limits TCP chord/directional-derivative speeds while reducing joint velocity/acceleration. The requested weld speed is treated as an upper bound, not a demonstrated exact feedrate guarantee. Returned weld TCP speed in the main two-seam test was approximately 9.524 mm/s for the declared 10 mm/s cap.

Default simulated position-drive gain 0.1 at 100 Hz produced 6.704 mm of in-motion TCP lag despite successful endpoints/action results. The ideal **simulation-only** drive now uses gain 1.0 and a 500 Hz controller update, with explicit tighter goal convergence. The job's 1 mm / 0.02 rad tolerances were not relaxed. Recorded main-job maximum in-motion TCP error after the fix was 0.192 mm. ABB actuator dynamics, torque limits and tuning are not validated; the effort limit and inertias are simulation assumptions, not manufacturer specifications.

## Limits of validation

Collision checking is discrete; source self-collision exclusions are retained and an actual self-collision fixture was detected. Link padding enforces the declared world-collision buffer in MoveIt; no continuous collision/clearance proof or measured global minimum distance is claimed. Singularity conditioning and actual collision-distance margins are unavailable and must not be displayed as measured values. Position/orientation residuals and controller tracking are checked, but an ABB physical-fidelity claim remains provisional.

Budgets/cancellation are checked between and within ROS calls. Simulator cleanup/restoration can consume additional wall time; it must not be abandoned to claim a tighter budget. Long trials with insufficient reserved execution/restoration budget return unknown. This implementation does not support concurrent independent scene writers or unrestricted fixture redesign.

A confirmed mandatory boundary failure rejects robustness even if MC was not run. Surviving boundary screens remain unknown until actual trials finish; missing counts never become successful jobs or a made-up rate. Duplicate/corrupt scenario evidence remains unknown. The 99% target is empirical, not a statistical guarantee; 100 trials per source would still give a substantially lower 95% confidence lower bound even with all successes.

## Presentation contracts and polling

`GET /api/state` returns compact read-only presentation summaries. Scenario records contain `summary_checks` (all confirmed failed checks, otherwise one unknown representative), `check_count`, scenario identity and outcome. They are deliberately not called complete Plans and are never inputs to execution authorization. Nominal checks and source aggregate counts remain available in the state. `GET /api/evidence?candidate_id=EXACT_ID` returns the unabridged authoritative candidate; `GET /api/audit?sequence=INTEGER` returns a complete hash-linked journal record. Both enforce the same loopback Host allowlist; unknown/invalid keys receive 400/404. Modal inspection persists across polling, and keyed DOM updates preserve interaction stability. No file-path or shell selector is exposed.

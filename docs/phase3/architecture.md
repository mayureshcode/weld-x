# Phase 3 — evidence and commissioning integrity

This extends, rather than replaces, [the verified robotics architecture](../phase2/architecture.md). Ubuntu/Jazzy/Harmonic, the ABB source model, ROS packages, joint interfaces, constraints and both protected benchmarks are unchanged.

## Evidence contract

A `Plan` establishes nominal planning evidence. For an uncertainty trial it is not a complete-job success. `ScenarioExecution` additionally binds the configuration SHA256, runtime/model dependency version, scenario SHA256, exact cached trajectory identity, ordered completed/observed segments, positive feedback sample counts, finite observed joint/TCP/orientation residuals, and confirmed restoration. The observer is trusted backend code, not a client-provided certificate or a calibrated physical sensor.

Aggregation validates declared scenario identities/payloads and rejects duplicates, mixed/stale models and inconsistent outcomes. Each evaluated candidate has explicit `pass`, `fail` or `unknown` status. Missing evidence cannot pass; a confirmed mandatory failure can reject an otherwise incomplete candidate. Classification distinguishes nominal infeasible, nominal feasible but robustness failed, incomplete and fully robust. Unevaluated map points remain separate from failed candidates.

A mandatory boundary screen can establish a necessary-condition failure. It cannot establish a successful execution. All boundary screens are attempted first; if a mandatory failure is found, expensive Monte Carlo execution is not needed to reject that candidate. Otherwise actual boundary trials precede MC trials. Scheduling changes do not change declared amplitudes, seeds or scenario identities. Empirical MC rate and Wilson interval remain unavailable unless all declared MC records are present, conclusive and backed by observed execution. `boundary_screened` is the number of processed boundary records (it includes executed records); it is not disjoint from `boundary_executed`.

The uncertainty runner observes every approach, weld, retreat and transition, reserves time for execution/restoration, restores the nominal simulator/planning scene/controllers, and only then constructs a successful receipt. A failed/unconfirmed restoration blocks authorization. Actual failed observed prefixes and screening-only failures are distinguished.

## Exact approval and placement application

The unchanged explicit engineer approval references the exact recommended candidate and original configuration. `Engine.apply` is a serialized long operation: consume approval, increment revision, invalidate final authorization, audit the change, synchronize the fixed-anchor Gazebo placement and MoveIt geometry, reinitialize controllers as required, and verify live poses. Failure records the new unconfirmed configuration and STOPPED state; it does not pretend that a declarative rollback physically succeeded. Fresh exact held-out revalidation is required in all cases. An observed base, fixture or workpiece drift invalidates binding; execution cannot silently repair it and proceed.

`POST /api/apply` now returns **202**, like other queued operations. Supply `approval_id`, then observe `/api/state.task` and audit. A 202 is not successful application. Existing Host/Origin/CSRF rules, one-operation serialization, error handling and cooperative cancellation remain. There is no remote shell interface. Isolated success-path approval tests use explicitly labelled doubles; no human approval or robust candidate has been manufactured for integration testing.

## Actual-data viewer contract

`GET /api/scene-evidence?candidate_id=EXACT&source=base|fixture|model|combined&scenario_id=EXACT` is read-only and allowlisted. Source/scenario selectors are optional. A matching exact cached MoveIt plan yields world-frame TCP path segments and trajectory identity. No matching cache yields an explicit unavailable reason, never synthetic paths. Scenario selection projects the recorded perturbation along the actual planned weld points and exposes the worst predicted rigid-transform residual.

This preview is a prediction, **not an observed trial, measurement compensation, applied placement or authorization**. The vector is visually magnified ×50 and labelled. The robot itself remains driven exclusively by observed joint feedback; selecting evidence never mutates Gazebo. Source/scenario, path visibility, seam selection, map selection and complete-record inspection use the same backend records. Unknown and unrun MC counts stay visible; a chart cannot override a backend gate.

## Scope limits retained

No calibrated sensing/registration mechanism; no automatic compensation of independent fixture error; no physical dynamics/fidelity verification; discrete collision checking, not a continuous guarantee; singularity and minimum clearance measurements unavailable; simulation gain/inertia assumptions remain provisional. No approved robust recovery or real-world probability is implied by a nominal execution or the single small-error integration fixture.

## Single execution authority and teardown

WELD-X sends the exact validated commands directly to ros2_control through its gated `FollowJointTrajectory` client. The unused MoveIt-internal execution route is disabled with the supported `allow_trajectory_execution=false` parameter; MoveIt planning, IK, FCL and state interfaces remain active. This does NOT prevent manager construction/destruction, and did not fix its shutdown crash. A MoveIt 2.12.4 shutdown crashed in `TrajectoryExecutionManager` / `rclcpp::CallbackGroup` destruction; the original stack is retained. The launch file is included in runtime dependency fingerprints. Post-change tests passed but teardown failed again; both stacks are retained. No arbitrary signal suppression or collision/authorization bypass is used.

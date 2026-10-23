> Historical orchestration checkpoint document. For the current real robotics integration, measured results and remaining blockers, see [Phase 2](phase2/README.md).

# Master specification and architecture

## Mission invariant

Detect → Search → Map → Recommend → Approve → Apply → Revalidate → Execute.

Execution requires every mandatory check for every mandatory segment, exact configuration/model/adapter identity, successful boundary tests, sufficient declared Monte Carlo evidence, held-out final evaluation, a live synchronized backend and single-use authorization. FAIL and UNKNOWN both block execution. A rank or UI status cannot override a hard gate. This is a virtual-only demonstrator, never industrial safety logic.

## Implemented boundaries

| Module | Responsibility |
|---|---|
| model.py | Immutable, extra-field-rejecting Pydantic schema, units, frame convention, configuration hashing |
| validation.py | Complete-segment mandatory evidence coverage and unavailable production adapter |
| robustness.py | Shared deterministic uncertainty scenarios, boundary/MC aggregation, Wilson intervals |
| engine.py | Validation orchestration, bounded search/refinement/ranking, recommendation, approval, revision, revalidation, execution gate, audit |
| server.py | Local HTTP, asynchronous single-worker tasks, cancellation, host/origin/token protection |
| dashboard/ | Real state polling, diagnostics, candidate selection, uncertainty records, audit, visible faults |

No database or microservice is required at this checkpoint. JSONL audit records are persisted with flush/fsync and verified on opening. Server instances acquire an exclusive per-audit-path lock. Audit integrity is not authenticity: no signatures, protected external anchor or tail-truncation detection is claimed. Restart does not restore approvals or execution authorization.

## Units and frames

SI metres/radians/seconds. REP-103 right-handed world; pose roll/pitch/yaw is fixed-XYZ. Upright robot mounting; base height fixed per configuration. Workpiece and fixture poses are in world. `tcp` is flange-to-tool. Seam points and required tool RPY are expressed in the workpiece frame. The source declares this frame; the missing robotics adapter must apply and verify the transformations. Fixture uncertainty moves fixture and attached workpiece consistently; it is not an authorized fixture relocation procedure.

Configurations include full job, tool, robot/model/software identifiers, installation, constraints, uncertainty and budget settings. Hashes cover the entire configuration including revision. No cache is used, avoiding dependency-invalidation ambiguity. Only base x/y/yaw changes are supported by recovery.

## Complete-job evidence

Segments: first approach/weld/retreat; between successive seams a mandatory transition; each subsequent approach/weld/retreat. Each segment requires reachability, IK, joint limits, collision (including self-collision), continuity, TCP tolerance, access, dynamics, timing and controller checks. Missing/duplicate checks, stale hashes, missing trajectory ID, nonfinite metrics or unknown outcomes block nominal feasibility. A backend PASS must represent actual validation, not a geometric score. Production currently returns UNKNOWN for every check.

## Search and ranking

Lazy bounded coarse grid; declared fraction reserved for half-step local refinement around up to three leading evaluated candidates. Maximum candidates, per-attempt wall time, cumulative wall time and attempt count are enforced. Base height never changes. No expansion of bounds or relaxation of requirements. Cheap geometric/kinematic screening is not yet implemented; no global-optimality claim.

Qualification first; then worst per-source MC Wilson lower bound in predefined comparable-width bands; smaller planar relocation; stronger exact lower bound; larger nominal joint-limit margin; lexicographic candidate hash. Fixed bands avoid non-transitive pairwise comparability. Diagnostic/incomplete candidates can be displayed but cannot become recommendations.

No qualifying placement: exact required no-solution message plus bounds/count/budget/termination and retained constraint records. If evaluation is incomplete, no-solution means "none established," not proof of infeasibility.

## Uncertainty design

Three sources: base xy/yaw error, fixture xyz/yaw error, and TCP xyz/yaw model mismatch. All independent uniform bounded, individually and combined. Digital-twin mismatch coverage is deliberately limited to TCP error; link dimensions, flex, friction, timing and calibration mismatch remain unmodeled.

Boundary design includes every nonzero signed axis extreme and two opposite all-dimension corners per source/group. It is NOT exhaustive corner coverage or continuous certification. Monte Carlo shares scenario vectors across candidates using source-separated deterministic RNGs. Search and held-out seed streams differ. One adapter validates all scenarios; there is no independent dashboard simulation pipeline.

All declared boundaries must pass. Each source needs the configured MC count and minimum evidence count and must meet the predeclared empirical success threshold. Missing/unknown trials yield insufficient evidence and no empirical success rate/interval. Wilson intervals describe sampling uncertainty; the threshold applies to empirical rate, not its lower confidence bound. Multiple seeds/repeated experiments are a benchmark protocol, not completed evidence. Simulated rates cannot establish production failure probability.

## Recovery and execution

Recommendation references original configuration and candidate, full evidence, limits and limitations. Explicit self-declared local engineer approval is bound to candidate, job, hash and adapter version. Apply consumes approval, changes only permitted base placement, increments revision and clears execution authorization.

At this checkpoint, apply updates declarative configuration only. Revalidation additionally requires an adapter `synchronize` acknowledgement for the exact hash before any authorization is possible. That acknowledgement must cover both Gazebo and MoveIt in a future adapter. Production synchronization cannot succeed.

Final revalidation always reruns nominal plus held-out trials. Failures stop; further bounded search and fresh approval are necessary. Execute consumes authorization even on controller errors. Completion requires exact trajectory/config identity, all observed segments in order, finite tracking error within the declared bound, no cancellation and no timeout. The unit-test adapter proves orchestration behavior ONLY; it is not a controller or robot implementation.

Cancellation/deadlines are cooperative. A future native adapter must bound/cancel planning and controller actions itself; Python cannot forcibly interrupt an arbitrary hung native call. No industrial emergency-stop guarantee exists.

## Decisions

- D01 accepted: preserve host; no incompatible ROS installation or unsupported robot substitution.
- D02 accepted: Pydantic + stdlib HTTP/unittest; avoid unnecessary infrastructure.
- D03 accepted: unavailable adapter by default; no production "demo success" toggle.
- D04 accepted: full revalidation, not incremental dependency assumptions.
- D05 provisional: ABB IRB 120 source candidate; no verified robot model yet.
- D06 accepted: local-only self-declared approval; authenticated multi-user operation requires separate engineering.

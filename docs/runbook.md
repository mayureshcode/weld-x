> Historical orchestration checkpoint document. For the current real robotics integration, measured results and remaining blockers, see [Phase 2](phase2/README.md).

# Runbook, experiment protocol and risks

## Reproducible local negative-path demonstration

1. Install project dependencies into a repository-local venv, as in README.
2. `python3 -m unittest discover -v` (or venv python).
3. `python3 -m weldx.server --config examples/job_01.json --audit .runtime/demo.jsonl`.
4. Open localhost:8765. Observe NOT CONNECTED robotics and LOCKED authorization.
5. Run detection. Every required segment/gate is UNKNOWN, not PASS.
6. Search placements. Select an actual evaluated candidate. Inspect constraint diagnostics and unknown robustness. No recommendation/approval appears because no candidate qualifies.
7. Run detection again, then revalidate current configuration. Scene synchronization is unconfirmed; workflow stops and execution stays locked.
8. Disconnect the backend (Ctrl+C). Console reports backend disconnected, stale data and locked controls.

This is a genuine missing-runtime failure demonstration. It is NOT the required successful welding demonstration. Tests use separate labelled doubles to exercise success/approval/recovery logic without impersonating physics.

## Browser checks

Start a fresh server process. With Playwright available and installed Chromium, run `WELDX_CHROMIUM="$(command -v chromium)" node tests/browser.cjs`. On systems using Playwright's bundled browser, omit WELDX_CHROMIUM. The build sandbox already supplies both tools; users of another host must install browser-test dependencies separately. Script captures desktop/mobile/records/disconnect states and a JSON check report. View screenshots; browser assertions alone are not visual QA.

## Planned simulation acceptance (not run)

Record exact package/model/controller versions, spawn logs, joint feedback, deliberate collision rejection, one feasible complete job, one infeasible job, robust bounded alternative, explicit engineer approval, exact dual-scene application/revalidation, full observed job execution, no-solution case and failed-revalidation bounded stop. Save commanded and observed trajectories with timestamps/frames. No simulator launch command can be supplied until those packages exist.

## Benchmark protocol — NOT RESULTS

Five supplied input jobs are a starting set, not feasible baselines. Freeze commissioned job definitions, thresholds, model versions, bounds and hardware before measurements. Compare:
1. Manual engineering baseline if an engineer performs and records it; otherwise N/A.
2. Nominal first feasible.
3. Nominal-ranked under the same candidate/wall-clock budget.
4. WELD-X robust search + engineer approval + fresh held-out validation.

Proposed repeated seed pairs: (1701,2903), (1702,2904), (1703,2905). Search and held-out vectors are separate; share held-out vectors across methods/candidates. Defaults: 20 MC samples/source, 0.95 empirical threshold, all declared axis/two-corner boundaries required. These small samples may be insufficient for reliability claims; report Wilson intervals and model limitations rather than asserting significance. Threshold/count changes must be predeclared, not selected after outcomes.

Record job/method/seed/config/model identity, complete-job success, MC denominator, failures/unknowns by seam and gate, boundary failures, candidate count, wall/CPU time, peak RSS, relocation, available clearance/joint margins, approval/apply/revalidation outcome, execution tracking and recovery consumption. Keep scenario records. Report paired measurements with sample sizes; no physical production probability inference. Current benchmark result: **NOT RUN**. Negative-path HTTP search timings measure orchestration overhead only, not planning performance.

## Risks and limitations

- R01 BLOCKING: no compatible ROS/Gazebo/MoveIt execution environment. No integrated robotics claim.
- R02 HIGH: robot model provisional; upstream ROS 1 source requires migration/verification, including zero effort limits and flange/tool frames.
- R03 HIGH: only TCP offsets model digital-twin mismatch; no physical calibration, structural/flex/friction/process model.
- R04 HIGH: cooperative deadline/cancel cannot kill hung native work. Real adapter must use bounded cancellable ROS actions; no industrial safety stop guarantee.
- R05 HIGH: local engineer name is self-declared; no multi-user authentication, signatures, authorization service or tamper-proof evidence.
- R06 MEDIUM: audit/snapshot grows without pagination; not a multi-process engine. Server enforces per-audit writer lock; direct library callers must also ensure a single writer.
- R07 MEDIUM: state/authorization is intentionally not restored after restart. Audit survives; results cannot silently reauthorize.
- R08 MEDIUM: five example jobs vary geometry/orientation but are not commissioned feasible jobs or exhaustive benchmark coverage.
- R09 MEDIUM: 2 CPU/4.2 GiB host may be inadequate for concurrent simulation/planning/rendering. No simulation resource profile exists.
- R10 MEDIUM: no project distribution license selected. Upstream model not copied. Review package/asset licensing before vendoring/publishing.
- R11 MEDIUM: core CI definition is local/archive only. GitHub rejected the batch containing the workflow with 403; the same batch excluding it succeeded. Workflow publication needs appropriate connection permissions; no remote CI pass is claimed.
- R12 MEDIUM: sensor/controller tracking semantics depend on a trusted future adapter; finite bounded scalar tracking alone is not full TCP execution proof.

## Troubleshooting

- `ModuleNotFoundError: pydantic`: activate the local venv, install project dependencies. Do not install global host robotics packages as a shortcut.
- `Address already in use`: choose `--port 8766`; stop only the WELD-X process you started.
- Audit writer lock: stop the process owning that same audit path or select a new path; do not delete another process's lock/file.
- Audit integrity failure: preserve the journal, investigate truncated/corrupt records; use a new path for an independent run. Never silently discard failed history.
- Search says incomplete/no solution: inspect UNKNOWN checks. With the current adapter this is expected, not evidence that every placement is infeasible.
- Execute/Approve disabled: backend gates have not passed. Do not bypass them.
- 403 API: correct local Host/Origin and fresh `/api/session` token. Restart rotates tokens.
- Console inaccessible outside sandbox: loopback-only by design; use an authenticated tunnel or deploy only after proper auth/TLS engineering.

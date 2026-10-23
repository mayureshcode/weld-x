# Phase 3 ledger — continuation of 58191bd

The baseline audit, protected file hashes and environment verification are in `evidence/phase3/baseline-audit.json`. Local history is the preserved Phase 2 source mirror; the remote engineering branch is the publication target. Main is not changed. Existing untracked Phase 1 screenshots are preserved.

## Implemented changes (verification evidence, not assumptions)

- Structured `ScenarioExecution` receipts bind the exact configuration, adapter/model dependency version, scenario perturbations, trajectory identity, ordered segments, feedback counts, observed errors and restoration. A planning PASS without this receipt is unknown for robustness. Receipt tampering, partial MC, and stale binding tests are included.
- Aggregation separates recorded screens, complete/failed observed execution, missing scenarios, inconclusive results and unavailable empirical rates. No unexecuted boundary screen becomes a successful complete job.
- Approval application is serialized and asynchronous through the API. It consumes the exact approval, increments the configuration revision, invalidates authorization, synchronizes the actual scene/controllers, and records any unconfirmed application without silently rolling back. Exact held-out revalidation remains mandatory.
- Actual observed base/fixture/workpiece drift invalidates runtime binding. Direct execution cannot silently restore an unapproved drift and proceed.
- Recommendation audit payloads now include original failure evidence, exact proposed placement, actual nominal/robust results, declared assumptions and bounded-search limitations.
- The viewer can display exact cached MoveIt TCP trajectories and the rigid-transform consequences of a selected recorded uncertainty scenario. The residual vector is explicitly magnified ×50 and labelled a prediction, never measured feedback, applied placement or compensation. Live robot motion still comes only from observed joint feedback.
- Source-specific sensitivity counts distinguish screening failures from actual complete jobs, missing MC and unavailable rates; candidate comparisons use actual source groups.

## Verification ledger

- Core/API receipts/application tests: see `core-final.log` (65 passed at this checkpoint).
- Actual 0.1 mm fixture-X integration fixture: `actual-complete-scenario.json`, `actual-scenario-receipts.log`. All seven segments executed with scenario-bound observed feedback and verified restoration; actual fixture-drift binding rejection also passed. One integration sample is not benchmark reliability evidence.
- Policy comparison: protocol frozen at `benchmarks/policy_comparison_v1/protocol.json`, full scenarios written before evaluation. Two jobs, two seed blocks, eight identical candidate evaluations per policy replay. Human manual performance is unavailable: the original placement is explicitly only a fixed-placement proxy. No synthetic manual time or approval is reported.
- Full real regression: 20 passed; nominal suite: 5/5 actual jobs passed; connected browser workflow: 8 checks passed, no JavaScript errors after a preserved mobile-overflow failure and targeted fix. See the final report and original logs. Publication receipts are separate; no CI or main merge is claimed.

## Engineering decision still required

No supported measurement/compensation mechanism exists. Recovery-v1 has an invariant allowed 1.5 mm relative translation error against the unchanged 1.0 mm Euclidean TCP limit, plus retained yaw/calibration failures. Base relocation cannot remove independent fixture error. Strict and recovery-v1 job definitions and their existing evidence remain unchanged. A separately versioned simulation measurement experiment requires explicit engineering authorization and declared residual assumptions; it is not silently substituted for v1.

Successful approved real commissioning and the 99% complete-job MC target remain unverified until an admissible experiment genuinely satisfies all mandatory gates and receives exact engineer approval.

## Teardown investigation result

65 core tests, 20 real robot integration tests, five nominal jobs and eight connected browser checks passed again with the unused MoveIt-internal execution route disabled. Shutdown still failed twice in MoveIt 2.12.4 / rclcpp callback-group destruction. The attempted mitigation did not resolve it; both stacks and shutdown-verification.json are retained. This is a known unresolved defect, not clean-shutdown acceptance.

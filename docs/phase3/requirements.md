# Phase 3 acceptance traceability

| User requirement | Implementation / evidence | Acceptance category |
|---|---|---|
| Continue branch/checkpoint; preserve work | baseline-audit.json, protected-inputs-final.json; local mirror ancestry explicitly documented | Verified preservation; remote publication receipts separate |
| Real industrial robot and nominal jobs | existing pinned ABB model, real ROS/Gazebo controller integration; robotics-regression.log, nominal-suite.json | 20 real integration tests and 5 nominal jobs passed; physical fidelity provisional |
| Meaningful robustness status | validation.py ScenarioExecution; robustness.py aggregation; test_scenario_receipts.py, candidate snapshots | Implemented/core tested; actual complete small-error receipt verified |
| Boundary screens are not successes | fail/unknown/observed evidence kinds and source counts | Real rejected benchmarks and connected dashboard; no fabricated MC rate |
| Recovery-v1 diagnosis without relaxation | protected SHA256; recovery-diagnosis.json; recovery-v1/evaluation.json | Confirmed no-solution/rejected result, not a successful recovery |
| Exact recommendation/approval/apply/invalidation | engine.py; server.py asynchronous apply; test_application_sync.py; existing integrity cases | Success path isolated tests; unqualified actual API attempts rejected |
| Actual placement/controller/live pose/joints | adapter.py binding_valid; existing scene.py fixed-anchor respawn; tests_robotics | Integration-tested; not a successful approved robust commissioning chain |
| Exact held-out revalidation and execution gate | exact version/model/scene binding and all mandatory gates | Core tested; real failed/unknown evidence blocks; no qualifying held-out experiment |
| Map and sensitivity from actual data | app.js, scene.js, model_view.py read-only exact evidence endpoint | Connected browser evidence; explicit predicted residual, no independent robot animation |
| No-solution end-to-end | real detect/search/map/denied approval/apply/execute and disconnect checks | Browser workflow report records exact result; execution remains blocked |
| Recoverable failure + explicit engineer approval | no admissible robust placement/no real measurement compensation under current assumptions | Blocked; no fabricated approval or tolerance changes |
| Fair manual/nominal/robust comparison | policy_comparison_v1/protocol.json, four blocks, shared pools, results.json and analysis/evidence.json | Actual paired selection comparison; manual human study and per-policy timings unavailable |
| Keep 5 nominal regressions | nominal-suite.json and .log; original Phase 2 evidence retained | 5/5 actual Gazebo jobs passed again |
| Publish engineering branch only | publication.json and GitHub commit receipts (when present) | No main merge, no CI claim |

Unresolved release defect: two MoveIt shutdowns fail with signal 11 in callback-group destruction. The internal execution-route parameter did not resolve it; operational tests passed before both shutdowns. See shutdown-verification.json and both launch logs. Final clean-shutdown acceptance is not passed.

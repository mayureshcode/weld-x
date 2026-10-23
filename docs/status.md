> Historical orchestration checkpoint document. For the current real robotics integration, measured results and remaining blockers, see [Phase 2](phase2/README.md).

# Requirement traceability and progress ledger

A file or unit-test pass is not robotics commissioning evidence.

| Milestone | Status | Evidence / remaining acceptance |
|---|---|---|
| 0 Audit | Complete for available host/repository | docs/audit.md; no prior work changed |
| 1 Robot/cell | BLOCKED | Source assessed statically; no model loading, cell, Gazebo or controllers |
| 2 Nominal complete job | BLOCKED | Segment ordering/input support only; no planning or motion |
| 3 Validation | Partial | Gate completeness/fail-closed rules tested; physical checks absent |
| 4 Placement search | Partial | Bounds/refinement/budgets/ranking tested with labelled doubles; no robotics feasible candidate established |
| 5 Robustness | Partial | Scenario generation/aggregation/reproducibility tested; no physics trials |
| 6 Recovery/integrity | Partial | Approval/version/revalidation/authorization tested with doubles; dual scene update absent |
| 7 Map/sensitivity | Partial foundation | Real candidate/uncertainty tables; spatial map, causal analysis and 3D linking absent |
| 8 Dashboard | Partial | Real API, responsive diagnostics/health/audit, visible disconnect; no simulator integration |
| 9 Verification | Partial | Core/API/browser evidence only; no robotics E2E or benchmark |

## Acceptance mapping

| Requirement group | Implementation / tests | Status |
|---|---|---|
| Configuration/units/version | model.py; schema/example/immutability tests | Locally passed |
| Mandatory hard gates / unknown / completeness | validation.py; missing/duplicate/stale/nonfinite/failure tests | Rules passed; robotics checks absent |
| Bounded search / ranking / no solution | engine.py; grid/refinement/ranking/attempt/time tests | Orchestration passed |
| Robustness source design / reproducibility | robustness.py; seed/boundary/insufficient-count tests | Design/aggregation passed; empirical robotics results absent |
| Approval / apply / exact revalidation | engine.py; stale approval/hash/adapter/scene tests | Orchestration passed |
| Execution blocking and tracking | engine.py; disconnect/unknown/segment/tracking/error/cancellation tests | Safety orchestration passed with doubles; no actual simulator execution |
| API / live-data UI | test_api.py, tests/browser.cjs | Local unavailable-backend path tested |
| Reference robot / collision / controller / job motion | None commissioned | BLOCKED |
| Engineering map / scene / explorer | Candidate records only | Incomplete |
| Multiple jobs | examples/job_01..05.json | Schema validated only |
| Benchmark / physical validity | docs/runbook.md protocol | Not run; no significance claim |

## Highest-priority remaining work

1. Provide an accessible Ubuntu 24.04 Jazzy/Harmonic/MoveIt environment (native or an actually available supported container/remote workspace).
2. Pin robot source/license assets; validate Xacro/meshes/joint transforms/limits and migration; add verified simulation ros2_control and planning configuration.
3. Spawn the cell; observe joint feedback/controllers; execute one complete known-feasible single seam with collision checks.
4. Implement trusted adapter and dual-scene synchronization, then test deliberate collisions and infeasible jobs.
5. Run actual placement/held-out robustness trials; connect real spatial map, sensitivity visualizations and 3D selection.
6. Extend to multi-seam and five job benchmarks, then complete the original definition of done.

No mandatory blocked milestone is marked complete. Robotics infrastructure is a genuine blocker; the unrelated host was not altered to disguise it.

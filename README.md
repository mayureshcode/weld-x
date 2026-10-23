> Current continuation: [Phase 3 report](docs/phase3/final-report.md) and [Phase 3 runbook](docs/phase3/runbook.md). Historical checkpoint text below is retained, not a current acceptance claim.

# WELD-X — evidence-gated virtual commissioning

**Current work: `engineering/robotics-integration`; main checkpoint preserved. The project is not yet fully commissioned.**

Real Jazzy/Harmonic/MoveIt robotics and five nominal jobs now execute in the verified project-local Ubuntu environment. The separately versioned 99%-target recovery benchmark is **rejected by mandatory boundary tests**, not represented as a successful recovery. No physical welding or safety certification is claimed.

- [Current engineering report](docs/phase2/README.md)
- [Install, launch and test runbook](docs/phase2/runbook.md)
- [Architecture and actual interfaces](docs/phase2/architecture.md)
- [Acceptance ledger](docs/phase2/acceptance.md)
- [Decisions, risks and next actions](docs/phase2/risks.md)
- Proposed assumptions and frozen scenarios: `benchmarks/recovery_v1/`
- Original asset hashes/licensing: `third_party/abb/`; run `python3 tools/fetch-robot-assets.py` before building a fresh checkout.

---

## Original orchestration checkpoint (historical)

# WELD-X

**Evidence before execution.** Virtual robotic welding commissioning, targeting Ubuntu 24.04, ROS 2 Jazzy, Gazebo Harmonic and MoveIt 2.

## Honest project status

This is a **tested orchestration foundation**, NOT a completed robotic welding simulator. The build environment has no ROS/Gazebo/MoveIt runtime. The production adapter explicitly returns UNKNOWN; it never fabricates collision checks, trajectories or successful motion. ABB IRB 120 remains **PROVISIONAL**.

Implemented and locally exercised:
- Immutable SI configuration schema and SHA-256 configuration identity.
- Complete-job segment ordering, mandatory per-segment gate coverage, fail/unknown distinction.
- Bounded x/y/yaw coarse search and local refinement; deterministic gated ranking.
- Per-source/combined boundary and seeded Monte Carlo scenario design, held-out seeds, aggregation and Wilson intervals.
- Version-bound recommendation, explicit approval, single-use application, fresh revalidation and single-use execution authorization.
- Hash-linked disk audit, errors/rejections, cooperative cancellation and cumulative search budgets.
- Loopback API and responsive dark console using actual backend records; disconnected/unknown states keep execution locked.

**Not implemented/verified:** ROS packages, robot model migration, cell assets, IK, MoveIt planning/collision checking, ros2_control, Gazebo motion, a spatial robustness map, 3D scene linking, production Sensitivity Explorer, robotics benchmark or complete simulated job execution. Scenario generation is implemented; no physical-model robustness trial has run.

## Run the existing console

From the repository root, with Python 3.12+:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
python -m unittest discover -v
python -m weldx.server --config examples/job_01.json --audit .runtime/audit.jsonl
```

Open **http://127.0.0.1:8765** on the same host. In a remote environment, use an authenticated localhost tunnel; no public listener is provided. This chat's sandbox localhost is not a public deployment.

Run detection, then search: placements will honestly show `validation_incomplete`. Re-run detection before revalidating the current configuration. Execution will remain disabled. Stop with Ctrl+C; do not kill unrelated processes. No simulation launch command exists yet.

## Verification

```bash
python3 -m unittest discover -v
python3 -m compileall -q weldx tests
node --check dashboard/app.js
# Optional: install Playwright locally, start a FRESH console, then:
WELDX_CHROMIUM="$(command -v chromium)" node tests/browser.cjs
```

The browser test needs Playwright and Chromium, not ROS. Test doubles in `tests/support.py` are labelled orchestration fixtures and cannot be selected through the production API. Their success is **not simulation evidence**.

The core CI workflow is retained in the downloadable workspace archive but **not published to GitHub**: the connected token rejected a batch containing workflow configuration (403). Publishing code/evidence without it succeeded. No remote CI run is claimed.

## Engineering record

- [Audit and robot assessment](docs/audit.md)
- [Master specification and architecture](docs/architecture.md)
- [Requirement/milestone ledger](docs/status.md)
- [API and adapter contract](docs/interfaces.md)
- [Runbook, benchmark protocol, risks and troubleshooting](docs/runbook.md)
- [Final checkpoint report](docs/report.md)
- [JSON schema](docs/configuration.schema.json)
- [Observed test output](evidence/unit-tests.log)
- [Observed browser checks](evidence/browser-tests.json)

Five example job inputs cover single/two-seam positions and orientations. They are uncommissioned **input fixtures**, not five verified feasible welding jobs.

Virtual-only. No physical actuation, real welding, certification or production-reliability claim. No project license has been selected; third-party source licensing is recorded in the audit.

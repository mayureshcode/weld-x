# Acceptance and evidence ledger

Categories are deliberately distinct: implementation, isolated test, real integration test and end-to-end commissioning acceptance are not interchangeable.

| Milestone | Implemented / tested | Current acceptance |
|---|---|---|
| 0. Audit | Actual OS/resources, rootfs feasibility, versions, branch/checkpoint and initial 50-test baseline | Verified |
| 1. Robot/cell | Two ROS packages build; source ABB kinematics/meshes, KDL/OMPL/FCL, actual Gazebo and controller feedback, visually inspected GUI | Integration-tested; physical model fidelity provisional |
| 2. Nominal job | Seven ordered two-seam segments; five varied nominal fixtures execute in real Gazebo | Nominal integration verified, not robust commissioning authorization |
| 3. Validation | IK, source bounds, Cartesian residuals, discrete collisions, timing/dynamics and observed tracking; known infeasible/collision tests | Integration-tested within documented discrete/model limits |
| 4. Search | Bounded grid/refinement, deterministic hard-gated ranking and cumulative budgets | Core tests pass; connected real no-solution workflow evidence recorded separately |
| 5. Robustness | Versioned parameters, exact seeded scenarios, individual/combined/opposed boundaries, open-loop real execution for survivors | One actual perturbed complete-job fixture passed; proposed benchmark rejected; 99% MC target not demonstrated |
| 6. Approval/recovery | Exact approval and version invalidation, actual pose/controller synchronization, dependency binding, stop/retry budgets | Isolated integrity tests and real synchronization pass; successful approved real recovery remains unverified |
| 7. Map/sensitivity | Actual candidate points, original/recommended legend, selected diagnostics/comparison/seam overlay and source records | Connected UI tests; no interpolated feasibility or invented rates |
| 8. Dashboard | Real URDF/meshes and observed joints/poses, status, controls, evidence, audit and connection fault handling | Actual desktop/mobile checks recorded; not an independently animated success demo |
| 9. Full system | Reproducible scripts, source/licensing, tests, scenario manifests, logs, runbook | Partial. No successful robust approved recovery, no full MC/alternative-method benchmark or CI/main merge claim |

## Exact measured commands

All robotics commands below ran through `tools/in-ubuntu /workspace/tools/ros-env`, with `/opt/weldx-venv/bin/python` unless noted.

| Command | Recorded result / scope |
|---|---|
| `python -m unittest discover -s tests -t . -v` | 55 tests passed in `core-regression-final.log`; default unavailable runtime and approval tests use labeled doubles where appropriate |
| `python -m unittest discover -s tests_robotics -t . -v` | 18 actual ROS/Gazebo integration tests passed in `robotics-regression-final.log` |
| `python -m robotics.nominal --execute` | Complete two-seam job passed, seven segments; 102.61 s including planning under software GUI load; maximum recorded in-motion TCP error 0.1915 mm |
| `python -m robotics.nominal_suite` | Five of five predefined nominal jobs passed; latest recorded wall times 11.32, 19.44, 16.58, 8.98, 9.58 s in the headless test setting |
| `python -m robotics.diagnostic_tests` | Actual self-collision fixture detected; cancellation acknowledged with action status 5; observed movement 0.001952 rad, subsequent sampled drift 0 rad over 0.3 wall seconds |
| Single `integration:small-fixture-error` scenario | Full seven-segment real Gazebo trial passed with +0.1 mm fixture-X error; one labeled integration case, not a Monte Carlo estimate |
| `python -m robotics.benchmark` | Recovery v1 nominal passes; 60 boundary screens, 20 violations, rejected; 0 benchmark MC jobs executed; no success-rate assertion |
| `python3 tools/browser-workflow-test.py` | Connected real detection/search/map/source/viewport/disconnect/denial results in `dashboard-workflow-tests.json`; passed all ten listed checks, with no JavaScript errors; see final JSON for exact search limits and measurements |

The final core and real-robotics reruns cover dependency fingerprints, start-state checks and controller-health polling. A pending callback warning exposed teardown scheduling in the multithreaded executor; a dedicated single-threaded spin loop now owns callbacks, and the final integration log exits cleanly. Earlier logs alone are not used as proof for later changes.

## Failures and corrections preserved

- Initial test discovery without `-t .` failed imports; corrected invocation passed.
- Node `clients` property and weak-referenced executor construction errors were diagnosed and corrected.
- Controller success with 1.122 mm endpoint error was correctly rejected; tighter simulation goal convergence fixed it.
- In-motion TCP lag of 6.704 mm was detected, not hidden by endpoints; simulation-only gain/rate corrected it without tolerance relaxation.
- Returned Cartesian timing ignored requested speed; conservative independent retiming and checks added.
- Direct anchored-model pose acknowledgement did not establish actual relocation; exact anchored respawn/readback passes.
- Python transport request timeout beside callbacks was fixed with bounded process-isolated transport requests.
- Exactly equal uncertainty boundaries had floating-point false violations; numerical guard fixed and regression-tested; first report kept.
- Browser polling initially attempted CSP-blocked unsafe evaluation; the test harness was corrected to DOM polling without weakening CSP.

## Not verified / blocked

No candidate has a complete qualifying robustness record under the current declared envelopes. No successful engineer approval → application → exact held-out revalidation → complete execution recovery is claimed. There is no calibrated physical measurement/compensation mechanism, physical welding, certified safety, proof of global optimum, continuous-collision proof, measured singularity margin, statistically established production failure probability, full manual/nominal/robust benchmark comparison, CI success or main merge.

## Dashboard performance and interactive stability

A real workflow exposed a 22,140,267-byte repeated status payload. Polling now sends presentation summaries only, with full authoritative candidate and audit records available on explicit read-only allowlisted requests. Gate calculations still consume original complete records; no validation evidence was truncated or replaced. The final browser report records response bytes and measured wall time. Polling also exposed detached controls while whole tables were rebuilt; keyed updates now preserve unchanged controls, source diagnostics and map points. Failed test attempts are preserved.

# WELD-X — Phase 3 engineering delivery

## Executive outcome

**Verified progress, not full commissioning acceptance.** The existing real ROS 2 Jazzy / Gazebo Harmonic / MoveIt foundation now has scenario-bound observed execution receipts, stricter robustness aggregation, exact asynchronous application/synchronization, live pose binding checks, connected trajectory/scenario evidence and a measured paired policy comparison. The completed negative commissioning demonstration correctly rejects invalid evidence and prevents approval/application/execution. A successful approved robust recovery remains blocked by the unchanged engineering assumptions, not hidden by nominal successes.

- Repository: https://github.com/mayureshcode/weld-x
- Working/publication branch: `engineering/robotics-integration`; remote baseline `58191bd134bdb55cef1ad91b72376db3302f4b48`. **Main was not merged or modified.**
- Local baseline: `2207ce6` is the preserved source/evidence mirror. Local and remote commit ancestry are not identical; published changes use the authorized GitHub file API, not a fabricated fast-forward Git push. See `evidence/phase3/publication.json` for returned remote commit IDs and verification.
- Strict and recovery-v1 input hashes match the initial audit exactly: `protected-inputs-final.json`. Their thresholds, scenarios and tolerances are not relaxed.
- Actual environment: project-local Ubuntu 24.04.3 on Amazon Linux 2023 x86-64; Jazzy, Gazebo 8.15.0, MoveIt 2.12.4, gz_ros2_control 1.2.20. ABB source kinematics/model and simulator/controller integration are exercised; physical fidelity remains PROVISIONAL.

## Implemented feature inventory

1. **Structured complete-job evidence:** exact configuration/model/scenario/trajectory binding, ordered observed segments, feedback counts, finite measured residuals and confirmed restoration. A planning PASS or a surviving screen cannot pass robustness.
2. **Truthful robustness accounting:** pass/fail/unknown candidate states; per-source screening, observed execution, failure, unknown and missing counts; empirical MC rates/intervals unavailable when evidence is incomplete. Duplicate/stale/inconsistent records cannot authorize execution. All mandatory boundaries are scheduled before MC without changing the declared scenario set.
3. **Application and execution integrity:** serialized asynchronous application consumes exact approval, increments version, invalidates authorization and synchronizes Gazebo/MoveIt/controllers/readback. Unconfirmed application records STOPPED rather than pretending to roll back. Live base/fixture/workpiece drift revokes exact runtime binding.
4. **Actual-data UI:** map, comparison, diagnostics and sensitivity use the original candidate records. Candidate/source/scenario selections link to the exact cached MoveIt TCP paths. The selected perturbation's residual is explicitly a predicted rigid-transform consequence, visually magnified ×50, never compensation, observed trial success or a scene mutation. Live robot motion comes from actual joint feedback.
5. **Measured policy comparison:** preregistered inputs/seeds, four shared candidate pools, actual nominal replay and held-out screens; no invented human baseline or per-policy timing claims.
6. **Reproducible delivery:** preserved failed attempts, logs, protected-input checks, architecture/API changes, requirement ledger and launch/test runbook. Large authoritative records are losslessly compressed for GitHub and retained raw in the archive.

Architecture: [contracts and evidence](architecture.md). Requirement coverage: [traceability](requirements.md). Execution/reproduction: [runbook](runbook.md).

## Milestone acceptance

| Milestone | Current measured status |
|---|---|
| 0 Environment / baseline | Actual runtime checked; existing branch/source preserved; protected input hashes verified |
| 1 Robot / cell | Real integration regression passed; original ABB model/TCP/frames/controller/pose checks retained; physical fidelity provisional |
| 2 Complete nominal jobs | Five of five predefined jobs execute in Gazebo again, including the seven-segment two-seam job |
| 3 Validation / diagnosis | Real model/IK/collision/controller checks plus exact receipt/binding tests pass within declared discrete/model limits |
| 4 Placement search | Actual bounded search populates map; shared policy experiment evaluates 32 candidates; no robust solution reported |
| 5 Robustness | Actual small-error complete-job receipt passes; mandatory boundary failures reject protected jobs; 99% empirical MC acceptance is NOT demonstrated |
| 6 Approval / recovery | Success path isolated tests; actual pose/controller synchronization and unqualified API denial tested; successful engineer-approved robust recovery unverified |
| 7 Map / sensitivity | Connected actual candidate/source/scenario/trajectory inspection passes; unrun MC remains unavailable |
| 8 Dashboard | Real connected desktop/mobile workflow passes after a measured selector overflow fix; disconnect locks execution |
| 9 Full acceptance | **Not complete:** no admissible robust placement, successful approved recovery, human manual study or remote CI acceptance |

The final functional launch hardening disables only the unused MoveIt-internal execution request route. It did **not** fix the observed teardown fault; see the preserved attempts below.

## Exact tests and outcomes

All commands run from the repository root. Robotics commands use `bash tools/in-ubuntu /workspace/tools/ros-env /opt/weldx-venv/bin/python`; core tests use the same project-local Python without requiring ROS imports.

| Command / evidence | Actual result and interpretation |
|---|---|
| `python -m unittest discover -s tests -t . -v` → `core-post-teardown-fix.log` | **65 passed**, 16.359 s; isolated doubles explicitly labelled, not simulator acceptance |
| `python -m unittest discover -s tests_robotics -t . -v` → `robotics-post-teardown-fix.log` | **20 passed**, 80.733 s; actual ROS/Gazebo/MoveIt scene, feedback and complete-job integration |
| `python -m unittest tests_robotics.test_adapter.ActualAdapterTests.test_01_exact_nominal_contract -v` | Additional targeted rerun after moving the test output away from historical evidence; see `adapter-evidence-path-regression.log` |
| `python -m robotics.nominal_suite --output-dir evidence/phase3/post-teardown-fix` | **5/5 actual nominal jobs passed**; per-job data below |
| `python -m robotics.benchmark --output-dir evidence/phase3/post-teardown-fix/recovery-v1` | Nominal pass, robustness fail; 60 boundary screens, 20 confirmed violations; rejected |
| `python -m robotics.benchmark --config examples/commissioning_two_seam.json --output-dir evidence/phase3/post-teardown-fix/strict` | Nominal pass, robustness fail; 60 boundary screens, 40 confirmed violations; rejected without changing strict inputs |
| `python -m robotics.policy_benchmark` | Four job/seed blocks completed; 32 candidates, 6 distinct actual nominal executions, all six nominal pass; no robust qualifier |
| `python3 tools/browser-phase3-test.py` | **passed**, 8 recorded checks, no JavaScript errors; actual detect/search/evidence/viewport/denial/disconnect; visual screenshots inspected |
| `python3 tools/analyze-policy-results.py` | Pandas aggregation and independent raw-list cross-check passed; one evidence object and count chart produced |
| Python compileall; Node syntax checks; `git diff --check` | Final output recorded in `source-hygiene.log` |

A targeted actual **+0.1 mm fixture-X** integration fixture completed all seven approach/weld/retreat/transition segments, with feedback counts `[401, 234, 62, 32, 62, 232, 61]` and maximum propagated observed TCP residual **0.137648 mm**, followed by confirmed nominal-scene restoration. This is **one designed integration fixture**, not a random sample or proof of the 99% target. The same suite detects actual 3 mm fixture drift and invalidates exact binding.

### Five nominal regressions

| Job | Completed segments | Measured wall seconds | Outcome |
|---|---:|---:|---|
| `nominal_straight_butt_v1` | 3 | 21.27 | passed |
| `nominal_parallel_seams_v1` | 7 | 43.20 | passed |
| `nominal_l_corner_v1` | 3 | 38.13 | passed |
| `nominal_raised_short_v1` | 3 | 17.84 | passed |
| `nominal_angled_torch_v1` | 3 | 19.18 | passed |

These directly commanded **nominal integration harnesses** do not authorize commissioning or stand in for engineer approval. Headless simulation ran at the default real-time setting; older Phase 2 speed measurements used a different headless rate and must not be treated as a regression comparison.

## Recovery-v1: actual cause and preserved no-solution outcome

The proposed simulation assumptions remain ±0.5 mm robot-base X/Y and ±0.5 mm fixture X/Y/Z, **not validated physical specifications**. The TCP Euclidean position tolerance remains 1.0 mm. Retained yaw and TCP calibration envelopes are unchanged too. Robot kinematics, the supported 0.12 m axial TCP, fixture/workpiece rigid attachment frames and independent-error propagation are covered by real frame/FK tests.

An allowed opposed-translation corner alone gives `sqrt(1.0² + 1.0² + 0.5²) = 1.5 mm` relative error, with yaw/calibration set to zero. This is invariant to nominal base translation: moving the base does not measure or cancel independent fixture error. Retained yaw/calibration uncertainties add further failures. Actual boundary records confirm violations, not merely this analytic argument.

| Recovery-v1 source | Required boundary screens | Confirmed failures | Inconclusive/screen survivors | Completed observed successes |
|---|---:|---:|---:|---:|
| base | 8 | 4 | 4 | 0 |
| fixture | 10 | 2 | 8 | 0 |
| model | 10 | 2 | 8 | 0 |
| combined | 32 | 12 | 20 | 0 |

All **60 screens** ran; **20 confirmed failures** are sufficient to reject robustness. The remaining screens are unknown as complete-job evidence, not successful jobs. The experiment predeclares **100 MC trials/source × four groups = 400/phase**, a **99% empirical target**, fixed search seed 20261023 and separate held-out seed 20261123. **Zero benchmark MC jobs executed**, so no empirical MC success rate or confidence interval is reported. Testing more MC cases cannot reverse a mandatory boundary failure. One passing small-error fixture does not replace those counts.

No supported physical measurement/registration/compensation mechanism exists. Truth used to perturb simulation geometry is not exposed as perfect weld-path compensation. A separate measurement experiment needs explicit engineering authorization, declared unvalidated residual assumptions, a separate version and complete new validation. No such decision has been silently made. Strict fixture ±2 mm and TCP ±1 mm remain intact as a negative benchmark.

## Policy comparison: measured, not a fabricated manual benchmark

Protocol: `benchmarks/policy_comparison_v1/protocol.json`; frozen scenarios were written before evaluation. Two existing jobs × two search seeds (20261023, 20261024), eight bounded candidates/block (six coarse plus two local) and 180 s pool budget/block. Policies replay the identical pool. Distinct selected configurations execute once per block, with reuse explicitly labelled; policy rows are not independent repeated experiments. Held-out boundary evidence uses the separate declared seed.

- **32 evaluated candidates:** 20 nominally feasible but robustness-failed, 12 nominally infeasible, zero robustness-qualified.
- **Six distinct selected nominal job executions passed** in Gazebo. Every selected nominal candidate failed its held-out boundary requirements.
- The fixed original placement is only a proxy, **not measured human engineering performance**. There is no invented manual task time, success rate or human approval.

| Policy | Job/seed blocks | Selected in blocks | Nominal pass records | Held-out boundary fail records | Fully qualified |
|---|---:|---:|---:|---:|---:|
| `fixed_original_placement_proxy` | 4 | 4 | 4 | 4 | 0 |
| `nominal_first_feasible` | 4 | 4 | 4 | 4 | 0 |
| `nominal_ranked` | 4 | 4 | 4 | 4 | 0 |
| `robust_hard_gated` | 4 | 0 | 0 | 0 | 0 |

The nominal-ranked policy selected a 0.141421 m relocation in both angled-torch seed blocks and improved its reported joint-limit margin from about 0.5579 to 0.6712 rad, but still failed robustness. This is not evidence that relocation solves independent error. Fixed and first-feasible policies selected the original pose in these four blocks.

| Shared block | Pool evaluation wall s | Full block wall s | Termination |
|---|---:|---:|---|
| `recovery_v1_proposed-20261023` | 32.45 | 78.62 | candidate_budget |
| `recovery_v1_proposed-20261024` | 30.08 | 76.47 | candidate_budget |
| `nominal_angled_torch_v1-20261023` | 11.59 | 77.46 | candidate_budget |
| `nominal_angled_torch_v1-20261024` | 10.99 | 98.00 | candidate_budget |

The paired policy experiment was recorded before the final unused MoveIt execution-route hardening attempt; its original runtime versions and logs remain authoritative for those measured comparisons, not final-release performance claims. Post-attempt nominal, robustness, core and browser regressions are separate. Per-policy isolated search timings, separate screen/planning timings, human manual times, MC complete-job rates, production reliability and statistical significance are **not measured/claimed**. The chart shows exclusive candidate counts in shared pools, not job probabilities or algorithm speedups. `analysis/evidence.json` documents population, derivations, missing fields and a direct cross-check.

## Failed attempts, fixes and unresolved teardown fault

- A legacy unit fixture changed only a Trial outcome while leaving a passing Plan. The stricter evidence contract correctly rejected this inconsistency. The fixture now supplies actual failed Check evidence; the initial failure log is preserved.
- The first real Phase 3 browser attempt found a long recorded scenario selector extending a 390 px viewport to 452 px. The selector is now width-bounded with an associated accessible label; the same actual workflow passes after the fix. The failing JSON/log/screenshot/audit remain preserved.
- An existing actual adapter test wrote its latest observation into the Phase 2 historical evidence location. The historic tracked bytes were restored from the untouched baseline, the Phase 3 observation retained separately, and the test now writes to Phase 3. Its targeted rerun verifies the change. Protected job/scenario definitions were never rewritten.

- **Unresolved MoveIt shutdown defect:** both the initial and final launch exit with MoveGroup signal 11 in `TrajectoryExecutionManager` / `rclcpp::CallbackGroup` destruction after the tests finish. Disabling the unused internal execution route (`allow_trajectory_execution=false`, live readback verified) did not prevent manager construction/destruction or fix the crash. Both traces and `shutdown-verification.json` are retained. Functional regressions passed with that route disabled; the final source comment only corrects the failed mitigation hypothesis. Direct exact-gated ros2_control execution remains unchanged. Directory names `post-teardown-fix` retain the original attempted experiment label, not proof of a fix.

## Resources and practical limits

Two CPUs, 4284 MiB RAM, no GPU/swap; Ubuntu rootfs approximately 5.1 GiB; about 17 GiB free at the measured checkpoint. One live RSS snapshot: Gazebo 232344 KiB, MoveGroup 93672 KiB, dashboard 236736 KiB. These are not process-tree totals or peaks. See `resources.json` for measured wall times and snapshot scope. Software-rendered UI and native GUI affect runtime. Large full candidate journals are retained; routine state polling uses summaries with explicit full-record inspection.

Each accepted recovery-v1 phase would need all 60 boundary executions and 400 seeded complete-job MC trials, with a separate final held-out evaluation. The existing bounded budget is not silently increased; a candidate lacking time/evidence stays unknown. The current hard boundary failures already prevent qualification independent of that resource limitation. Single-scene writers are serialized; concurrent controllers/dashboards/tests may corrupt assumptions and are unsupported.

## Delivery, modified files and launch

Source changes: `weldx/{validation,robustness,engine,server}.py`; `robotics/{adapter,uncertain_execution,model_view,benchmark,nominal_suite,policy_benchmark}.py`; dashboard HTML/CSS/JS; labelled core/API/actual robot tests; preregistered paired protocol; analysis/browser scripts; Phase 3 docs/evidence and current-document pointers. `modified-files.txt` and the publication manifest enumerate exact paths. Unrelated pre-existing screenshots and historical protected benchmarks remain preserved. Remote writes target only the engineering branch; no workflow publication, CI run or main merge is claimed.

Launch simulation and dashboard using the two commands in [the runbook](runbook.md). Do not interpret the default unavailable adapter as a working robot, or a nominal harness as authorized robust execution. The delivery archive includes raw full journals, source robot assets and screenshots; GitHub carries small records and lossless compressed copies with hashes.

## Remaining blockers / highest-priority engineering actions

1. **Unresolved dependency teardown:** investigate the recorded MoveIt/rclcpp destructor ownership fault using a pinned debug build/upstream-supported fix. No clean-shutdown acceptance is claimed.
2. **Engineering decision:** retain honest open-loop no-solution, or explicitly authorize a separately versioned measurement/registration study with defensible declared sensor-residual assumptions. Do not relabel simulation truth as a real measurement device.
3. If authorized, implement the actual supported compensation contract and re-run every mandatory boundary and the entire predefined MC/held-out experiment. Until then no robust placement or successful approved recovery exists.
4. Only after an admissible candidate qualifies, obtain explicit engineer approval of its exact candidate/job/config version and demonstrate Apply → fresh exact Revalidate → complete observed Execute. No unit double or nominal harness can satisfy this gate.
5. Conduct a real human manual engineering baseline and independently instrument per-policy runtime/compute stages before comparative speed or productivity claims. Current shared-pool selection comparison is useful but narrower.
6. ABB physical model calibration, broader model mismatch, continuous collision proof, measured minimum clearances/singularity conditioning and industrial certification remain outside demonstrated evidence. Virtual-only; no physical robot actuation or welding is supported.

**Final acceptance remains NOT COMPLETE.** The delivered negative workflow and integrity improvements are verified; the success-path commissioning gate is deliberately not bypassed.

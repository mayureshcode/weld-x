# Decisions, limitations and next engineering actions

| ID | Decision / status | Rationale or remaining work |
|---|---|---|
| D01 | Preserve main; dedicated engineering branch | Existing checkpoint and unrelated work retained; no merge claimed |
| D02 | Project-local Ubuntu fallback verified | Native host is Amazon Linux; actual sudo/mount capabilities enabled the supported target userspace after the earlier audit missed them |
| D03 | ABB IRB120 retained, physical fidelity provisional | Source kinematics/meshes and actual Jazzy/Harmonic movement verified; manufacturer dynamics and complete collision-exclusion justification are not |
| D04 | No mock success adapter in production | Actual ROS selected explicitly; missing runtime defaults to unknown/blocked |
| D05 | Strict job unchanged | Independent ±2 mm fixture error cannot be compensated by base placement for a 1 mm open-loop TCP requirement |
| D06 | Recovery v1 uses authorized proposed ±0.5 mm translations | Separate version, unchanged TCP tolerance; yaw and model mismatch retained; seeds/scenarios frozen before evaluation |
| D07 | Recovery v1 rejected | Twenty of sixty boundary screens violate commanded-path constraints. Zero benchmark MC execution successes are claimed; no approval was fabricated |
| D08 | Add opposed-error corners before first recovery experiment | Same-sign corners alone missed large relative base/fixture translation; eight explicit opposed corners added, manifest records the pre-evaluation amendment |
| D09 | Tiny arithmetic boundary guard | Exactly equal 1 mm boundaries falsely failed due floating point; first report preserved, 1e-12 SI numerical comparison guard tested, no engineering limit changed |
| D10 | No physical measurement/compensation | A future calibrated registration/sensing design would be a material scope extension requiring evidence and approval; simulator truth is not that mechanism |
| R01 | Full successful approved recovery unverified | Needs an engineer-supported job/envelope or validated sensing mechanism that genuinely meets every mandatory boundary and complete-job MC gate |
| R02 | 99% empirical target not demonstrated | Declared 100 MC/source, separate seeds. Mandatory boundaries reject before acceptance, so MC rates are unavailable, not 99% |
| R03 | Model mismatch is restricted | TCP calibration transform only; not physical link, fixture compliance, thermal or dynamics mismatch |
| R04 | Discrete collision validation | No continuous path certificate or minimum-distance/singularity metric; introduce validated distance/conditioning instrumentation if required |
| R05 | Budget/resource limitations | Two CPUs/no GPU; GUI software rendering reduced observed RTF to roughly 0.35–0.45. Headless tests requested RTF 3; actual per-job wall times are recorded, not a guaranteed rate |
| R06 | Rootfs fallback is privileged, not secure isolation | Shared host networking/PIDs, private ephemeral mounts; trusted simulation only, no physical robot stack on the same domain |
| R07 | Concurrent writers unsupported | Serialize scene/motion tests and the commissioning workflow; separate journals are not a global simulator lock |
| R08 | CI and main merge unverified | Workflow-file publication permission was rejected previously; no successful CI or main merge is claimed |
| R09 | Recovery-loop real acceptance incomplete | Integrity/approval/retry unit tests exist; no qualifying candidate means no genuine approval/application/revalidation-success recovery demonstration |

Next priority: review the exact independent-error geometry and retained yaw/calibration terms with engineering evidence. Do not tune these after outcomes to force a demo. If specifications change legitimately, create recovery v2 with a new preregistration, preserve v1 rejection, rerun mandatory boundaries, and only then spend compute on full seeded Monte Carlo execution. A robot-base move alone must never be advertised as correcting an independent fixture offset.

Additional visualization limits: the 3D view shows actual observed joints, source meshes, live cell poses and declared seam geometry. It does not yet display the full planned trajectory or a source-specific uncertainty ghost. The sensitivity view is recorded source tables/diagnostics, not a completed statistical experiment comparison chart. These UI extensions are not claimed complete.

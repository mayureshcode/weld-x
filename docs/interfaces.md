> Current continuation: [Phase 3 report](phase3/final-report.md) and [Phase 3 runbook](phase3/runbook.md). Historical checkpoint text below is retained, not a current acceptance claim.

> Historical orchestration checkpoint document. For the current real robotics integration, measured results and remaining blockers, see [Phase 2](phase2/README.md).

# Interfaces and lifecycle

## HTTP

Bind `127.0.0.1`, default port 8765. No CORS. GET requires exact localhost/127.0.0.1 Host. POST additionally requires same Origin (if supplied) and the per-process `X-Weldx-Token` obtained from GET `/api/session`. Token protects local browser mutations, not user authentication. TLS/authentication/public deployment are outside this checkpoint.

| Route | Contract |
|---|---|
| GET /api/session | CSRF session token |
| GET /api/state | Configuration/hash/stage/health/candidates/audit/initial/final/execution/task |
| POST /api/detect | 202 background task; nominal + held-out evaluation |
| POST /api/search | 202 bounded background search; observable evaluated records |
| POST /api/revalidate | 202 scene sync + exact final held-out revalidation |
| POST /api/execute | 202 queued attempt; backend still validates authorization before execution |
| POST /api/cancel | 202 cooperative cancellation request, audit recorded |
| POST /api/approve | candidate_id, config_hash, engineer; exact-version approval |
| POST /api/apply | approval_id; consumes approval and returns updated declarative config |

GET `/api/state` task status is `running`, `finished`, `cancelled` or `failed`, with explicit error. 202 never means successful validation or robot execution. One long operation at a time. Frontend polls every 1.5s; fetch failures visibly lock controls. Cancellation reaches the currently running operation via an Event.

Errors: 400 malformed/missing input; 403 host/origin/token; 404 route; 409 rejected state/approval/concurrent operation; 413 body >16KiB. Background errors appear in task state and the audit rather than retroactively changing the 202 response. Audit persistence errors are not silently downgraded; journal health faults revoke execution authorization. State/audit pagination and large histories require future hardening.

## Trusted robotics adapter — interface only, production implementation absent

- `version: str`: digest/version identifying exact robot assets, solver and controller/scene interfaces.
- `ready: bool`: real current health; disconnect must revoke readiness.
- `health() -> dict`: actually measured instrument status; never fabricated heartbeat data.
- `synchronize(config, cancel, deadline) -> hash | None`: acknowledge both planning scene and simulator exact configuration. UNKNOWN/failed sync cannot authorize execution.
- `validate(config, scenario, cancel, deadline) -> Plan`: complete job plan and every segment/gate Check. Apply scenario perturbations to robot/fixture/model consistently; restore nominal state safely. Plan stores config hash, adapter version, checks, actual trajectory identity.
- `execute(config, plan, cancel, deadline) -> Execution`: run validated nominal trajectory through intended controller; observe full ordered segments, tracking error, failure/cancellation and exact trajectory/config hashes.

The adapter is trusted backend code, never user-submitted JSON. Test doubles are not loadable by server flags/API. A real implementation must verify substantive gate semantics, capture planning/execution measurements, reject stale scene state and implement bounded calls.

## Planned ROS contracts — NOT implemented

Configuration synchronization and scene acknowledgment; complete-job validation/planning action; execution action using FollowJointTrajectory through ros2_control; health/joint-state subscriptions; cooperative cancellation. Exact package/message names, launch files and MoveIt APIs must be chosen after inspection of the installed Jazzy stack. No fictitious ROS launch or service name is advertised as available.

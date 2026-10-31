# Dashboard refinement checkpoint

The console remains a **virtual-only engineering demonstrator**. These changes are UX and data-presentation improvements, not a ROS/Gazebo/MoveIt adapter.

## What changed
- At-a-glance runtime, nominal-check status, evaluated candidate count, and job identity cards.
- Next-action guidance and stronger distinction between execution authorization and background task status.
- Top-down placement plot from actual returned backend x/y values and declared search bounds. There is **no fabricated reachability surface**, no 3D robot motion, and no invented placement feasibility.
- Candidate and diagnostic filters, inspected candidate details, and collapsible raw evidence.
- Copyable configuration SHA-256, keyboard-accessible candidate points, skip navigation, and compact mobile layout.
- Existing POST routes, CSRF header, backend authorization logic, and fail-closed disconnect behavior remain in control.

## Verification
- Confirmed the updated dashboard JavaScript parses successfully.
- A separate local visual-preview package was browser smoke-tested at 1440 px and 390 px with a fixed API-shape fixture, no JavaScript errors, no horizontal overflow, and execution disabled. **This is not a tested run of the exact GitHub UI revisions or real backend.**
- Runtime backend integration, original `tests/browser.cjs` regressions, Blender rendering, ROS 2, Gazebo, MoveIt 2, actual welding jobs, and simulator behavior **remain unverified in this environment**.

## Recommended release gate
On Ubuntu with a fresh server, run:

```bash
python -m unittest discover -v
python -m compileall -q weldx tests
node --check dashboard/app.js
python -m weldx.server --config examples/job_01.json --audit .runtime/ui-check.jsonl
# in a separate terminal with Playwright installed:
WELDX_CHROMIUM="$(command -v chromium)" node tests/browser.cjs
```

Review screenshots and follow the runtime evidence ledger in `docs/status.md`. Never treat candidate plotted coordinates as a collision-checked robot mounting result without actual adapter validation.

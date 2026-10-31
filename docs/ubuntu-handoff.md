# WELD-X — Ubuntu 24.04 handoff

## Fetch the development branch

```bash
git clone --branch feat/weldx-workcell-visual-enhancement --single-branch https://github.com/mayureshcode/weld-x.git
cd weld-x
bash scripts/ubuntu_setup.sh
```

For an existing `weld-x` checkout:

```bash
git fetch origin feat/weldx-workcell-visual-enhancement
git switch -c feat/weldx-workcell-visual-enhancement --track origin/feat/weldx-workcell-visual-enhancement
bash scripts/ubuntu_setup.sh
```

If a local branch already exists, `git switch feat/weldx-workcell-visual-enhancement && git pull --ff-only` instead.

## Obtain original GLB

Place `demo_robotic_welding_workcell.glb` in `assets/source/`. It was supplied in ChatGPT and is **not stored in this GitHub repository yet**. Validate:

```bash
sha256sum assets/source/demo_robotic_welding_workcell.glb
# expected 582e97563443be6e3fae4880a72d5442510ebccb8f3b379a2e745b521c23185f
```

To publish the 34 MB binary yourself from Ubuntu (requires GitHub permissions and git-lfs):

```bash
sudo apt update
sudo apt install git-lfs
git lfs install
git add .gitattributes assets/source/demo_robotic_welding_workcell.glb
git commit -m "Track source robotic welding GLB asset with Git LFS"
git push origin feat/weldx-workcell-visual-enhancement
```

This prevents committing an uncompressed binary into ordinary Git history. `git lfs pull` fetches asset bytes on another Ubuntu computer.

## Run UI

```bash
source .venv/bin/activate
python -m weldx.server --config examples/job_01.json --audit .runtime/audit.jsonl
```

Open http://127.0.0.1:8765. The dashboard will correctly show execution LOCKED until a real trusted ROS/Gazebo/MoveIt adapter is implemented, validated, and connected. No fake animation or controller authorization is supplied.

## Create Blender workcell

Install Blender 4.x compatible with your OS:

```bash
mkdir -p outputs/previews
blender -b --python tools/enhance_workcell.py -- \
  --input assets/source/demo_robotic_welding_workcell.glb \
  --output outputs/WELDX_Industrial_Cell_V1.blend \
  --render-dir outputs/previews
```

This generates a **presentation enhancement**, not a calibrated digital twin. The script preserves the imported transforms and places optional seam/base markers only when verified anchors are supplied. Inspect output in Blender and confirm scene units. Any claimed robot-base recommendation must come from actual validated MoveIt+Gazebo evidence.

## Tests before merging to main

```bash
python -m unittest discover -v
python -m compileall -q weldx tests
node --check dashboard/app.js
# optional browser tests, requires Playwright/Chromium:
WELDX_CHROMIUM="$(command -v chromium)" node tests/browser.cjs
```

Record screenshots and failures. Do not merge or call it commissioned until tests and physical-model verification pass.

**Current repository status:** API, search, robustness orchestration and audit are implemented with unavailable production robotics adapter. A real ROS 2 Jazzy + Gazebo Harmonic + MoveIt 2 implementation remains a separate milestone.

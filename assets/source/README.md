# Source workcell asset

Expected file: `demo_robotic_welding_workcell.glb`

SHA-256: `582e97563443be6e3fae4880a72d5442510ebccb8f3b379a2e745b521c23185f`

Binary length: 35,390,404 bytes. glTF 2.0 binary, 181 mesh objects and 239 nodes.

The original file was supplied in ChatGPT. **The binary is not uploaded to this branch** because the connected GitHub write interface only accepts UTF-8 text. Do not treat the manifest as the mesh.

Copy the asset from your local backup/download to `assets/source/demo_robotic_welding_workcell.glb`. Verify its SHA-256 with `sha256sum`. When explicitly publishing the binary from Ubuntu, use Git LFS (already configured via `.gitattributes`).

Do not use generic GLB object names as reliable robot or fixture identifiers. The robot and scene transforms require verified anchors and metric scale before ROS/MoveIt integration.

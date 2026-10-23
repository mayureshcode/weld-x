#!/usr/bin/env python3
"""Fetch unchanged Apache-2.0 ABB assets from an immutable upstream commit.
Existing files must match their pinned hash; unknown local edits are not replaced.
"""
import hashlib,json,urllib.request
from pathlib import Path
root=Path(__file__).resolve().parent.parent
pin='45f4769d826cf3ac62a65495f2db67b78b0c81df'
manifest=json.loads((root/'third_party/abb/mesh-sha256.json').read_text())
base=root/'ros_ws/src/weldx_description/meshes/irb120_3_58'
for relative,expected in manifest.items():
    path=base/relative
    if path.exists():
        if hashlib.sha256(path.read_bytes()).hexdigest()!=expected:raise SystemExit('Preserving modified asset; hash mismatch: '+str(path))
        print('verified',relative);continue
    url=f'https://raw.githubusercontent.com/ros-industrial/abb/{pin}/abb_irb120_support/meshes/irb120_3_58/{relative}'
    with urllib.request.urlopen(url,timeout=30) as response:data=response.read(20000000)
    if hashlib.sha256(data).hexdigest()!=expected:raise SystemExit('Downloaded asset hash mismatch: '+relative)
    path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_suffix('.download');tmp.write_bytes(data);tmp.replace(path);print('downloaded and verified',relative)

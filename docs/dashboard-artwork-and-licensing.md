# Dashboard asset provenance — WELD-X VNext

## Three.js GLB loaders

`GLTFLoader.js` and `BufferGeometryUtils.js` originate from the **Three.js r160**
examples tree, authored by the Three.js contributors, under the MIT License.

Source: `https://github.com/mrdoob/three.js/tree/r160/examples/jsm`

Changes are limited to local ESM imports (`./three.module.min.js` and
`./BufferGeometryUtils.js`) to work with the existing self-hosted Three.js
r160 vendor module and the dashboard's strict same-origin CSP.

MIT notice (the library's original copyright is retained):

The MIT License

Copyright © 2010–2023 three.js authors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE
USE OR OTHER DEALINGS IN THE SOFTWARE.

## Generated visual concept artwork

`dashboard/assets/weldx-hero.webp` is a locally bundled, AI-generated
illustrative concept image created for WELD-X VNext; it depicts an industrial
welding cell visually inspired by the user's actual screenshot. The bundled
asset is a reduced WebP thumbnail for fast first-page loading. The dashboard
labels it **AI concept visual — not telemetry**.

It must **never** substitute for actual Gazebo rendering, camera evidence,
robot alignment, collision checks, or a successful simulation result.

## Interactive workcell model

`/assets/workcell-preview.glb` is *not* part of this repository or the
artwork. It is generated locally from the user's `WELD-X_final.glb` using
`tools/build_visual_preview.py`. In preview mode it includes the customized
robot as a static visual, removes the extra duplicate scene branch, and
disables misleading planned-path overlays. The native ROS model remains
separate until calibrated geometry/joint integration is complete.

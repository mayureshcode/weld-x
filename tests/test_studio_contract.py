"""Offline dashboard integration contract. No simulated execution is implied."""
from html.parser import HTMLParser
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
UI=ROOT/'dashboard'

class IdCollector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids=set()
        self.duplicate_ids=[]
    def handle_starttag(self, tag, attrs):
        attrs=dict(attrs)
        found=attrs.get('id')
        if found:
            if found in self.ids: self.duplicate_ids.append(found)
            self.ids.add(found)

class StudioContractTests(unittest.TestCase):
    def test_original_backend_controls_and_new_viewer_all_exist(self):
        document=(UI/'index.html').read_text()
        parser=IdCollector();parser.feed(document)
        required={
            'connection','authorization','authreason','version','runtime-title','runtime-notice',
            'cell-view','scene-status','seam-select','show-planned','scene-evidence-status',
            'detect','search','revalidate','execute','cancel','task','error','stage',
            'configuration','hash','count','placement-map','map-yaw','map-status',
            'candidates','candidate-detail','comparison','approval-form','approve',
            'apply','engineer','source-select','scenario-select','source-detail',
            'sensitivity','diagnostic-summary','diagnostics','health','audit',
            'view-mode','runtime-led','view-accuracy','inspector-source','joint-data',
            'inspector-note','inspector-job','inspector-stage','view-home','view-top',
            'view-side','view-robot','view-focus'
        }
        self.assertFalse(parser.duplicate_ids)
        self.assertFalse(required-parser.ids, f"Missing controls: {required-parser.ids}")
        self.assertIn('AI CONCEPT VISUAL · NOT TELEMETRY',document)

    def test_static_preview_cannot_masquerade_as_live_robot(self):
        src=(UI/'scene.js').read_text()
        inspector=(UI/'app.js').read_text()
        self.assertIn('glb-preview',src)
        self.assertIn('live-urdf',src)
        self.assertIn('WELDX_ROBOT_ROOT',src)
        self.assertIn('SOURCE GLB · NOT JOINT SYNCHRONIZED',src)
        self.assertIn('if(!fresh) return;',src)
        self.assertIn("t.live===true",inspector)
        self.assertIn("weldxViewerMode==='live-urdf'",inspector)
        self.assertIn("value.textContent='—'",inspector)
        self.assertIn("button.disabled=true",inspector)
        self.assertIn("for(const id of ['detect','search','revalidate','execute','cancel','approve','apply'])",inspector)

    def test_local_asset_only_and_viewer_mode_wired_to_launcher(self):
        server=(ROOT/'weldx/server.py').read_text()
        launch=(ROOT/'scripts/start_weldx.sh').read_text()
        loader=(UI/'vendor/GLTFLoader.js').read_text()
        self.assertIn('"/assets/workcell-preview.glb"',server)
        self.assertIn('"/assets/weldx-hero.webp"',server)
        self.assertIn('"/api/viewer-meta"',server)
        self.assertIn('WELDX_VIEW_MODE=glb-preview',launch)
        self.assertIn('WELDX_VIEW_MODE=live-urdf',launch)
        self.assertIn("from './three.module.min.js'",loader)
        self.assertTrue((UI/'assets/weldx-hero.webp').read_bytes().startswith(b'RIFF'))
        self.assertTrue((UI/'vendor/BufferGeometryUtils.js').is_file())

if __name__=='__main__': unittest.main()

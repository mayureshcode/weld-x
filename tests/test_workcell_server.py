"""HTTP and static workcell/telemetry integration without claiming ROS simulation."""
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
from http.server import ThreadingHTTPServer
from urllib.request import urlopen, Request
from urllib.error import HTTPError

from weldx.engine import Engine, Journal
from weldx.server import App, handler
from .support import configuration


class WorkcellServerTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)
        self.glb=self.root/"cell.glb"
        self.glb.write_bytes(b"glTF"+b"\x00"*60)
        self.telemetry=self.root/"telemetry.json"
        self.app=App(Engine(configuration(),Journal(self.root/"audit.jsonl")),
                     workcell=self.glb,telemetry=self.telemetry)
        self.server=ThreadingHTTPServer(("127.0.0.1",0),handler(self.app))
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True)
        self.thread.start()
        self.base=f"http://127.0.0.1:{self.server.server_port}"
    def tearDown(self):
        self.server.shutdown();self.server.server_close();self.thread.join()
        self.app.pool.shutdown(wait=True)
        self.tmp.cleanup()
    def request(self,path):
        try:
            with urlopen(self.base+path,timeout=3) as r:
                return r.status,r.read(),r.headers
        except HTTPError as e:
            return e.code,e.read(),e.headers
    def test_binary_is_exact_source_and_not_executable(self):
        status,body,headers=self.request("/assets/workcell.glb")
        self.assertEqual(status,200)
        self.assertEqual(body,self.glb.read_bytes())
        self.assertEqual(headers["Content-Type"],"model/gltf-binary")
        self.assertFalse(self.app.engine.authorized())
    def test_missing_asset_fails_explicitly(self):
        self.glb.unlink()
        self.assertEqual(self.request("/assets/workcell.glb")[0],404)
    def test_telemetry_stale_and_fresh(self):
        status,body,_=self.request("/api/telemetry")
        self.assertFalse(json.loads(body)["connected"])
        self.telemetry.write_text(json.dumps({"received":True,"joints":[{"name":"joint_1","position":0.5}],"tf_count":2}))
        data=json.loads(self.request("/api/telemetry")[1])
        self.assertTrue(data["connected"]);self.assertEqual(data["joint_count"],1)
        old=time.time()-10
        import os
        os.utime(self.telemetry,(old,old))
        data=json.loads(self.request("/api/telemetry")[1])
        self.assertFalse(data["connected"])
        self.assertFalse(self.app.engine.authorized())
    def test_module_path_rejects_traversal(self):
        for path in ("/vendor/three/../../weldx/server.py","/vendor/three/examples/jsm/../secret.txt"):
            self.assertEqual(self.request(path)[0],404)
    def test_html_and_viewer_module_available(self):
        self.assertEqual(self.request("/")[0],200)
        self.assertEqual(self.request("/workcell.js")[0],200)
        self.assertIn(b"workcell-canvas",self.request("/")[1])
    def test_backend_safety_unchanged(self):
        self.assertFalse(json.loads(self.request("/api/state")[1])["authorized"])


if __name__=="__main__":
    unittest.main()

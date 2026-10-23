import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from http.server import ThreadingHTTPServer
from weldx.engine import Engine, Journal
from weldx.server import App, handler
from .support import configuration

class APITests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.app=App(Engine(configuration(),Journal(Path(self.tmp.name)/'audit.jsonl')))
        self.server=ThreadingHTTPServer(('127.0.0.1',0),handler(self.app))
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.url=f'http://127.0.0.1:{self.server.server_port}'
    def tearDown(self):
        self.app.cancel.set();self.server.shutdown();self.server.server_close();self.thread.join();self.app.pool.shutdown(wait=True);self.tmp.cleanup()
    def request(self,path,data=None,token=True,headers=None):
        h=headers or {}
        if token:h['X-Weldx-Token']=self.app.token
        req=Request(self.url+path,data=None if data is None else json.dumps(data).encode(),headers=h)
        try:
            with urlopen(req,timeout=3) as res:return res.status,res.read()
        except HTTPError as exc:return exc.code,exc.read()
    def wait(self):
        self.app.future.result(timeout=5)
    def test_read_contract(self):
        status,body=self.request('/api/state');s=json.loads(body)
        self.assertEqual(status,200);self.assertFalse(s['authorized']);self.assertEqual(s['health']['gazebo'],'not_connected')
    def test_static_assets_and_missing_route(self):
        for path in ['/','/app.js','/style.css']:self.assertEqual(self.request(path)[0],200)
        self.assertEqual(self.request('/../weldx/engine.py')[0],404)
    def test_csrf_required(self):
        self.assertEqual(self.request('/api/detect',{},token=False)[0],403)
    def test_foreign_origin_and_host_rejected(self):
        self.assertEqual(self.request('/api/detect',{},headers={'Origin':'https://evil.invalid'})[0],403)
        self.assertEqual(self.request('/api/state',headers={'Host':'evil.invalid'})[0],403)
    def test_detect_and_search_real_unavailable_adapter(self):
        self.assertEqual(self.request('/api/detect',{})[0],202);self.wait()
        self.assertEqual(self.request('/api/search',{})[0],202);self.wait()
        s=self.app.engine.snapshot();self.assertTrue(s['candidates']);self.assertFalse(s['authorized'])
        self.assertTrue(all(c['classification']=='validation_incomplete' for c in s['candidates']))
        self.assertIsNone(s['recommended'])
    def test_summary_does_not_replace_authoritative_evidence(self):
        from .support import TestAdapter
        self.app.engine.adapter = TestAdapter()  # Isolated serialization contract, not robotics evidence.
        self.request('/api/detect',{});self.wait()
        self.request('/api/search',{});self.wait()
        status,raw=self.request('/api/state');state=json.loads(raw)
        self.assertEqual(status,200)
        candidate=state['candidates'][0]
        trials=candidate['evidence']['evaluation']['robustness']['trials']
        self.assertTrue(trials)
        self.assertIn('summary_checks',trials[0]);self.assertNotIn('plan',trials[0])
        self.assertNotIn('payload',state['audit'][0])
        status,raw=self.request('/api/evidence?candidate_id='+candidate['id'])
        full=json.loads(raw);self.assertEqual(status,200)
        self.assertIn('plan',full['evaluation']['robustness']['trials'][0])
        status,raw=self.request('/api/audit?sequence=1')
        self.assertEqual(status,200);self.assertIn('payload',json.loads(raw))
        self.assertFalse(self.app.engine.authorized())
    def test_evidence_route_is_allowlisted(self):
        for path,status in [('/api/evidence',400),('/api/audit?sequence=bad',400),
                            ('/api/audit?sequence=999999',404),('/api/evidence?candidate_id=missing',404),
                            ('/api/evidence?candidate_id=a&candidate_id=b',400)]:
            self.assertEqual(self.request(path)[0],status)
        self.assertEqual(self.request('/api/audit?sequence=1',headers={'Host':'evil.invalid'})[0],403)
    def test_execution_fails_asynchronously(self):
        self.assertEqual(self.request('/api/execute',{})[0],202);self.wait()
        self.assertEqual(self.app.task['status'],'failed');self.assertIn('execution denied',self.app.task['error'])
    def test_approval_missing_and_invalid_input(self):
        self.assertEqual(self.request('/api/approve',{})[0],400)
        self.assertEqual(self.request('/api/approve',{'candidate_id':'x','config_hash':'x','engineer':'E'})[0],409)
    def test_revalidate_unknown_then_cancel_records(self):
        self.assertEqual(self.request('/api/revalidate',{})[0],202);self.wait()
        self.assertFalse(self.app.engine.authorized());self.assertEqual(self.app.engine.stage,'STOPPED')
        self.assertEqual(self.request('/api/cancel',{})[0],202)
        self.assertEqual(self.app.engine.journal.events[-1]['kind'],'cancel_requested')

if __name__=='__main__':unittest.main()

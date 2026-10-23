"""Loopback-only inspection API. No shell endpoint, physical control or demo mode."""
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import argparse
import json
from pathlib import Path
import secrets
import threading
from .engine import Denied, Engine, Journal, serial
from .model import Configuration

class App:
    def __init__(self, engine):
        self.engine = engine
        self.token = secrets.token_urlsafe(32)
        self.pool = ThreadPoolExecutor(max_workers=1)
        self.cancel = threading.Event()
        self.future = None
        self.task_lock = threading.Lock()
        self.task = None
    def submit(self, operation):
        with self.task_lock:
            if self.future and not self.future.done():
                raise Denied("another background task is running")
            self.cancel = threading.Event()
            self.task = {"operation": operation, "status": "running", "error": None}
            def run():
                try:
                    getattr(self.engine, operation)(self.cancel)
                    self.task["status"] = "cancelled" if self.cancel.is_set() else "finished"
                except Exception as exc:
                    self.task.update(status="failed", error=f"{type(exc).__name__}: {exc}")
                    self.engine._event("task_failed", dict(self.task))
            self.future = self.pool.submit(run)
            return dict(self.task)

def handler(app):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            # HTTP access logs remain visible to the local operator.
            super().log_message(fmt, *args)
        def respond(self, status, body, content_type="application/json"):
            data = body.encode() if isinstance(body, str) else json.dumps(serial(body), allow_nan=False).encode()
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; frame-ancestors 'none'; base-uri 'none'")
            self.end_headers()
            self.wfile.write(data)
        def local(self):
            host = self.headers.get("Host", "")
            return host in {f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"}
        def do_GET(self):
            if not self.local():
                return self.respond(403, {"error": "loopback Host required"})
            if self.path == "/api/session":
                return self.respond(200, {"csrf_token": app.token})
            if self.path == "/api/state":
                return self.respond(200, {**app.engine.snapshot(), "task": app.task})
            assets = {"/": ("index.html", "text/html"), "/app.js": ("app.js", "application/javascript"), "/style.css": ("style.css", "text/css")}
            if self.path in assets:
                filename, mime = assets[self.path]
                return self.respond(200, (Path(__file__).resolve().parent.parent/"dashboard"/filename).read_text(), mime)
            return self.respond(404, {"error": "not found"})
        def do_POST(self):
            origin = self.headers.get("Origin")
            allowed = {f"http://127.0.0.1:{self.server.server_port}", f"http://localhost:{self.server.server_port}"}
            if not self.local() or (origin and origin not in allowed) or not secrets.compare_digest(self.headers.get("X-Weldx-Token", ""), app.token):
                return self.respond(403, {"error": "same-origin session token required"})
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 <= length <= 16384:
                    return self.respond(413, {"error": "request too large"})
                body = json.loads(self.rfile.read(length) or b"{}")
                if self.path in ("/api/detect", "/api/search", "/api/revalidate", "/api/execute"):
                    return self.respond(202, app.submit(self.path.rsplit("/", 1)[-1]))
                if self.path == "/api/cancel":
                    app.cancel.set()
                    app.engine._event("cancel_requested", {"task": app.task})
                    return self.respond(202, {"cancel_requested": True, "note": "cooperative cancellation; not an industrial safety stop"})
                if self.path == "/api/approve":
                    return self.respond(200, app.engine.approve(body["candidate_id"], body["config_hash"], body["engineer"]))
                if self.path == "/api/apply":
                    return self.respond(200, app.engine.apply(body["approval_id"]).model_dump(mode="json"))
                return self.respond(404, {"error": "not found"})
            except Denied as exc:
                app.engine._event("request_rejected", {"path": self.path, "reason": str(exc)})
                return self.respond(409, {"error": str(exc)})
            except (ValueError, KeyError, TypeError) as exc:
                return self.respond(400, {"error": str(exc)})
    return Handler

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="examples/job_01.json")
    parser.add_argument("--audit", default=".runtime/audit.jsonl")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    import fcntl
    lock_path = Path(args.audit+".lock")
    lock_path.parent.mkdir(parents=True,exist_ok=True)
    process_lock = lock_path.open("a")
    try:
        fcntl.flock(process_lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError:
        raise SystemExit("another server owns this audit journal; choose a separate audit path")
    config = Configuration.model_validate_json(Path(args.config).read_text())
    app = App(Engine(config, Journal(args.audit)))
    server = ThreadingHTTPServer(("127.0.0.1", args.port), handler(app))
    print(f"WELD-X http://127.0.0.1:{server.server_port} — robotics unavailable; execution blocked", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        app.cancel.set()
        server.server_close()
        app.pool.shutdown(wait=True)

if __name__ == "__main__":
    main()

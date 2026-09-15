"""Loopback-only user interface. Secrets are never MCP tool results."""
import json
import secrets
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from pocketport.storage import export_session, home, list_sessions, read_json, write_json


class Dashboard:
    def __init__(self, controller, port=8766):
        self.controller = controller
        self.token = secrets.token_urlsafe(32)
        dashboard = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def reply(self, value, status=200, ctype="application/json"):
                data = value if isinstance(value, bytes) else json.dumps(value, ensure_ascii=False).encode()
                self.send_response(status)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(data)))
                self.send_header("Cache-Control", "no-store")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.send_header("Referrer-Policy", "no-referrer")
                self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' blob:; frame-ancestors 'none'; connect-src 'self'")
                self.end_headers()
                self.wfile.write(data)

            def allowed(self, auth=True):
                host = f"127.0.0.1:{dashboard.server.server_port}"
                if self.headers.get("Host") != host:
                    self.reply({"error": "Invalid host"}, 403)
                    return False
                if self.headers.get("Origin") not in (None, "http://" + host):
                    self.reply({"error": "Invalid origin"}, 403)
                    return False
                if auth and not secrets.compare_digest(self.headers.get("Authorization", ""), "Bearer " + dashboard.token):
                    self.reply({"error": "Open POCKETPort from your agent or the desktop launcher"}, 401)
                    return False
                return True

            def do_GET(self):
                if not self.allowed(auth=self.path != "/"):
                    return
                if self.path == "/":
                    self.reply(Path(__file__).with_name("dashboard.html").read_bytes(), ctype="text/html; charset=utf-8")
                elif self.path == "/api/status":
                    self.reply(controller.status())
                elif self.path == "/api/sessions":
                    self.reply(list_sessions())
                elif self.path in ("/api/qr", "/api/config"):
                    if not controller.status()["running"]:
                        self.reply({"error": "Start collection first"}, 409)
                        return
                    path = home() / ("phone-qr.png" if self.path.endswith("qr") else "phone.conf")
                    self.reply(path.read_bytes(), ctype="image/png" if self.path.endswith("qr") else "text/plain")
                else:
                    self.reply({"error": "Not found"}, 404)

            def do_POST(self):
                if not self.allowed():
                    return
                try:
                    size = int(self.headers.get("Content-Length", 0))
                    if not 0 < size < 16384:
                        raise ValueError("Invalid request size")
                    args = json.loads(self.rfile.read(size))
                    if self.path == "/api/start":
                        result = controller.start(**args)
                    elif self.path == "/api/stop":
                        result = controller.stop()
                    elif self.path == "/api/export":
                        result = export_session(args["session"])
                        self.reply(Path(result["path"]).read_bytes())
                        return
                    else:
                        self.reply({"error": "Not found"}, 404)
                        return
                    self.reply(result)
                except (ValueError, TypeError, KeyError, OSError, RuntimeError) as exc:
                    self.reply({"error": str(exc)}, 400)

        self.server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
        self.server.daemon_threads = True
        # Binding is the single-instance guard; only recover old metadata after it succeeds.
        for meta in list_sessions():
            if meta["state"] == "running":
                meta.update(state="stopped", stop_reason="previous_app_interrupted")
                write_json(home() / "sessions" / meta["id"] / "session.json", meta)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def open(self):
        url = f"http://127.0.0.1:{self.server.server_port}/#{self.token}"
        opened = webbrowser.open(url)
        # Only the public, non-secret URL is returned to the agent.
        return {"opened": opened, "url": url.split("#")[0],
                "notice": "Pairing QR is displayed in the local browser only. If the browser did not open, use the desktop launcher."}

    def close(self):
        self.controller.stop(reason="app_closed")
        self.server.shutdown()
        self.server.server_close()

import asyncio
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from pocketport.controller import Controller
from pocketport.storage import read_json, write_json
from pocketport.web import Dashboard


def free_port(kind=socket.SOCK_STREAM):
    with socket.socket(socket.AF_INET, kind) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class RuntimeTests(unittest.TestCase):
    def test_dashboard_blocks_unauthenticated_and_cross_origin(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {"POCKETPORT_HOME": tmp}):
            dashboard = Dashboard(Controller(), port=0)
            url = f"http://127.0.0.1:{dashboard.server.server_port}"
            try:
                with urlopen(url) as r:
                    self.assertIn(b"POCKETPort", r.read())
                with self.assertRaises(HTTPError) as error:
                    urlopen(url + "/api/status")
                self.assertEqual(error.exception.code, 401)
                headers = {"Authorization": "Bearer " + dashboard.token}
                with urlopen(Request(url + "/api/status", headers=headers)) as r:
                    self.assertFalse(json.load(r)["running"])
                headers["Origin"] = "https://attacker.example"
                with self.assertRaises(HTTPError) as error:
                    urlopen(Request(url + "/api/status", headers=headers))
                self.assertEqual(error.exception.code, 403)
            finally:
                dashboard.close()

    def test_actual_proxy_records_synthetic_http_response(self):
        class Origin(BaseHTTPRequestHandler):
            def do_GET(self):
                body = b'{"orders":[{"id":"synthetic-123"}],"token":"DO-NOT-STORE"}'
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass

        with tempfile.TemporaryDirectory() as tmp:
            origin = ThreadingHTTPServer(("127.0.0.1", 0), Origin)
            threading.Thread(target=origin.serve_forever, daemon=True).start()
            port = free_port()
            folder = Path(tmp)
            write_json(folder / "session.json", {"source": "test", "hosts": ["127.0.0.1"]})
            env = dict(os.environ, POCKETPORT_SESSION=tmp)
            import importlib.util
            addon_path = importlib.util.find_spec("pocketport.addon").origin
            executable = Path(sys.executable).parent / ("mitmdump.exe" if os.name == "nt" else "mitmdump")
            proc = subprocess.Popen([str(executable), "--mode", f"regular@{port}", "--listen-host", "127.0.0.1",
                                     "--set", f"confdir={folder / 'ca'}", "-q", "-s", addon_path],
                                    env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            try:
                end = time.monotonic() + 15
                while not read_json(folder / "status.json", {}).get("ready"):
                    if proc.poll() is not None:
                        self.fail(proc.stderr.read().decode())
                    if time.monotonic() > end:
                        self.fail("proxy did not become ready")
                    time.sleep(.1)
                import httpx
                with httpx.Client(proxy=f"http://127.0.0.1:{port}", trust_env=False) as client:
                    response = client.get(f"http://127.0.0.1:{origin.server_port}/orders?token=DO-NOT-STORE")
                    self.assertEqual(response.status_code, 200)
                end = time.monotonic() + 5
                while not (folder / "records.jsonl").exists() and time.monotonic() < end:
                    time.sleep(.05)
                raw = (folder / "records.jsonl").read_text()
                self.assertIn("synthetic-123", raw)
                self.assertNotIn("DO-NOT-STORE", raw)
            finally:
                proc.terminate()
                try:
                    proc.communicate(timeout=10)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.communicate()
                origin.shutdown()
                origin.server_close()

    def test_mcp_stdio_and_actual_wireguard_lifecycle(self):
        async def exercise(tmp):
            from mcp import ClientSession, StdioServerParameters
            from mcp.client.stdio import stdio_client
            env = dict(os.environ, POCKETPORT_HOME=tmp)
            params = StdioServerParameters(command=sys.executable, args=["-m", "pocketport", "mcp"], env=env)
            async with stdio_client(params) as streams:
                async with ClientSession(*streams) as client:
                    await client.initialize()
                    names = {t.name for t in (await client.list_tools()).tools}
                    self.assertEqual(len(names), 7)
                    started = await client.call_tool("start_capture", {"source": "taobao", "endpoint": "192.168.1.20", "port": free_port(socket.SOCK_DGRAM), "minutes": 1})
                    self.assertFalse(started.isError, str(started))
                    value = json.loads(started.content[0].text)
                    self.assertTrue(value["running"])
                    self.assertTrue(value["capture"]["ready"])
                    self.assertNotIn("PrivateKey", str(started))
                    conf = (Path(tmp) / "phone.conf").read_text()
                    self.assertIn("Endpoint = 192.168.1.20:", conf)
                    self.assertTrue((Path(tmp) / "phone-qr.png").exists())
                    sid = value["session"]["id"]
                    stopped = await client.call_tool("stop_capture", {})
                    self.assertFalse(stopped.isError, str(stopped))
                    self.assertFalse(json.loads(stopped.content[0].text)["running"])
                    exported = await client.call_tool("export_collection", {"session": sid})
                    self.assertFalse(exported.isError, str(exported))
                    result = json.loads(exported.content[0].text)
                    self.assertEqual(result["records"], 0)
                    self.assertTrue(Path(result["path"]).exists())

        with tempfile.TemporaryDirectory() as tmp:
            asyncio.run(exercise(tmp))

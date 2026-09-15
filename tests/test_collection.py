import importlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from mitmproxy import http
from mitmproxy.test import tflow

from pocketport.filters import clean_url, normalize_host, redact, selected
from pocketport.storage import export_session, read_records, write_json


class CollectionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.sid = "a" * 32
        self.directory = Path(self.tmp.name) / "sessions" / self.sid
        self.directory.mkdir(parents=True)
        self.env = patch.dict(os.environ, {"POCKETPORT_HOME": self.tmp.name, "POCKETPORT_SESSION": str(self.directory)})
        self.env.start()
        write_json(self.directory / "session.json", {"id": self.sid, "source": "taobao", "hosts": ["taobao.com"], "state": "running"})
        addon = importlib.import_module("pocketport.addon")
        self.capture = addon.Capture()

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()

    def flow(self, host="api.taobao.com", payload=None, ctype="application/json"):
        flow = tflow.tflow(resp=True)
        flow.request = http.Request.make("POST", f"https://{host}/orders?token=SECRET&order=123", b"password=SECRET", {"Authorization": "Bearer SECRET"})
        flow.response = http.Response.make(200, json.dumps(payload or {"orders": [1], "accessToken": "SECRET"}).encode(), {"Content-Type": ctype, "Set-Cookie": "SECRET"})
        return flow

    def test_selected_boundary_and_ip(self):
        self.assertTrue(selected("api.taobao.com", ["taobao.com"]))
        self.assertFalse(selected("taobao.com.attacker.example", ["taobao.com"]))
        self.assertFalse(selected("eviltaobao.com", ["taobao.com"]))
        self.assertFalse(selected("sub.192.0.2.1", ["192.0.2.1"]))
        self.assertEqual(normalize_host(" API.EXAMPLE.COM. "), "api.example.com")
        for host in ["https://example.com", "*.example.com", "a..com", "example.com:443", "-a.com"]:
            with self.assertRaises(ValueError):
                normalize_host(host)

    def test_response_capture_minimises_credentials(self):
        self.capture.response(self.flow())
        raw = (self.directory / "records.jsonl").read_text()
        self.assertNotIn("SECRET", raw)
        record = json.loads(raw)
        self.assertEqual(record["response_body"]["orders"], [1])
        self.assertEqual(record["response_body"]["accessToken"], "[REDACTED]")
        self.assertNotIn("request_headers", record)
        self.assertEqual(read_records(self.sid)["next_offset"], 1)

    def test_unrelated_and_non_json_never_persist(self):
        self.capture.response(self.flow(host="taobao.com.attacker.example"))
        self.capture.response(self.flow(ctype="text/html"))
        flow = self.flow()
        flow.response.content = b"not json SECRET"
        self.capture.response(flow)
        self.assertFalse((self.directory / "records.jsonl").exists())

    def test_jsonp_and_nested_secrets(self):
        flow = self.flow(ctype="application/javascript")
        flow.response.content = b'callback({"data":"{\\"token\\":\\"SECRET\\"}","url":"https://example.com/a?q=SECRET"});'
        self.capture.response(flow)
        raw = (self.directory / "records.jsonl").read_text()
        self.assertNotIn("SECRET", raw)
        self.assertEqual(self.capture.stats["saved"], 1)

    def test_export_stop_required_and_partial_tail(self):
        self.capture.response(self.flow())
        with self.assertRaises(ValueError):
            export_session(self.sid)
        with (self.directory / "records.jsonl").open("a") as f:
            f.write('{"unfinished":')
        self.assertEqual(len(read_records(self.sid)["records"]), 1)
        write_json(self.directory / "session.json", {"state": "stopped"})
        result = export_session(self.sid)
        self.assertEqual(result["records"], 1)
        self.assertEqual(len(json.loads(Path(result["path"]).read_text())["records"]), 1)

    def test_limit_and_omission(self):
        flow = self.flow()
        flow.response.raw_content = None
        self.capture.response(flow)
        row = read_records(self.sid)["records"][0]
        self.assertIsNone(row["response_body"])
        self.assertEqual(row["omitted_reason"], "streamed_or_oversized")
        self.capture.stats["bytes"] = 100_000_000
        self.capture.response(self.flow())
        self.assertTrue(self.capture.stats["limit_reached"])
        self.assertEqual(self.capture.stats["saved"], 1)

    def test_path_and_page_bounds(self):
        for sid in ["../ca", "/etc/passwd", "bad"]:
            with self.assertRaises(ValueError):
                read_records(sid)
        for offset, limit in [(-1, 5), (0, 0), (0, 100)]:
            with self.assertRaises(ValueError):
                read_records(self.sid, offset, limit)

    def test_sni_and_target_ip_selection(self):
        from types import SimpleNamespace as S
        for host, ip, expected in [("api.taobao.com", "192.0.2.1", False), ("other.example", "192.0.2.1", True)]:
            data = S(client_hello=S(sni=host), context=S(server=S(address=(ip, 443))), ignore_connection=False)
            self.capture.tls_clienthello(data)
            self.assertEqual(data.ignore_connection, expected)


if __name__ == "__main__":
    unittest.main()

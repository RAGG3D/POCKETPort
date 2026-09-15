"""Loaded by mitmdump. Never logs payloads or authentication headers."""
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from pocketport.filters import clean_url, redact, selected
from pocketport.storage import read_json, write_json


class Capture:
    def __init__(self):
        self.directory = Path(os.environ["POCKETPORT_SESSION"])
        self.config = read_json(self.directory / "session.json")
        self.targets = self.config["hosts"]
        self.stats = {"saved": 0, "ignored": 0, "errors": 0, "tls_errors": 0,
                      "bytes": 0, "limit_reached": False, "ready": False}

    def flush(self):
        write_json(self.directory / "status.json", self.stats)

    def running(self):
        self.stats["ready"] = True
        self.flush()

    def tls_clienthello(self, data):
        sni = data.client_hello.sni or ""
        address = data.context.server.address
        host = address[0] if address else ""
        data.ignore_connection = not (selected(sni, self.targets) or selected(host, self.targets) or sni == "mitm.it")

    def tls_failed_client(self, data):
        self.stats["tls_errors"] += 1
        self.flush()

    def error(self, flow):
        if selected(flow.request.pretty_host, self.targets):
            self.stats["errors"] += 1
            self.flush()

    def responseheaders(self, flow):
        # Never buffer unlimited downloads, including compressed responses.
        ctype = flow.response.headers.get("content-type", "").lower()
        if not selected(flow.request.pretty_host, self.targets) or not self.is_json(ctype):
            flow.response.stream = True
            return
        size = flow.response.headers.get("content-length", "")
        if size.isdigit() and int(size) > 1_000_000:
            flow.response.stream = True

    @staticmethod
    def is_json(ctype):
        return "json" in ctype or "text/plain" in ctype or "javascript" in ctype

    def response(self, flow):
        if not selected(flow.request.pretty_host, self.targets):
            return
        if self.stats["limit_reached"]:
            return
        ctype = flow.response.headers.get("content-type", "").lower()
        if not self.is_json(ctype):
            self.stats["ignored"] += 1
            self.flush()
            return
        body, omitted = None, None
        raw = flow.response.raw_content
        if raw is None:
            omitted = "streamed_or_oversized"
        elif len(raw) > 1_000_000:
            omitted = "oversized"
        else:
            try:
                text = flow.response.get_text(strict=False) or ""
                if len(text) > 1_000_000:
                    omitted = "oversized_decoded"
                else:
                    # JSONP wrappers from MTOP are accepted, scripts and HTML aren't persisted.
                    text = text.strip()
                    if not text.startswith(("{", "[")) and "(" in text and text.rstrip(";").endswith(")"):
                        text = text[text.index("(") + 1:text.rfind(")")]
                    body = redact(json.loads(text))
            except (ValueError, RecursionError):
                self.stats["ignored"] += 1
                self.flush()
                return
        rec = {"schema_version": 1, "captured_at": datetime.now(timezone.utc).isoformat(),
               "source": self.config["source"], "host": flow.request.pretty_host,
               "method": flow.request.method, "url": clean_url(flow.request.pretty_url),
               "status": flow.response.status_code, "content_type": ctype,
               "response_body": body, "omitted_reason": omitted}
        line = (json.dumps(rec, ensure_ascii=False) + "\n").encode("utf-8")
        if self.stats["bytes"] + len(line) > 100_000_000:
            self.stats["limit_reached"] = True
        else:
            fd = os.open(self.directory / "records.jsonl", os.O_APPEND | os.O_CREAT | os.O_WRONLY, 0o600)
            with os.fdopen(fd, "ab") as out:
                out.write(line)
            self.stats["bytes"] += len(line)
            self.stats["saved"] += 1
        self.flush()


addons = [Capture()]

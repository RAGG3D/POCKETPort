from __future__ import annotations

import io
import ipaddress
import os
import socket
import subprocess
import sys
import sysconfig
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from pocketport.filters import PRESETS, normalize_host
from pocketport.storage import home, read_json, write_json, write_private


def now():
    return datetime.now(timezone.utc).isoformat()


def suggested_ip():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("192.0.2.1", 80))  # route lookup only; no packet is sent
            return sock.getsockname()[0]
    except OSError:
        return ""


class Controller:
    def __init__(self):
        self.lock = threading.RLock()
        self.process = None
        self.session = None
        self.deadline = None
        self.timer = None

    def status(self):
        with self.lock:
            if self.process is not None and self.process.poll() is not None:
                self._finish("process_exited")
            meta = read_json(self.session / "session.json") if self.session else None
            return {"running": self.process is not None,
                    "session": meta,
                    "capture": read_json(self.session / "status.json", {}) if self.session else {},
                    "suggested_ip": suggested_ip(), "data_directory": str(home()),
                    "notice": "Zero saved responses does not establish that an account has no data."}

    def start(self, source: str, endpoint: str, extra_hosts: list[str] | None = None,
              port: int = 51820, minutes: int = 30):
        with self.lock:
            if self.status()["running"]:
                raise ValueError("A collection is running. Stop it before starting another.")
            if source not in PRESETS:
                raise ValueError("Unknown source")
            ip = ipaddress.ip_address(endpoint.strip())
            if ip.version != 4 or ip.is_loopback or ip.is_unspecified or ip.is_multicast or not ip.is_private:
                raise ValueError("Use the computer's private LAN IPv4 address reachable by your phone")
            if not 1024 <= port <= 65535 or not 1 <= minutes <= 120:
                raise ValueError("port must be 1024..65535; minutes must be 1..120")
            extra_hosts = extra_hosts or []
            if len(extra_hosts) > 30:
                raise ValueError("At most 30 additional hosts")
            hosts = sorted(set(PRESETS[source] + [normalize_host(h) for h in extra_hosts]))
            if not hosts:
                raise ValueError("Enter this WeChat mini-program's actual service domain or IP; there is no universal WeChat API host")
            # Early port collision check. The child's readiness remains authoritative.
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.bind(("0.0.0.0", port))
            sid = uuid.uuid4().hex
            self.session = home() / "sessions" / sid
            self.session.mkdir(parents=True, mode=0o700)
            self.deadline = time.time() + minutes * 60
            meta = {"id": sid, "source": source, "hosts": hosts, "started_at": now(),
                    "state": "running", "endpoint": str(ip), "port": port,
                    "duration_minutes": minutes,
                    "coverage": "Only observed JSON/JSONP responses; no completeness guarantee",
                    "credentials": "Request bodies and headers omitted; known response credential keys and all URL query values redacted"}
            write_json(self.session / "session.json", meta)
            try:
                self._prepare_pairing(str(ip), port)
                executable = Path(sysconfig.get_path("scripts")) / ("mitmdump.exe" if os.name == "nt" else "mitmdump")
                if not executable.exists():
                    raise RuntimeError("mitmdump missing; run the installer")
                env = os.environ.copy()
                env["POCKETPORT_SESSION"] = str(self.session)
                # Needed for editable installs and addon import from arbitrary working directories.
                env["PYTHONPATH"] = str(Path(__file__).resolve().parent.parent)
                args = [str(executable), "--mode", f"wireguard:{home() / 'wireguard-keys.json'}@{port}",
                        "--listen-host", "0.0.0.0", "-s", str(Path(__file__).with_name("addon.py")),
                        "--set", f"confdir={home() / 'ca'}", "--set", "termlog_verbosity=error",
                        "--set", "flow_detail=0", "--set", "stream_large_bodies=1m",
                        "--set", "body_size_limit=2m", "--set", "http3=false"]
                with (self.session / "engine.log").open("wb") as log:
                    self.process = subprocess.Popen(args, stdin=subprocess.DEVNULL, stdout=log, stderr=log,
                                                    env=env, cwd=str(home()),
                                                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
                end = time.monotonic() + 15
                while time.monotonic() < end:
                    if self.process.poll() is not None:
                        raise RuntimeError("Capture engine failed to start. Inspect the local engine.log; it is never returned to the agent.")
                    if read_json(self.session / "status.json", {}).get("ready"):
                        self.timer = threading.Timer(minutes * 60, self.stop, kwargs={"reason": "time_limit"})
                        self.timer.daemon = True
                        self.timer.start()
                        return self.status()
                    time.sleep(0.1)
                raise RuntimeError("Capture engine startup timed out")
            except Exception:
                self.stop(reason="startup_failed")
                raise

    def _prepare_pairing(self, endpoint, port):
        import mitmproxy_rs
        import qrcode
        from mitmproxy.certs import CertStore

        keys_path = home() / "wireguard-keys.json"
        keys = read_json(keys_path)
        if keys is None:
            keys = {"server_key": mitmproxy_rs.wireguard.genkey(), "client_key": mitmproxy_rs.wireguard.genkey()}
            write_json(keys_path, keys)
        certdir = home() / "ca"
        certdir.mkdir(exist_ok=True, mode=0o700)
        CertStore.from_store(certdir, "mitmproxy", 2048)
        conf = (f"[Interface]\nPrivateKey = {keys['client_key']}\nAddress = 10.0.0.1/32\n"
                f"DNS = 10.0.0.53\n\n[Peer]\nPublicKey = {mitmproxy_rs.wireguard.pubkey(keys['server_key'])}\n"
                f"AllowedIPs = 0.0.0.0/0\nEndpoint = {endpoint}:{port}\nPersistentKeepalive = 25\n")
        write_private(home() / "phone.conf", conf)
        out = io.BytesIO()
        qrcode.make(conf).save(out, format="PNG")
        write_private(home() / "phone-qr.png", out.getvalue())

    def _finish(self, reason):
        if self.timer:
            self.timer.cancel()
            self.timer = None
        if self.session:
            meta = read_json(self.session / "session.json")
            if meta["state"] == "running":
                meta.update(state="stopped", stopped_at=now(), stop_reason=reason)
                write_json(self.session / "session.json", meta)
        self.process = None

    def stop(self, reason="user_stopped"):
        with self.lock:
            if self.process and self.process.poll() is None:
                self.process.terminate()
                try:
                    self.process.wait(timeout=8)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait(timeout=5)
            self._finish(reason)
            return self.status()

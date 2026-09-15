"""Pure capture selection and credential minimisation, shared with tests."""
import ipaddress
import json
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

PRESETS = {
    "taobao": ["taobao.com", "tmall.com", "alicdn.com"],
    "xiaohongshu": ["xiaohongshu.com", "xhscdn.com"],
    "wechat-mini": [],
    "yihe": ["ejs56.com"],
}
SECRET = re.compile(r"token|password|passwd|secret|cookie|authorization|session|signature|shield|openid|unionid|^sign$|^sid$|^code$|^credential$|^x-mini", re.I)


def normalize_host(value: str) -> str:
    value = value.strip().lower().rstrip(".")
    try:
        return str(ipaddress.ip_address(value))
    except ValueError:
        value = value.encode("idna").decode("ascii")
        if len(value) > 253 or not re.fullmatch(r"[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?", value):
            raise ValueError("Enter domains or IP addresses only, without URL, port or wildcard")
        if "." not in value or any(not p or len(p) > 63 or p.startswith("-") or p.endswith("-") for p in value.split(".")):
            raise ValueError("Invalid domain")
        return value


def selected(host: str, targets: list[str]) -> bool:
    host = host.lower().rstrip(".")
    for target in targets:
        if host == target:
            return True
        try:
            ipaddress.ip_address(target)
        except ValueError:
            if host.endswith("." + target):
                return True
    return False


def redact(value, depth=0):
    if depth > 50:
        return "[DEPTH LIMIT]"
    if isinstance(value, dict):
        return {k: "[REDACTED]" if SECRET.search(k) else redact(v, depth + 1) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(v, depth + 1) for v in value]
    if isinstance(value, str):
        if value.startswith(("https://", "http://")):
            return clean_url(value)
        # Handle API envelopes that put another JSON document in a string.
        if value.lstrip().startswith(("{", "[")):
            try:
                return json.dumps(redact(json.loads(value), depth + 1), ensure_ascii=False)
            except (ValueError, RecursionError):
                pass
    return value


def clean_url(url: str) -> str:
    parts = urlsplit(url)
    # Query values can embed signed requests, cookies, account IDs or payloads.
    query = urlencode([(k, "[REDACTED]") for k, _ in parse_qsl(parts.query, keep_blank_values=True)])
    hostname = parts.hostname or ""
    if ":" in hostname:
        hostname = f"[{hostname}]"
    if parts.port:
        hostname += f":{parts.port}"
    return urlunsplit((parts.scheme, hostname, parts.path, query, ""))

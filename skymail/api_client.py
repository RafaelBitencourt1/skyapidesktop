import json
import threading
import time
from datetime import datetime
import requests

from .constants import CHANGE_LOG_FILE, DNS_LOG_FILE, _log_lock

def now_iso():
    return datetime.now().isoformat(timespec="milliseconds")


def normalize_row(row):
    clean = {}
    for k, v in row.items():
        if k is None:
            continue
        clean[k.lstrip("\ufeff").strip()] = (v or "").strip()
    return clean


def parse_kv_lines(text):
    data = {}
    for raw in (text or "").splitlines():
        line = raw.strip()
        if not line:
            continue
        if "=" not in line:
            continue
        k, v = line.split("=", 1)
        data[k.strip()] = v.strip()
    return data


class ApiClient:
    def __init__(self, token):
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"bearer {token}",
                "cache-control": "no-cache",
            }
        )

    def request(self, method, url, params=None, data=None, json=None, _max_retries=3):
        for attempt in range(_max_retries):
            resp = self.session.request(method=method, url=url, params=params, data=data, json=json, timeout=60)
            if resp.status_code in (429, 503) and attempt < _max_retries - 1:
                time.sleep(2 ** attempt)  # 1s, 2s, 4s
                continue
            return resp
        return resp


def write_change_log(mode, method, url, data, response, error=None):
    if method not in ("POST", "PUT", "DELETE"):
        return

    response_body = None
    status = ""
    success = False
    if response is not None:
        status = str(response.status_code)
        success = response.ok
        text = response.text or ""
        if len(text) > 1500:
            text = text[:1500]
        try:
            response_body = json.loads(text)
        except Exception:
            response_body = text or None

        # Detectar falha no corpo mesmo com HTTP 2xx
        if success and response_body is not None:
            _raw = (response.text or "").strip().lower()
            if response_body is False or response_body == 0:
                success = False
            elif isinstance(response_body, dict):
                for _k in ("success", "ok", "result"):
                    if response_body.get(_k) is False:
                        success = False
                        break
            elif _raw in ("false", "0"):
                success = False

    entry = {
        "timestamp": now_iso(),
        "mode": mode,
        "method": method,
        "url": url,
        "status": status,
        "success": success,
        "body": data or {},
        "response": response_body,
        "error": error or "",
    }

    with _log_lock:
        try:
            existing = json.loads(CHANGE_LOG_FILE.read_text(encoding="utf-8")) if CHANGE_LOG_FILE.exists() else []
        except Exception:
            existing = []
        existing.append(entry)
        try:
            CHANGE_LOG_FILE.write_text(
                json.dumps(existing, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception:
            pass


def write_dns_log(mode, url, params, response, error=None):
    response_body = None
    status = ""
    success = False
    if response is not None:
        status = str(response.status_code)
        success = response.ok
        text = response.text or ""
        if len(text) > 1500:
            text = text[:1500]
        try:
            response_body = json.loads(text)
        except Exception:
            response_body = text or None

    entry = {
        "timestamp": now_iso(),
        "mode": mode,
        "method": "GET",
        "url": url,
        "params": params or {},
        "status": status,
        "success": success,
        "response": response_body,
        "error": error or "",
    }

    with _log_lock:
        try:
            existing = json.loads(DNS_LOG_FILE.read_text(encoding="utf-8")) if DNS_LOG_FILE.exists() else []
        except Exception:
            existing = []
        existing.append(entry)
        try:
            DNS_LOG_FILE.write_text(
                json.dumps(existing, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception:
            pass


def _apply_kv(target: dict, kv_str: str) -> None:
    """Aplica pares key=value separados por virgula ao dict target."""
    if not kv_str:
        return
    for pair in kv_str.split(","):
        pair = pair.strip()
        if "=" in pair:
            k, _, v = pair.partition("=")
            target[k.strip()] = v.strip()



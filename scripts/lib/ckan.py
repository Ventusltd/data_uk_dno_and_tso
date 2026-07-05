from __future__ import annotations

import json
import os
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CKANPortal:
    base_url: str
    api_key_env: str | None = None
    min_delay_seconds: float = 1.0

    @property
    def action_base(self) -> str:
        return self.base_url.rstrip("/") + "/api/3/action"


def _headers(api_key_env: str | None) -> dict[str, str]:
    headers = {"User-Agent": "globalgrid2050-data-fetcher/0.1"}
    if api_key_env:
        api_key = os.environ.get(api_key_env)
        if api_key:
            headers["Authorization"] = api_key
    return headers


def action_url(portal: CKANPortal, action: str, **params: str) -> str:
    query = urllib.parse.urlencode(params)
    return f"{portal.action_base}/{action}" + (f"?{query}" if query else "")


def get_action(portal: CKANPortal, action: str, **params: str) -> dict[str, Any]:
    url = action_url(portal, action, **params)
    req = urllib.request.Request(url, headers=_headers(portal.api_key_env))
    time.sleep(portal.min_delay_seconds)
    with urllib.request.urlopen(req, timeout=60) as response:
        body = response.read().decode("utf-8")
    return json.loads(body)

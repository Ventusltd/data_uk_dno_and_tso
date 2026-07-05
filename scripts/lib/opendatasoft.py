from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ODSPortal:
    base_url: str
    api_key_env: str | None = None

    @property
    def api_base(self) -> str:
        return self.base_url.rstrip("/") + "/api/explore/v2.1"


def _headers(api_key_env: str | None) -> dict[str, str]:
    headers = {"User-Agent": "globalgrid2050-data-fetcher/0.1"}
    if api_key_env:
        api_key = os.environ.get(api_key_env)
        if api_key:
            headers["Authorization"] = f"Apikey {api_key}"
    return headers


def get_json(url: str, headers: dict[str, str]) -> dict[str, Any]:
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=60) as response:
        body = response.read().decode("utf-8")
    return json.loads(body)


def list_datasets(portal: ODSPortal, limit: int = 100) -> dict[str, Any]:
    query = urllib.parse.urlencode({"limit": str(limit)})
    url = f"{portal.api_base}/catalog/datasets?{query}"
    return get_json(url, _headers(portal.api_key_env))


def records_url(portal: ODSPortal, dataset_id: str, *, limit: int = 10, offset: int = 0) -> str:
    if limit > 100:
        raise ValueError("OpenDataSoft records endpoint limit must not exceed 100")
    if offset + limit >= 10000:
        raise ValueError("OpenDataSoft records endpoint offset + limit must remain below 10000; use exports for bulk pulls")
    query = urllib.parse.urlencode({"limit": str(limit), "offset": str(offset)})
    return f"{portal.api_base}/catalog/datasets/{dataset_id}/records?{query}"


def export_url(portal: ODSPortal, dataset_id: str, fmt: str = "json") -> str:
    safe_fmt = fmt.lower().strip()
    if safe_fmt not in {"csv", "json", "geojson", "parquet", "xlsx"}:
        raise ValueError(f"Unsupported export format: {fmt}")
    return f"{portal.api_base}/catalog/datasets/{dataset_id}/exports/{safe_fmt}"

#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


BASE_URL = "https://app.groupalarm.com/api/v1"
ENV_FILE = Path(__file__).with_name(".env")


def load_env(path: Path) -> None:
    if not path.exists():
        return

    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


def request(path: str, query: dict[str, str], headers: dict[str, str]) -> tuple[int, str, bytes]:
    url = BASE_URL + path
    if query:
        url += "?" + urllib.parse.urlencode(query)

    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "krempel-groupalarm-homeassistant-test/1.0",
            **headers,
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            return response.status, response.headers.get("content-type", ""), response.read()
    except urllib.error.HTTPError as error:
        return error.code, error.headers.get("content-type", ""), error.read()


def summarize_body(body: bytes) -> str:
    if not body:
        return "empty body"

    try:
        data = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return f"non-json body, {len(body)} bytes"

    if isinstance(data, dict):
        error_keys = ("status", "error_code", "error_name", "detail", "error", "message", "i18nKey")
        error_parts = [f"{key}={data[key]}" for key in error_keys if key in data]
        if error_parts:
            return "json error; " + "; ".join(error_parts)

        keys = ", ".join(sorted(data.keys())[:12])
        identity = any(key in data for key in ("id", "email", "name", "surname"))
        return f"json object; keys=[{keys}]; identity_fields={identity}"
    if isinstance(data, list):
        return f"json list; items={len(data)}"
    return f"json {type(data).__name__}"


def main() -> int:
    load_env(ENV_FILE)
    api_key = os.environ.get("GROUPALARM_API_KEY", "").strip()
    organization_id = os.environ.get("GROUPALARM_ORGANIZATION_ID", "").strip()
    token_header = os.environ.get("GROUPALARM_TOKEN_HEADER", "API-TOKEN").strip()

    if not api_key:
        print("GROUPALARM_API_KEY missing")
        return 1
    if not organization_id:
        print("GROUPALARM_ORGANIZATION_ID missing")
        return 1
    if token_header not in {"API-TOKEN", "Personal-Access-Token"}:
        print("GROUPALARM_TOKEN_HEADER must be API-TOKEN or Personal-Access-Token")
        return 1

    status, content_type, body = request(
        "/alarms",
        {"organization": organization_id, "limit": "1", "offset": "0"},
        {token_header: api_key},
    )
    print(f"GetAlarms: status={status}, content_type={content_type or '-'}, {summarize_body(body)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

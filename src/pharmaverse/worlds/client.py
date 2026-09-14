"""Thin World Labs World API client.

Talks to https://api.worldlabs.ai using the public Marble v1 routes.
Auth is the WLT-Api-Key header. API credits are billed on the World Labs
Platform, not the Marble app.
"""

from __future__ import annotations

import json
import os
import time
from typing import Any, Callable
from urllib import error, request

DEFAULT_BASE_URL = "https://api.worldlabs.ai"
DEFAULT_TIMEOUT_S = 60.0
DOWNLOAD_TIMEOUT_S = 300.0


class WorldAPIError(RuntimeError):
    def __init__(self, message: str, status: int | None = None, body: str | None = None):
        super().__init__(message)
        self.status = status
        self.body = body


def load_api_key(environ: dict[str, str] | None = None) -> str:
    env = environ if environ is not None else os.environ
    key = (env.get("WLT_API_KEY") or "").strip()
    if not key:
        raise WorldAPIError(
            "Set WLT_API_KEY to a World Labs World API key from "
            "https://platform.worldlabs.ai/. Marble app credits cannot be used."
        )
    return key


def unwrap_world(payload: dict[str, Any]) -> dict[str, Any]:
    """Normalize generate-snapshot and GET /worlds payloads."""
    if "world" in payload and isinstance(payload["world"], dict):
        world = dict(payload["world"])
    else:
        world = dict(payload)
    if "id" in world and "world_id" not in world:
        world["world_id"] = world["id"]
    return world


class WorldLabsClient:
    def __init__(
        self,
        api_key: str,
        base_url: str = DEFAULT_BASE_URL,
        timeout_s: float = DEFAULT_TIMEOUT_S,
        opener: Callable[[request.Request], tuple[int, bytes]] | None = None,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout_s = timeout_s
        self._opener = opener

    def request(
        self,
        method: str,
        path: str,
        body: dict[str, Any] | None = None,
        timeout_s: float | None = None,
    ) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        payload = json.dumps(body).encode("utf-8") if body is not None else None
        headers = {
            "WLT-Api-Key": self.api_key,
            "Accept": "application/json",
        }
        if payload is not None:
            headers["Content-Type"] = "application/json"
        req = request.Request(url, data=payload, headers=headers, method=method)
        timeout = self.timeout_s if timeout_s is None else timeout_s
        try:
            if self._opener is not None:
                status, raw = self._opener(req)
                if status >= 400:
                    text = raw.decode("utf-8", errors="replace")
                    raise WorldAPIError(
                        f"{method} {path}: {status} {text}", status=status, body=text
                    )
                return json.loads(raw.decode("utf-8")) if raw else {}
            with request.urlopen(req, timeout=timeout) as response:
                raw = response.read()
                return json.loads(raw.decode("utf-8")) if raw else {}
        except error.HTTPError as exc:
            text = exc.read().decode("utf-8", errors="replace")
            raise WorldAPIError(
                f"{method} {path}: {exc.code} {text}", status=exc.code, body=text
            ) from exc
        except error.URLError as exc:
            raise WorldAPIError(f"{method} {path}: {exc.reason}") from exc

    def get_credits(self) -> dict[str, Any]:
        return self.request("GET", "/marble/v1/credits")

    def generate_world(self, generate_request: dict[str, Any]) -> dict[str, Any]:
        return self.request("POST", "/marble/v1/worlds:generate", generate_request)

    def get_operation(self, operation_id: str) -> dict[str, Any]:
        return self.request("GET", f"/marble/v1/operations/{operation_id}")

    def get_world(self, world_id: str) -> dict[str, Any]:
        return unwrap_world(self.request("GET", f"/marble/v1/worlds/{world_id}"))

    def list_worlds(self, **filters: Any) -> dict[str, Any]:
        body = {key: value for key, value in filters.items() if value is not None}
        return self.request("POST", "/marble/v1/worlds:list", body or {"page_size": 20})

    def export_world(self, world_id: str, export_request: dict[str, Any]) -> dict[str, Any]:
        return self.request(
            "POST",
            f"/marble/v1/worlds/{world_id}:export",
            export_request,
        )

    def poll_operation(
        self,
        operation_id: str,
        interval_s: float = 5.0,
        timeout_s: float = 1200.0,
        sleep: Callable[[float], None] = time.sleep,
    ) -> dict[str, Any]:
        deadline = time.monotonic() + timeout_s
        operation: dict[str, Any] | None = None
        while time.monotonic() < deadline:
            operation = self.get_operation(operation_id)
            if operation.get("done"):
                if operation.get("error"):
                    raise WorldAPIError(
                        f"operation {operation_id} failed: {operation['error']}",
                        body=json.dumps(operation["error"]),
                    )
                return operation
            sleep(interval_s)
        raise WorldAPIError(
            f"operation {operation_id} timed out after {timeout_s:.0f}s; last={operation}"
        )

    def download(self, url: str, dest: str, timeout_s: float = DOWNLOAD_TIMEOUT_S) -> str:
        req = request.Request(url, headers={"WLT-Api-Key": self.api_key})
        with request.urlopen(req, timeout=timeout_s) as response, open(dest, "wb") as handle:
            while True:
                chunk = response.read(1024 * 256)
                if not chunk:
                    break
                handle.write(chunk)
        return dest

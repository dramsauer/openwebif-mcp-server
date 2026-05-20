from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any
from urllib.parse import urljoin

import httpx


class OpenWebifError(RuntimeError):
    """Raised when OpenWebif returns an error or cannot be reached."""


@dataclass(frozen=True)
class OpenWebifConfig:
    base_url: str
    username: str | None = None
    password: str | None = None
    timeout: float = 10.0
    allow_mutations: bool = False

    @classmethod
    def from_env(cls) -> "OpenWebifConfig":
        base_url = os.environ.get("OPENWEBIF_BASE_URL", "").strip()
        if not base_url:
            raise OpenWebifError("OPENWEBIF_BASE_URL is required")

        username = os.environ.get("OPENWEBIF_USERNAME") or None
        password = os.environ.get("OPENWEBIF_PASSWORD") or None
        timeout = float(os.environ.get("OPENWEBIF_TIMEOUT", "10"))
        allow_mutations = os.environ.get("OPENWEBIF_ALLOW_MUTATIONS", "false").lower() in {
            "1",
            "true",
            "yes",
            "on",
        }

        return cls(
            base_url=base_url.rstrip("/") + "/",
            username=username,
            password=password,
            timeout=timeout,
            allow_mutations=allow_mutations,
        )


class OpenWebifClient:
    def __init__(self, config: OpenWebifConfig):
        self.config = config
        auth = None
        if config.username is not None:
            auth = (config.username, config.password or "")
        self._client = httpx.Client(timeout=config.timeout, auth=auth)

    def api(self, method: str, params: dict[str, Any] | None = None) -> Any:
        url = urljoin(self.config.base_url, f"api/{method.lstrip('/')}")
        try:
            response = self._client.get(url, params=self._clean_params(params or {}))
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise OpenWebifError(f"OpenWebif request failed: {exc}") from exc

        try:
            payload = response.json()
        except ValueError as exc:
            raise OpenWebifError(f"OpenWebif returned non-JSON response from {method}") from exc

        if isinstance(payload, dict) and payload.get("result") is False:
            message = payload.get("message") or payload.get("statetext") or "OpenWebif returned false"
            raise OpenWebifError(str(message))

        return payload

    def require_mutations_enabled(self) -> None:
        if not self.config.allow_mutations:
            raise OpenWebifError(
                "This tool changes the receiver. Set OPENWEBIF_ALLOW_MUTATIONS=true to enable it."
            )

    @staticmethod
    def _clean_params(params: dict[str, Any]) -> dict[str, Any]:
        return {key: value for key, value in params.items() if value is not None}


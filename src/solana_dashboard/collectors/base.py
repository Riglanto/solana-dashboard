"""Shared HTTP plumbing for collectors: timeouts, retries, errors."""

from __future__ import annotations

import logging
import time

import requests

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 15.0

# Statuses worth retrying with backoff (rate limit / transient server errors).
TRANSIENT_STATUSES = (429, 502, 503, 504)


class CollectorError(Exception):
    """Raised when a data source cannot be reached or parsed."""

    def __init__(self, message: str, *, transient: bool = False) -> None:
        super().__init__(message)
        self.transient = transient  # True → retry with backoff


def _with_retries(attempt, what: str, retries: int = 3):
    """Run attempt() with exponential backoff on transient failures."""
    last_err: Exception | None = None
    for n in range(retries):
        try:
            return attempt()
        except requests.RequestException as exc:
            last_err = exc
        except CollectorError as exc:
            if not exc.transient:
                raise
            last_err = exc
        time.sleep(2**n)
    raise CollectorError(f"Giving up on {what} after {retries} attempts: {last_err}")


def _request(
    method: str,
    url: str,
    *,
    params: dict | None = None,
    json_body: dict | None = None,
    headers: dict | None = None,
    retries: int = 3,
    timeout: float = DEFAULT_TIMEOUT,
) -> dict | list:
    """HTTP with exponential backoff. Raises CollectorError after retries."""

    def attempt() -> dict | list:
        resp = requests.request(
            method, url, params=params, json=json_body, headers=headers,
            timeout=timeout,
        )
        if resp.status_code == 200:
            return resp.json()
        if resp.status_code in TRANSIENT_STATUSES:
            raise CollectorError(f"HTTP {resp.status_code} for {url}",
                                 transient=True)
        raise CollectorError(f"HTTP {resp.status_code} for {url}: {resp.text[:200]}")

    return _with_retries(attempt, url, retries)


def get_json(
    url: str,
    *,
    params: dict | None = None,
    headers: dict | None = None,
    retries: int = 3,
    timeout: float = DEFAULT_TIMEOUT,
) -> dict | list:
    """GET with exponential backoff. Raises CollectorError after retries."""
    return _request(
        "GET", url, params=params, headers=headers, retries=retries,
        timeout=timeout,
    )


def post_json(
    url: str,
    *,
    json_body: dict | None = None,
    headers: dict | None = None,
    retries: int = 3,
    timeout: float = DEFAULT_TIMEOUT,
) -> dict | list:
    """POST JSON with exponential backoff. Raises CollectorError after retries."""
    return _request(
        "POST", url, json_body=json_body, headers=headers, retries=retries,
        timeout=timeout,
    )


def post_json_rpc(
    url: str,
    method: str,
    params: list | None = None,
    *,
    retries: int = 3,
    timeout: float = DEFAULT_TIMEOUT,
) -> dict:
    """JSON-RPC 2.0 POST with retry. Returns the parsed `result` dict."""
    payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params or []}

    def attempt() -> dict:
        resp = requests.post(url, json=payload, timeout=timeout)
        if resp.status_code != 200:
            raise CollectorError(f"HTTP {resp.status_code} for {method}",
                                 transient=True)
        body = resp.json()
        if "error" in body:
            raise CollectorError(f"{method} RPC error: {body['error']}")
        return body["result"]

    return _with_retries(attempt, method, retries)

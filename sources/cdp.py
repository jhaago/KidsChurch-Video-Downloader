from __future__ import annotations

from collections import deque
import json
import time
from typing import Callable

import websocket


class CdpProtocolError(RuntimeError):
    pass


class CdpConnection:
    def __init__(self, ws_url: str, websocket_factory: Callable | None = None):
        factory = websocket_factory or websocket.create_connection
        self._ws = factory(ws_url, timeout=10.0, suppress_origin=True)
        self._next_id = 1
        self._events: deque[tuple[str, dict]] = deque()
        self._responses: dict[int, dict] = {}
        self._closed = False

    def _recv_message(self, timeout: float | None = None) -> dict:
        if timeout is not None and hasattr(self._ws, "settimeout"):
            self._ws.settimeout(timeout)
        try:
            raw = self._ws.recv()
        except (TimeoutError, websocket.WebSocketTimeoutException) as exc:
            raise TimeoutError("Timed out waiting for CDP response.") from exc
        if not raw:
            return {}
        try:
            return json.loads(raw)
        except (TypeError, json.JSONDecodeError) as exc:
            raise CdpProtocolError("Received invalid CDP JSON.") from exc

    def _stash(self, message: dict) -> None:
        method = message.get("method")
        if method:
            self._events.append((method, message.get("params") or {}))
        elif isinstance(message.get("id"), int):
            self._responses[message["id"]] = message

    def call(self, method: str, params: dict | None = None, timeout: float = 10.0) -> dict:
        request_id = self._next_id
        self._next_id += 1
        payload = {"id": request_id, "method": method, "params": params or {}}
        self._ws.send(json.dumps(payload, separators=(",", ":")))

        deadline = time.monotonic() + max(0.0, timeout)
        while True:
            message = self._responses.pop(request_id, None)
            if message is None:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError(f"Timed out waiting for CDP method {method}.")
                message = self._recv_message(remaining)
                if message.get("id") != request_id:
                    self._stash(message)
                    continue
            if "error" in message:
                error = message.get("error") or {}
                raise CdpProtocolError(error.get("message") or f"CDP method {method} failed.")
            return message.get("result") or {}

    def iter_events(self, timeout: float = 0.25):
        while self._events:
            yield self._events.popleft()
        while not self._closed:
            try:
                message = self._recv_message(timeout)
            except TimeoutError:
                return
            method = message.get("method")
            if method:
                yield method, message.get("params") or {}
            elif isinstance(message.get("id"), int):
                self._responses[message["id"]] = message

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._ws.close()

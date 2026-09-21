from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time
from typing import Callable, Mapping
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from .cdp import CdpConnection


class MinnoBrowserError(RuntimeError):
    pass


class BrowserUnavailableError(MinnoBrowserError):
    pass


class MinnoDiscoveryCancelled(MinnoBrowserError):
    pass


class MinnoDiscoveryTimeout(MinnoBrowserError):
    pass


@dataclass(frozen=True)
class BrowserInfo:
    name: str
    executable: Path


@dataclass(frozen=True)
class MinnoDiscovery:
    page_url: str
    title: str
    master_playlist_url: str
    request_headers: dict[str, str]


def find_supported_browser(
    platform_name: str | None = None,
    environ: Mapping[str, str] | None = None,
) -> BrowserInfo | None:
    platform_name = platform_name or sys.platform
    environ = dict(os.environ if environ is None else environ)
    candidates: list[BrowserInfo] = []

    if platform_name.startswith("win"):
        pf = environ.get("PROGRAMFILES")
        pf86 = environ.get("PROGRAMFILES(X86)")
        local = environ.get("LOCALAPPDATA")
        if pf:
            candidates.append(BrowserInfo("Google Chrome", Path(pf) / "Google" / "Chrome" / "Application" / "chrome.exe"))
        if pf86:
            candidates.append(BrowserInfo("Google Chrome", Path(pf86) / "Google" / "Chrome" / "Application" / "chrome.exe"))
        if local:
            candidates.append(BrowserInfo("Google Chrome", Path(local) / "Google" / "Chrome" / "Application" / "chrome.exe"))
        if pf86:
            candidates.append(BrowserInfo("Microsoft Edge", Path(pf86) / "Microsoft" / "Edge" / "Application" / "msedge.exe"))
        if pf:
            candidates.append(BrowserInfo("Microsoft Edge", Path(pf) / "Microsoft" / "Edge" / "Application" / "msedge.exe"))
    elif platform_name == "darwin":
        candidates.extend(
            [
                BrowserInfo("Google Chrome", Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")),
                BrowserInfo("Google Chrome", Path.home() / "Applications" / "Google Chrome.app" / "Contents" / "MacOS" / "Google Chrome"),
                BrowserInfo("Microsoft Edge", Path("/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge")),
            ]
        )

    return next((candidate for candidate in candidates if candidate.executable.exists()), None)


def _safe_headers(headers: Mapping[str, object] | None) -> dict[str, str]:
    if not headers:
        return {}
    by_lower = {str(k).lower(): str(v) for k, v in headers.items()}
    result: dict[str, str] = {}
    for canonical in ("User-Agent", "Referer", "Origin"):
        value = by_lower.get(canonical.lower())
        if value:
            result[canonical] = value
    return result


class MinnoBrowserSession:
    def __init__(self, profile_dir: Path, browser: BrowserInfo | None = None):
        self.profile_dir = Path(profile_dir)
        self.browser = browser or find_supported_browser()
        self._managed_process: subprocess.Popen | None = None

    def profile_exists(self) -> bool:
        return self.profile_dir.exists()

    def _require_browser(self) -> BrowserInfo:
        if self.browser is None:
            self.browser = find_supported_browser()
        if self.browser is None:
            raise BrowserUnavailableError(
                "Minno downloads require Google Chrome or Microsoft Edge to be installed."
            )
        return self.browser

    def _base_args(self) -> list[str]:
        browser = self._require_browser()
        self.profile_dir.mkdir(parents=True, exist_ok=True)
        return [
            str(browser.executable),
            f"--user-data-dir={self.profile_dir}",
            "--no-first-run",
            "--no-default-browser-check",
            "--autoplay-policy=no-user-gesture-required",
        ]

    def _spawn(self, args: list[str]) -> subprocess.Popen:
        self.close_managed_browser()
        self._managed_process = subprocess.Popen(
            args,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return self._managed_process

    def open_account_window(self, url: str = "https://kids.gominno.com/") -> subprocess.Popen:
        return self._spawn(self._base_args() + ["--new-window", url])

    def close_managed_browser(self) -> None:
        process = self._managed_process
        self._managed_process = None
        if process is None or process.poll() is not None:
            return
        process.terminate()
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            process.kill()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                pass

    def sign_out(self) -> None:
        self.close_managed_browser()
        if self.profile_dir.exists():
            shutil.rmtree(self.profile_dir)

    @staticmethod
    def _reserve_port() -> int:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("127.0.0.1", 0))
            return int(sock.getsockname()[1])

    def _launch_debug_browser(self, page_url: str) -> int:
        port = self._reserve_port()
        args = self._base_args() + [
            "--remote-debugging-address=127.0.0.1",
            f"--remote-debugging-port={port}",
            "--new-window",
            page_url,
        ]
        self._spawn(args)
        return port

    def _wait_for_target_websocket(self, port: int, page_url: str, deadline: float) -> str:
        wanted_host = (urlparse(page_url).hostname or "").lower()
        endpoint = f"http://127.0.0.1:{port}/json/list"
        while time.monotonic() < deadline:
            try:
                with urlopen(endpoint, timeout=1.0) as response:
                    targets = json.loads(response.read().decode("utf-8"))
                for target in targets:
                    if target.get("type") != "page" or not target.get("webSocketDebuggerUrl"):
                        continue
                    host = (urlparse(target.get("url") or "").hostname or "").lower()
                    if host == wanted_host or host.endswith(".gominno.com"):
                        return str(target["webSocketDebuggerUrl"])
            except Exception:
                pass
            time.sleep(0.1)
        raise MinnoDiscoveryTimeout("Timed out waiting for the Minno browser page.")

    def _create_cdp(self, ws_url: str) -> CdpConnection:
        return CdpConnection(ws_url)

    def _probe_playlist(self, url: str, headers: Mapping[str, str]) -> str:
        request = Request(url, headers=dict(headers), method="GET")
        with urlopen(request, timeout=15.0) as response:
            return response.read().decode("utf-8", errors="replace")

    @staticmethod
    def _title_from_cdp(cdp: CdpConnection) -> str:
        try:
            result = cdp.call(
                "Runtime.evaluate",
                {
                    "expression": "document.querySelector('meta[property=\\\"og:title\\\"]')?.content || document.title",
                    "returnByValue": True,
                },
            )
            value = (result.get("result") or {}).get("value")
            if value:
                return str(value).strip()
        except Exception:
            pass
        return "Minno episode"

    def discover(
        self,
        page_url: str,
        cancel_requested: Callable[[], bool],
        status_callback: Callable[[str], None],
        timeout_seconds: float = 180,
    ) -> MinnoDiscovery:
        deadline = time.monotonic() + max(1.0, float(timeout_seconds))
        cdp = None
        try:
            port = self._launch_debug_browser(page_url)
            if cancel_requested():
                raise MinnoDiscoveryCancelled("Minno discovery cancelled.")
            ws_url = self._wait_for_target_websocket(port, page_url, deadline)
            cdp = self._create_cdp(ws_url)
            cdp.call("Network.enable")
            cdp.call("Page.enable")
            cdp.call("Runtime.enable")

            started = time.monotonic()
            last_nudge = 0.0
            prompted = False
            while time.monotonic() < deadline:
                if cancel_requested():
                    raise MinnoDiscoveryCancelled("Minno discovery cancelled.")

                now = time.monotonic()
                if now - last_nudge >= 3.0:
                    try:
                        cdp.call(
                            "Runtime.evaluate",
                            {
                                "expression": "(() => { const v = document.querySelector('video'); if (v) { v.muted = true; v.play().catch(() => {}); } })()"
                            },
                            timeout=2.0,
                        )
                    except Exception:
                        pass
                    last_nudge = now

                if not prompted and now - started >= 12.0:
                    status_callback("Sign in to Minno and press Play in the browser window…")
                    prompted = True

                had_event = False
                for method, params in cdp.iter_events(timeout=0.25):
                    had_event = True
                    if method != "Network.requestWillBeSent":
                        continue
                    request_data = params.get("request") or {}
                    url = str(request_data.get("url") or "")
                    if ".m3u8" not in url.lower():
                        continue
                    headers = _safe_headers(request_data.get("headers") or {})
                    try:
                        playlist = self._probe_playlist(url, headers)
                    except Exception:
                        continue
                    if "#EXT-X-STREAM-INF" not in playlist.upper():
                        continue
                    return MinnoDiscovery(
                        page_url=page_url,
                        title=self._title_from_cdp(cdp),
                        master_playlist_url=url,
                        request_headers=headers,
                    )
                if not had_event:
                    time.sleep(0.05)

            raise MinnoDiscoveryTimeout(
                "No playable Minno stream was detected. Sign in and start playback, then try again."
            )
        finally:
            if cdp is not None:
                try:
                    cdp.close()
                except Exception:
                    pass
            self.close_managed_browser()

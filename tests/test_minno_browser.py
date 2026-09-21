import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from sources.minno_browser import (
    BrowserInfo,
    MinnoBrowserSession,
    MinnoDiscoveryCancelled,
    find_supported_browser,
)


class FakeProcess:
    def __init__(self):
        self.terminated = False
        self.killed = False
        self._running = True

    def poll(self):
        return None if self._running else 0

    def terminate(self):
        self.terminated = True
        self._running = False

    def wait(self, timeout=None):
        self._running = False
        return 0

    def kill(self):
        self.killed = True
        self._running = False


class FakeCdp:
    def __init__(self, events):
        self.events = list(events)
        self.calls = []
        self.closed = False

    def call(self, method, params=None, timeout=10.0):
        self.calls.append((method, params or {}))
        if method == "Runtime.evaluate":
            return {"result": {"value": "Test Minno Episode"}}
        return {}

    def iter_events(self, timeout=0.25):
        if not self.events:
            return iter(())
        event = self.events.pop(0)
        return iter((event,))

    def close(self):
        self.closed = True


class DiscoverySession(MinnoBrowserSession):
    def __init__(self, profile_dir, cdp, probes):
        super().__init__(profile_dir, browser=BrowserInfo("Chrome", Path("/fake/chrome")))
        self._fake_cdp = cdp
        self._probes = probes
        self.fake_process = FakeProcess()

    def _launch_debug_browser(self, page_url):
        self._managed_process = self.fake_process
        return 9222

    def _wait_for_target_websocket(self, port, page_url, deadline):
        return "ws://fake"

    def _create_cdp(self, ws_url):
        return self._fake_cdp

    def _probe_playlist(self, url, headers):
        return self._probes[url]


class MinnoBrowserTests(unittest.TestCase):
    def test_windows_browser_priority_prefers_chrome_then_edge(self):
        env = {
            "PROGRAMFILES": r"C:\Program Files",
            "PROGRAMFILES(X86)": r"C:\Program Files (x86)",
            "LOCALAPPDATA": r"C:\Users\me\AppData\Local",
        }
        chrome = Path(env["PROGRAMFILES"]) / "Google" / "Chrome" / "Application" / "chrome.exe"
        edge = Path(env["PROGRAMFILES(X86)"]) / "Microsoft" / "Edge" / "Application" / "msedge.exe"
        with patch.object(Path, "exists", autospec=True, side_effect=lambda p: p in {chrome, edge}):
            found = find_supported_browser("win32", env)
        self.assertEqual("Google Chrome", found.name)
        self.assertEqual(chrome, found.executable)

    def test_windows_falls_back_to_edge(self):
        env = {
            "PROGRAMFILES": r"C:\Program Files",
            "PROGRAMFILES(X86)": r"C:\Program Files (x86)",
            "LOCALAPPDATA": r"C:\Users\me\AppData\Local",
        }
        edge = Path(env["PROGRAMFILES(X86)"]) / "Microsoft" / "Edge" / "Application" / "msedge.exe"
        with patch.object(Path, "exists", autospec=True, side_effect=lambda p: p == edge):
            found = find_supported_browser("win32", env)
        self.assertEqual("Microsoft Edge", found.name)

    def test_macos_chrome_path_and_no_browser(self):
        chrome = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
        with patch.object(Path, "exists", autospec=True, side_effect=lambda p: p == chrome):
            found = find_supported_browser("darwin", {})
        self.assertEqual(chrome, found.executable)
        with patch.object(Path, "exists", autospec=True, return_value=False):
            self.assertIsNone(find_supported_browser("darwin", {}))

    def test_profile_exists_and_sign_out_closes_managed_process_then_deletes(self):
        with tempfile.TemporaryDirectory() as td:
            profile = Path(td) / "profile"
            profile.mkdir()
            session = MinnoBrowserSession(profile, browser=BrowserInfo("Chrome", Path("/fake/chrome")))
            process = FakeProcess()
            session._managed_process = process
            self.assertTrue(session.profile_exists())
            session.sign_out()
            self.assertTrue(process.terminated)
            self.assertFalse(profile.exists())

    def test_discovery_selects_master_and_only_returns_safe_headers(self):
        rendition = "https://media.example.invalid/video_3499968.m3u8"
        master = "https://media.example.invalid/index.m3u8?sessionId=secret"
        headers = {
            "User-Agent": "UA",
            "Referer": "https://kids.gominno.com/watch/1",
            "Origin": "https://kids.gominno.com",
            "Cookie": "secret-cookie",
            "Authorization": "Bearer secret",
        }
        events = [
            ("Network.requestWillBeSent", {"request": {"url": rendition, "headers": headers}}),
            ("Network.requestWillBeSent", {"request": {"url": master, "headers": headers}}),
        ]
        probes = {
            rendition: "#EXTM3U\n#EXTINF:2,\nseg.m4s\n",
            master: "#EXTM3U\n#EXT-X-STREAM-INF:BANDWIDTH=1000,RESOLUTION=1280x720\nvideo.m3u8\n",
        }
        with tempfile.TemporaryDirectory() as td:
            session = DiscoverySession(Path(td) / "profile", FakeCdp(events), probes)
            result = session.discover(
                "https://kids.gominno.com/watch/1",
                cancel_requested=lambda: False,
                status_callback=lambda _: None,
                timeout_seconds=2,
            )
        self.assertEqual(master, result.master_playlist_url)
        self.assertEqual("Test Minno Episode", result.title)
        self.assertEqual({"User-Agent": "UA", "Referer": headers["Referer"], "Origin": headers["Origin"]}, result.request_headers)
        self.assertTrue(session.fake_process.terminated)

    def test_cancellation_closes_browser_but_retains_profile(self):
        with tempfile.TemporaryDirectory() as td:
            profile = Path(td) / "profile"
            profile.mkdir()
            session = DiscoverySession(profile, FakeCdp([]), {})
            with self.assertRaises(MinnoDiscoveryCancelled):
                session.discover(
                    "https://kids.gominno.com/watch/1",
                    cancel_requested=lambda: True,
                    status_callback=lambda _: None,
                    timeout_seconds=2,
                )
            self.assertTrue(session.fake_process.terminated)
            self.assertTrue(profile.exists())


if __name__ == "__main__":
    unittest.main()

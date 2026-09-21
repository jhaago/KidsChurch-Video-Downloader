import tempfile
import unittest
from pathlib import Path

from sources.hls import NoUsableStreamError, ProtectedStreamError
from sources.minno import (
    MinnoClient,
    MinnoDownloadCancelled,
    MinnoTransferError,
    MinnoUnsupportedFormatError,
    validate_output_format,
)
from sources.minno_browser import MinnoDiscovery

MASTER_URL = "https://media.example.invalid/path/index.m3u8?sessionId=secret"
VIDEO_1080 = "https://media.example.invalid/path/video_1080.m3u8"
VIDEO_720 = "https://media.example.invalid/path/video_720.m3u8"
AUDIO = "https://media.example.invalid/path/audio_en.m3u8"

MASTER = """#EXTM3U
#EXT-X-MEDIA:TYPE=AUDIO,GROUP-ID="audio",NAME="English",LANGUAGE="en",DEFAULT=YES,URI="audio_en.m3u8"
#EXT-X-STREAM-INF:BANDWIDTH=2500000,RESOLUTION=1280x720,CODECS="avc1.640020,mp4a.40.2",AUDIO="audio"
video_720.m3u8
#EXT-X-STREAM-INF:BANDWIDTH=3500000,RESOLUTION=1920x1080,CODECS="avc1.640028,mp4a.40.2",AUDIO="audio"
video_1080.m3u8
"""
VIDEO_MEDIA = """#EXTM3U
#EXT-X-PLAYLIST-TYPE:VOD
#EXTINF:2,
a.m4s
#EXTINF:2,
b.m4s
#EXTINF:2,
c.m4s
"""
AUDIO_MEDIA = """#EXTM3U
#EXT-X-PLAYLIST-TYPE:VOD
#EXTINF:2,
a.m4s
#EXTINF:2,
b.m4s
#EXTINF:2,
c.m4s
"""


class FakeBrowserSession:
    def __init__(self, discovery=None):
        self.discovery = discovery or MinnoDiscovery(
            page_url="https://kids.gominno.com/watch/test",
            title="Episode Title",
            master_playlist_url=MASTER_URL,
            request_headers={"User-Agent": "UA", "Referer": "https://kids.gominno.com/"},
        )
        self.discover_count = 0

    def discover(self, page_url, cancel_requested, status_callback, timeout_seconds=180):
        self.discover_count += 1
        return self.discovery


class FakeProcess:
    def __init__(self, lines, returncode=0):
        self.stdout = iter(lines)
        self.returncode = returncode
        self.terminated = False
        self.running = True

    def wait(self):
        self.running = False
        return self.returncode

    def poll(self):
        return None if self.running else self.returncode

    def terminate(self):
        self.terminated = True
        self.running = False
        self.returncode = -15

    def kill(self):
        self.terminated = True
        self.running = False
        self.returncode = -9


class ProcessFactory:
    def __init__(self, processes):
        self.processes = list(processes)
        self.commands = []

    def __call__(self, command, **kwargs):
        self.commands.append(command)
        return self.processes.pop(0)


def make_fetch(mapping=None):
    values = {
        MASTER_URL: MASTER,
        VIDEO_1080: VIDEO_MEDIA,
        VIDEO_720: VIDEO_MEDIA,
        AUDIO: AUDIO_MEDIA,
    }
    if mapping:
        values.update(mapping)
    return lambda url, headers: values[url]


class MinnoTests(unittest.TestCase):
    def test_output_format_validation(self):
        validate_output_format("MP4 Video")
        for value in ("MP3 Audio", "WAV Audio"):
            with self.subTest(value=value), self.assertRaises(MinnoUnsupportedFormatError):
                validate_output_format(value)

    def test_preview_and_prepare_quality(self):
        client = MinnoClient(FakeBrowserSession(), fetch_text=make_fetch())
        preview = client.preview("https://kids.gominno.com/watch/test")
        self.assertEqual("Episode Title", preview.title)
        self.assertEqual(6.0, preview.duration)
        self.assertEqual(1080, preview.max_height)
        prepared = client.prepare("https://kids.gominno.com/watch/test", 720)
        self.assertEqual(720, prepared.height)
        self.assertEqual(VIDEO_720, prepared.video_url)
        self.assertEqual(AUDIO, prepared.audio_url)

    def test_protection_is_rejected_before_process(self):
        protected = "#EXTM3U\n#EXT-X-KEY:METHOD=AES-128,URI=\"key\"\n#EXTINF:2,\nseg.m4s\n"
        for target in (MASTER_URL, VIDEO_1080, AUDIO):
            with self.subTest(target=target):
                mapping = {target: protected}
                client = MinnoClient(FakeBrowserSession(), fetch_text=make_fetch(mapping))
                with self.assertRaises(ProtectedStreamError):
                    client.prepare("https://kids.gominno.com/watch/test", 1080)

    def test_no_audio_fails(self):
        no_audio_master = """#EXTM3U
#EXT-X-STREAM-INF:BANDWIDTH=3500000,RESOLUTION=1920x1080,CODECS="avc1.640028"
video_1080.m3u8
"""
        client = MinnoClient(FakeBrowserSession(), fetch_text=make_fetch({MASTER_URL: no_audio_master}))
        with self.assertRaises(NoUsableStreamError):
            client.prepare("https://kids.gominno.com/watch/test", 1080)

    def test_compatible_ffmpeg_command_maps_two_inputs_and_never_logs_url(self):
        process_factory = ProcessFactory([
            FakeProcess([
                "out_time_us=2000000\n",
                "total_size=1000000\n",
                "progress=continue\n",
                "out_time_us=6000000\n",
                "total_size=3000000\n",
                "progress=end\n",
            ])
        ])
        logs = []
        progress = []
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "episode.mp4"
            client = MinnoClient(
                FakeBrowserSession(),
                fetch_text=make_fetch(),
                process_factory=process_factory,
                status_callback=logs.append,
            )
            result = client.download(
                "https://kids.gominno.com/watch/test",
                1080,
                "ffmpeg",
                out,
                cancel_requested=lambda: False,
                progress_callback=progress.append,
                process_started_callback=lambda p: None,
            )
        cmd = process_factory.commands[0]
        self.assertIn("-progress", cmd)
        self.assertIn("pipe:1", cmd)
        self.assertIn("-nostats", cmd)
        self.assertEqual(2, cmd.count("-i"))
        self.assertIn("0:v:0", cmd)
        self.assertIn("1:a:0", cmd)
        self.assertIn("-c", cmd)
        self.assertIn("copy", cmd)
        self.assertIn("+faststart", cmd)
        self.assertFalse(result.needs_conversion)
        self.assertEqual("Episode Title", result.title)
        self.assertEqual(6.0, result.duration)
        self.assertTrue(progress)
        self.assertFalse(any("sessionId=secret" in line or ".m3u8?" in line for line in logs))

    def test_incompatible_codecs_use_mkv_and_require_conversion(self):
        incompatible_master = MASTER.replace("avc1.640028,mp4a.40.2", "vp09.00.10.08,opus")
        process_factory = ProcessFactory([FakeProcess(["progress=end\n"])])
        with tempfile.TemporaryDirectory() as td:
            client = MinnoClient(
                FakeBrowserSession(),
                fetch_text=make_fetch({MASTER_URL: incompatible_master}),
                process_factory=process_factory,
            )
            result = client.download(
                "https://kids.gominno.com/watch/test", 1080, "ffmpeg", Path(td) / "episode.mp4",
                cancel_requested=lambda: False,
                progress_callback=lambda s: None,
                process_started_callback=lambda p: None,
            )
        self.assertTrue(result.needs_conversion)
        self.assertEqual(".mkv", result.path.suffix)
        self.assertNotIn("+faststart", process_factory.commands[0])

    def test_403_retries_discovery_once_then_fails(self):
        session = FakeBrowserSession()
        factory = ProcessFactory([
            FakeProcess(["HTTP error 403 Forbidden\n"], returncode=1),
            FakeProcess(["HTTP error 403 Forbidden\n"], returncode=1),
        ])
        with tempfile.TemporaryDirectory() as td:
            client = MinnoClient(session, fetch_text=make_fetch(), process_factory=factory)
            with self.assertRaises(MinnoTransferError):
                client.download(
                    "https://kids.gominno.com/watch/test", 1080, "ffmpeg", Path(td) / "episode.mp4",
                    cancel_requested=lambda: False,
                    progress_callback=lambda s: None,
                    process_started_callback=lambda p: None,
                )
        self.assertEqual(2, session.discover_count)
        self.assertEqual(2, len(factory.commands))

    def test_cancellation_terminates_active_process(self):
        process = FakeProcess(["out_time_us=1000000\n", "progress=continue\n"])
        factory = ProcessFactory([process])
        calls = {"n": 0}

        def cancelled():
            calls["n"] += 1
            return calls["n"] >= 2

        with tempfile.TemporaryDirectory() as td:
            client = MinnoClient(FakeBrowserSession(), fetch_text=make_fetch(), process_factory=factory)
            with self.assertRaises(MinnoDownloadCancelled):
                client.download(
                    "https://kids.gominno.com/watch/test", 1080, "ffmpeg", Path(td) / "episode.mp4",
                    cancel_requested=cancelled,
                    progress_callback=lambda s: None,
                    process_started_callback=lambda p: None,
                )
        self.assertTrue(process.terminated)


if __name__ == "__main__":
    unittest.main()

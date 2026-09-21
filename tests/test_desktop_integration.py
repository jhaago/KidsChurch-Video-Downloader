import importlib
import sys
import tempfile
import types
import unittest
from pathlib import Path


class FakeBase:
    def _download_job(self, job, tools):
        return "youtube-path"


legacy = types.ModuleType("main")
legacy.DownloaderApp = FakeBase
legacy.APP_NAME = "YouTube Downloader"
legacy.APP_VERSION = "0.6.5"
legacy.RESOLUTION_FORMATS = {
    "1080p": "unused",
    "720p": "unused",
    "480p": "unused",
}
legacy.OUTPUT_FORMATS = ("MP4 Video", "MP3 Audio", "WAV Audio")
legacy.safe_filename = lambda name: name.replace("/", "_") or "media"
legacy.duration_text = lambda seconds: "1:30:00" if seconds else "Unknown"
legacy.no_window_flags = lambda: 0
legacy.tool_environment = lambda: {}
sys.modules.setdefault("main", legacy)

desktop_app = importlib.import_module("desktop_app")


class DesktopIntegrationTests(unittest.TestCase):
    def test_resolution_height(self):
        self.assertEqual(1080, desktop_app.resolution_height("1080p"))
        self.assertEqual(720, desktop_app.resolution_height("720p"))
        self.assertEqual(480, desktop_app.resolution_height("480p"))
        self.assertEqual(1080, desktop_app.resolution_height("unexpected"))

    def test_format_minno_progress_includes_speed_and_eta(self):
        from sources.progress import TransferSnapshot

        pct, text = desktop_app.format_minno_progress(
            TransferSnapshot(percent=53.8, speed_bps=2_900_000, eta_seconds=702)
        )
        self.assertAlmostEqual(40.35, pct)
        self.assertIn("53.8%", text)
        self.assertIn("2.9 MB/s", text)
        self.assertIn("ETA 11:42", text)

    def test_unique_output_path_avoids_overwrite(self):
        with tempfile.TemporaryDirectory() as td:
            folder = Path(td)
            first = folder / "Episode.mp4"
            first.write_text("existing")
            self.assertEqual(folder / "Episode (2).mp4", desktop_app.unique_output_path(folder, "Episode", ".mp4"))

    def test_download_job_routes_minno_without_touching_youtube_base_path(self):
        app = desktop_app.MultiSourceDownloaderApp.__new__(desktop_app.MultiSourceDownloaderApp)
        app._download_minno_job = lambda job, tools: "minno-path"
        self.assertEqual("minno-path", app._download_job({"source": "minno"}, {}))
        self.assertEqual("youtube-path", app._download_job({"source": "youtube"}, {}))

    def test_app_data_path_keeps_existing_settings_folder_name(self):
        self.assertEqual("KidsChurchVideoDownloader", desktop_app.app_data_dir().name)


if __name__ == "__main__":
    unittest.main()

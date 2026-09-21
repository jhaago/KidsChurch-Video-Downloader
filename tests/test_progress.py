import unittest

from sources.progress import (
    TransferProgressEstimator,
    format_bytes_per_second,
    format_eta,
    redact_sensitive,
)


class ProgressTests(unittest.TestCase):
    def test_redacts_url_query_and_headers(self):
        text = (
            "GET https://cdn.example.invalid/index.m3u8?sessionId=abc123&token=secret\n"
            "Cookie: a=b\nAuthorization: Bearer secret\nX-Playback-Token: xyz\n"
            "sessionId=other token=again"
        )
        safe = redact_sensitive(text)
        self.assertIn("https://cdn.example.invalid/index.m3u8?<redacted>", safe)
        for secret in ("abc123", "secret", "a=b", "xyz", "other", "again"):
            self.assertNotIn(secret, safe)
        self.assertIn("Cookie: <redacted>", safe)
        self.assertIn("Authorization: <redacted>", safe)

    def test_progress_speed_and_eta(self):
        est = TransferProgressEstimator(100.0, window_seconds=8.0)
        first = est.update(0.0, 0.0, 0)
        second = est.update(5.0, 20.0, 10_000_000)
        self.assertEqual(0.0, first.percent)
        self.assertIsNone(first.speed_bps)
        self.assertAlmostEqual(20.0, second.percent)
        self.assertAlmostEqual(2_000_000.0, second.speed_bps)
        self.assertAlmostEqual(20.0, second.eta_seconds)

    def test_progress_without_size_keeps_eta_but_no_speed(self):
        est = TransferProgressEstimator(100.0)
        est.update(0.0, 0.0, None)
        snap = est.update(10.0, 25.0, None)
        self.assertAlmostEqual(25.0, snap.percent)
        self.assertIsNone(snap.speed_bps)
        self.assertAlmostEqual(30.0, snap.eta_seconds)

    def test_decreasing_media_time_never_produces_negative_eta(self):
        est = TransferProgressEstimator(100.0)
        est.update(0.0, 50.0, 1_000)
        snap = est.update(5.0, 40.0, 2_000)
        self.assertGreaterEqual(snap.percent, 0.0)
        self.assertTrue(snap.eta_seconds is None or snap.eta_seconds >= 0.0)

    def test_formatters(self):
        self.assertEqual("2.0 MB/s", format_bytes_per_second(2_000_000))
        self.assertEqual("—", format_bytes_per_second(None))
        self.assertEqual("1:05", format_eta(65))
        self.assertEqual("1:01:01", format_eta(3661))
        self.assertEqual("—", format_eta(None))


if __name__ == "__main__":
    unittest.main()

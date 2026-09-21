import unittest
from sources.source_detector import SourceType, classify_source


class SourceDetectorTests(unittest.TestCase):
    def test_youtube_hosts(self):
        for url in (
            "https://www.youtube.com/watch?v=abc",
            "https://youtu.be/abc",
            "https://music.youtube.com/watch?v=abc",
        ):
            with self.subTest(url=url):
                self.assertEqual(SourceType.YOUTUBE, classify_source(url))

    def test_minno_hosts(self):
        for url in (
            "https://gominno.com/watch/example",
            "https://kids.gominno.com/example",
            "https://app.gominno.com/watch/example?foo=bar",
        ):
            with self.subTest(url=url):
                self.assertEqual(SourceType.MINNO, classify_source(url))

    def test_lookalike_domains_are_unknown(self):
        for url in (
            "https://gominno.com.evil.example/watch/1",
            "https://notyoutube.com/watch?v=1",
            "not a url",
            "",
        ):
            with self.subTest(url=url):
                self.assertEqual(SourceType.UNKNOWN, classify_source(url))


if __name__ == "__main__":
    unittest.main()

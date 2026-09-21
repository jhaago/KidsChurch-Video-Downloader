import unittest
from pathlib import Path

from sources.hls import (
    HlsAudioTrack,
    HlsMasterPlaylist,
    HlsVariant,
    NoUsableStreamError,
    ProtectedStreamError,
    inspect_media_playlist,
    parse_master_playlist,
    select_stream,
)

FIXTURES = Path(__file__).parent / "fixtures"


def read_fixture(name):
    return (FIXTURES / name).read_text(encoding="utf-8")


class HlsTests(unittest.TestCase):
    def test_parse_master_and_select_by_ceiling(self):
        master = parse_master_playlist(read_fixture("minno_master.m3u8"), "https://media.example.invalid/path/index.m3u8")
        self.assertEqual(4, len(master.variants))
        self.assertEqual(1080, select_stream(master, 1080).video.height)
        self.assertEqual(720, select_stream(master, 720).video.height)
        self.assertEqual(540, select_stream(master, 600).video.height)
        self.assertEqual("en", select_stream(master, 1080).audio.language)
        self.assertEqual("https://media.example.invalid/path/video_3499968.m3u8", select_stream(master, 1080).video.uri)

    def test_media_duration(self):
        info = inspect_media_playlist(read_fixture("minno_video.m3u8"))
        self.assertAlmostEqual(6.0, info.duration_seconds)
        self.assertFalse(info.is_protected)

    def test_no_video_at_or_below_ceiling_fails(self):
        master = HlsMasterPlaylist(
            variants=(HlsVariant("v540.m3u8", 2_000_000, 960, 540, ("avc1",), "audio"),),
            audio_tracks=(HlsAudioTrack("a.m3u8", "audio", "en", "English", True),),
        )
        with self.assertRaises(NoUsableStreamError):
            select_stream(master, 480)

    def test_audio_preference_english_then_default_then_first(self):
        variants = (HlsVariant("v.m3u8", 1, 1280, 720, ("avc1",), "audio"),)
        master = HlsMasterPlaylist(
            variants=variants,
            audio_tracks=(
                HlsAudioTrack("es.m3u8", "audio", "es", "Spanish", True),
                HlsAudioTrack("en.m3u8", "audio", "en", "English", False),
            ),
        )
        self.assertEqual("en", select_stream(master, 1080).audio.language)

        no_english = HlsMasterPlaylist(
            variants=variants,
            audio_tracks=(
                HlsAudioTrack("fr.m3u8", "audio", "fr", "French", False),
                HlsAudioTrack("es.m3u8", "audio", "es", "Spanish", True),
            ),
        )
        self.assertEqual("es", select_stream(no_english, 1080).audio.language)

        no_default = HlsMasterPlaylist(
            variants=variants,
            audio_tracks=(
                HlsAudioTrack("fr.m3u8", "audio", "fr", "French", False),
                HlsAudioTrack("es.m3u8", "audio", "es", "Spanish", False),
            ),
        )
        self.assertEqual("fr", select_stream(no_default, 1080).audio.language)

    def test_missing_audio_fails(self):
        master = HlsMasterPlaylist(
            variants=(HlsVariant("v.m3u8", 1, 1280, 720, ("avc1",), "audio"),),
            audio_tracks=(),
        )
        with self.assertRaises(NoUsableStreamError):
            select_stream(master, 1080)

    def test_master_session_key_is_rejected(self):
        text = '#EXTM3U\n#EXT-X-SESSION-KEY:METHOD=AES-128,URI="key"\n'
        with self.assertRaises(ProtectedStreamError):
            parse_master_playlist(text, "https://media.example.invalid/index.m3u8")

    def test_media_encryption_markers_are_rejected(self):
        for name in ("protected_aes128.m3u8", "protected_sample_aes.m3u8"):
            with self.subTest(name=name):
                with self.assertRaises(ProtectedStreamError):
                    inspect_media_playlist(read_fixture(name))
        with self.assertRaises(ProtectedStreamError):
            inspect_media_playlist('#EXTM3U\n#EXT-X-KEY:METHOD=AES-128,KEYFORMAT="com.widevine"\n')

    def test_method_none_is_allowed(self):
        info = inspect_media_playlist("#EXTM3U\n#EXT-X-KEY:METHOD=NONE\n#EXTINF:2,\nseg.m4s\n")
        self.assertAlmostEqual(2.0, info.duration_seconds)


if __name__ == "__main__":
    unittest.main()

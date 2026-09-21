import json
import unittest

from sources.cdp import CdpConnection, CdpProtocolError


class FakeWebSocket:
    def __init__(self, incoming):
        self.incoming = list(incoming)
        self.sent = []
        self.closed = False
        self.timeout = None

    def send(self, text):
        self.sent.append(text)

    def recv(self):
        if not self.incoming:
            raise TimeoutError("timed out")
        item = self.incoming.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    def settimeout(self, value):
        self.timeout = value

    def close(self):
        self.closed = True


class CdpTests(unittest.TestCase):
    def test_call_matches_response_and_preserves_events(self):
        fake = FakeWebSocket([
            json.dumps({"method": "Network.requestWillBeSent", "params": {"request": {"url": "https://example.invalid"}}}),
            json.dumps({"id": 1, "result": {"ok": True}}),
        ])
        conn = CdpConnection("ws://example", websocket_factory=lambda *a, **k: fake)
        result = conn.call("Network.enable")
        self.assertEqual({"ok": True}, result)
        self.assertEqual({"id": 1, "method": "Network.enable", "params": {}}, json.loads(fake.sent[0]))
        events = list(conn.iter_events(timeout=0.01))
        self.assertEqual("Network.requestWillBeSent", events[0][0])

    def test_protocol_error_raises(self):
        fake = FakeWebSocket([json.dumps({"id": 1, "error": {"code": -1, "message": "bad"}})])
        conn = CdpConnection("ws://example", websocket_factory=lambda *a, **k: fake)
        with self.assertRaises(CdpProtocolError):
            conn.call("Bad.method")

    def test_timeout_raises_timeout_error(self):
        fake = FakeWebSocket([])
        conn = CdpConnection("ws://example", websocket_factory=lambda *a, **k: fake)
        with self.assertRaises(TimeoutError):
            conn.call("Network.enable", timeout=0.01)

    def test_close_closes_socket(self):
        fake = FakeWebSocket([])
        conn = CdpConnection("ws://example", websocket_factory=lambda *a, **k: fake)
        conn.close()
        self.assertTrue(fake.closed)


if __name__ == "__main__":
    unittest.main()

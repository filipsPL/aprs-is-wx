import aprs_is_wx
from aprs_is_wx import send_aprs_with_retry

CONFIG = {
    "APRS_HOST": "rotate.aprs.net",
    "APRS_PORT": 14580,
    "APRS_USER": "N0CALL",
    "APRS_PASS": "12345",
    "CALLSIGN": "N0CALL-13",
}


class FakeSocket:
    """Stand-in for socket.socket that replays canned recv() responses."""

    def __init__(self, recv_queue, connect_exception=None):
        self._recv_queue = list(recv_queue)
        self._connect_exception = connect_exception
        self.sent = []
        self.closed = False

    def settimeout(self, timeout_value):
        pass

    def connect(self, address):
        if self._connect_exception is not None:
            raise self._connect_exception

    def send(self, data):
        self.sent.append(data)

    def recv(self, bufsize):
        if not self._recv_queue:
            return b""
        item = self._recv_queue.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    def shutdown(self, how):
        pass

    def close(self):
        self.closed = True


def patch_socket_factory(monkeypatch, sockets):
    """Make aprs_is_wx.socket(...) return the given fakes, one per call."""
    remaining = list(sockets)

    def factory(*args, **kwargs):
        return remaining.pop(0)

    monkeypatch.setattr(aprs_is_wx, "socket", factory)
    monkeypatch.setattr(aprs_is_wx.time, "sleep", lambda seconds: None)


def test_verified_login_sends_packet_even_when_banner_and_logresp_are_split(monkeypatch):
    fake = FakeSocket(
        [
            b"# aprsc 2.1.21-gbfc2090\r\n",
            b"# logresp N0CALL verified, server aprsc\r\n",
        ]
    )
    patch_socket_factory(monkeypatch, [fake])

    result = send_aprs_with_retry(CONFIG, "TESTPACKET")

    assert result is True
    assert fake.sent[0].startswith(b"user N0CALL pass 12345")
    assert fake.sent[1] == b"N0CALL-13>APRS:TESTPACKET\n"


def test_invalid_login_is_rejected_without_sending_packet(monkeypatch):
    fake = FakeSocket([b"# logresp N0CALL invalid, bad password\r\n"])
    patch_socket_factory(monkeypatch, [fake])

    result = send_aprs_with_retry(CONFIG, "TESTPACKET")

    assert result is False
    assert len(fake.sent) == 1  # only the login line, no weather packet


def test_unverified_login_still_sends_packet_and_warns(monkeypatch, caplog):
    fake = FakeSocket([b"# logresp N0CALL unverified, bad password\r\n"])
    patch_socket_factory(monkeypatch, [fake])

    with caplog.at_level("WARNING"):
        result = send_aprs_with_retry(CONFIG, "TESTPACKET")

    assert result is True
    assert any("unverified" in message.lower() for message in caplog.messages)


def test_banner_only_response_warns_but_still_sends_packet(monkeypatch, caplog):
    fake = FakeSocket(
        [
            b"# aprsc 2.1.21-gbfc2090\r\n",
            aprs_is_wx.timeout("timed out"),
        ]
    )
    patch_socket_factory(monkeypatch, [fake])

    with caplog.at_level("WARNING"):
        result = send_aprs_with_retry(CONFIG, "TESTPACKET")

    assert result is True
    assert any("unexpected aprs-is login response" in message.lower() for message in caplog.messages)


def test_connection_refused_retries_then_gives_up(monkeypatch):
    fakes = [FakeSocket([], connect_exception=ConnectionRefusedError()) for _ in range(2)]
    patch_socket_factory(monkeypatch, fakes)

    result = send_aprs_with_retry(CONFIG, "TESTPACKET", max_retries=2, retry_delay=0)

    assert result is False

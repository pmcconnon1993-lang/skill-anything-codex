"""Tests for parsers."""

import socket
import tempfile

import pytest

from skill_anything.parsers.base import BaseParser
from skill_anything.parsers.text_parser import TextParser


class _FakeWebConnection:
    def __init__(self):
        self.closed = False

    def close(self):
        self.closed = True


class _FakeWebResponse:
    def __init__(self, status, *, body=b"", location=None):
        self.status = status
        self.body = body
        self.location = location
        self.reason = "test response"
        self.headers = self

    def getheader(self, name):
        return self.location if name == "Location" else None

    def get_content_charset(self):
        return "utf-8"

    def read(self):
        return self.body


def test_text_parser_from_file():
    content = "# Chapter 1\n\nThis is the first chapter content.\n\n# Chapter 2\n\nThis is the second chapter."
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write(content)
        f.flush()
        parser = TextParser()
        chunks = parser.parse(f.name)
        assert len(chunks) >= 1
        assert chunks[0].section in ("Chapter 1", "Chapter 2", "Section 1")


def test_text_parser_from_inline():
    parser = TextParser()
    text = "This is a test content with enough words to be meaningful and useful for testing purposes."
    chunks = parser.parse(text)
    assert len(chunks) >= 1
    assert chunks[0].content


def test_text_parser_rejects_missing_file_instead_of_learning_filename(tmp_path):
    missing = tmp_path / "missing-notes.md"

    with pytest.raises(FileNotFoundError, match="Text source file not found"):
        TextParser().parse(str(missing))


def test_text_parser_markdown_headings():
    parser = TextParser()
    md = "# Introduction\n\nSome intro text here.\n\n## Methods\n\nSome methods text.\n\n## Results\n\nSome results."
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write(md)
        f.flush()
        chunks = parser.parse(f.name)
        sections = [c.section for c in chunks]
        assert any("Introduction" in s or "Methods" in s for s in sections)


def test_base_parser_split_chunks():
    long_text = "A" * 500 + "\n\n" + "B" * 500 + "\n\n" + "C" * 500
    chunks = BaseParser._split_into_chunks(long_text, max_chars=600, overlap=50)
    assert len(chunks) >= 2
    for chunk in chunks:
        assert len(chunk) <= 700


def test_text_parser_empty_file():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("")
        f.flush()
        parser = TextParser()
        chunks = parser.parse(f.name)
        assert len(chunks) == 0


def test_web_parser_rejects_non_url():
    from skill_anything.parsers.web_parser import WebParser
    parser = WebParser()
    with pytest.raises(ValueError, match="Expected a URL"):
        parser.parse("not-a-url")


def test_web_parser_accepts_public_default_port(monkeypatch):
    from skill_anything.parsers.web_parser import WebParser

    def public_dns(host, port, **_kwargs):
        assert (host, port) == ("example.com", 443)
        return [
            (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("93.184.216.34", port))
        ]

    monkeypatch.setattr(socket, "getaddrinfo", public_dns)

    target = WebParser._resolve_target("https://example.com/guide?q=security")

    assert target.host == "example.com"
    assert target.port == 443
    assert target.request_target == "/guide?q=security"
    assert target.addresses[0][3][0] == "93.184.216.34"


@pytest.mark.parametrize(
    ("url", "address", "family"),
    [
        ("http://127.0.0.1/", "127.0.0.1", socket.AF_INET),
        ("http://2130706433/", "127.0.0.1", socket.AF_INET),
        ("http://example.com/", "10.0.0.8", socket.AF_INET),
        ("http://example.com/", "169.254.169.254", socket.AF_INET),
        ("https://[::1]/", "::1", socket.AF_INET6),
        ("https://example.com/", "fc00::1", socket.AF_INET6),
    ],
)
def test_web_parser_rejects_non_public_resolutions(monkeypatch, url, address, family):
    from skill_anything.parsers.web_parser import WebParser

    def private_dns(_host, port, **_kwargs):
        sockaddr = (address, port, 0, 0) if family == socket.AF_INET6 else (address, port)
        return [(family, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", sockaddr)]

    monkeypatch.setattr(socket, "getaddrinfo", private_dns)

    with pytest.raises(ValueError, match="resolves to non-public address"):
        WebParser._resolve_target(url)


def test_web_parser_rejects_non_default_ports():
    from skill_anything.parsers.web_parser import WebParser

    with pytest.raises(ValueError, match="must use port 443"):
        WebParser._resolve_target("https://example.com:8443/")


def test_web_parser_revalidates_public_redirects(monkeypatch):
    from skill_anything.parsers.web_parser import WebParser

    start = "https://example.com/start"
    destination = "https://example.com/article"
    events = []
    connections = []

    def resolve(url):
        events.append(("resolve", url))
        return url

    def request(target):
        events.append(("request", target))
        connection = _FakeWebConnection()
        connections.append(connection)
        if target == start:
            return connection, _FakeWebResponse(302, location="/article")
        return connection, _FakeWebResponse(200, body=b"<html>public page</html>")

    monkeypatch.setattr(WebParser, "_resolve_target", staticmethod(resolve))
    monkeypatch.setattr(WebParser, "_request", staticmethod(request))

    assert WebParser._fetch(start) == "<html>public page</html>"
    assert events == [
        ("resolve", start),
        ("request", start),
        ("resolve", destination),
        ("request", destination),
    ]
    assert all(connection.closed for connection in connections)


def test_web_parser_blocks_private_redirect_before_request(monkeypatch):
    from skill_anything.parsers.web_parser import WebParser

    start = "https://example.com/start"
    private = "http://127.0.0.1/admin"
    events = []

    def resolve(url):
        events.append(("resolve", url))
        if url == private:
            raise ValueError("Unsafe web URL: resolves to non-public address")
        return url

    def request(target):
        events.append(("request", target))
        return _FakeWebConnection(), _FakeWebResponse(302, location=private)

    monkeypatch.setattr(WebParser, "_resolve_target", staticmethod(resolve))
    monkeypatch.setattr(WebParser, "_request", staticmethod(request))

    with pytest.raises(ValueError, match="non-public address"):
        WebParser._fetch(start)

    assert events == [
        ("resolve", start),
        ("request", start),
        ("resolve", private),
    ]


def test_video_parser_url_detection():
    from skill_anything.parsers.video_parser import VideoParser
    parser = VideoParser()
    assert parser._is_youtube_url("https://www.youtube.com/watch?v=abc123")
    assert parser._is_youtube_url("https://youtu.be/abc123")
    assert not parser._is_youtube_url("https://example.com")
    assert parser._is_subtitle_file("test.srt")
    assert parser._is_subtitle_file("test.vtt")
    assert not parser._is_subtitle_file("test.pdf")


def test_video_parser_srt_parsing():
    from skill_anything.parsers.video_parser import VideoParser
    srt = "1\n00:00:01,000 --> 00:00:05,000\nHello world\n\n2\n00:00:06,000 --> 00:00:10,000\nThis is a test"
    segments = VideoParser._parse_srt_text(srt)
    assert len(segments) == 2
    assert segments[0][1] == "Hello world"
    assert segments[1][1] == "This is a test"


def test_audio_parser_supported_extensions():
    from skill_anything.parsers.audio_parser import AudioParser
    expected = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg", ".wma"}
    assert AudioParser.SUPPORTED_EXTENSIONS == expected


def test_audio_parser_rejects_unsupported():
    from skill_anything.parsers.audio_parser import AudioParser
    parser = AudioParser()
    with pytest.raises(ValueError, match="Unsupported audio format"):
        parser.parse("test.pdf")


def test_audio_parser_rejects_missing_file():
    from skill_anything.parsers.audio_parser import AudioParser
    parser = AudioParser()
    with pytest.raises(FileNotFoundError, match="Audio file not found"):
        parser.parse("nonexistent.mp3")

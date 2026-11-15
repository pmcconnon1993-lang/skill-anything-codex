"""Web parser — extract knowledge from webpages."""

from __future__ import annotations

import http.client
import ipaddress
import logging
import re
import socket
import ssl
import urllib.error
from dataclasses import dataclass
from urllib.parse import urljoin, urlsplit

from skill_anything.models import KnowledgeChunk, Section, SourceType
from skill_anything.parsers.base import BaseParser

log = logging.getLogger(__name__)

_DEFAULT_PORTS = {"http": 80, "https": 443}
_MAX_REDIRECTS = 20
_REDIRECT_STATUSES = {301, 302, 303, 307, 308}
_REQUEST_TIMEOUT = 30.0
_USER_AGENT = "Mozilla/5.0 (compatible; SkillAnything/1.0)"


@dataclass(frozen=True)
class _ResolvedTarget:
    scheme: str
    host: str
    port: int
    request_target: str
    addresses: tuple[tuple, ...]


class WebParser(BaseParser):
    source_type = SourceType.WEBPAGE

    def parse_sections(self, source: str) -> list[Section]:
        if not source.startswith(("http://", "https://")):
            raise ValueError(f"Expected a URL, got: {source}")

        html = self._fetch(source)
        title, text = self._extract_content(html)
        return self._build_sections(text, title, source)

    @staticmethod
    def _fetch(url: str) -> str:
        current_url = url
        for redirect_count in range(_MAX_REDIRECTS + 1):
            target = WebParser._resolve_target(current_url)
            connection, response = WebParser._request(target)
            try:
                if response.status in _REDIRECT_STATUSES:
                    location = response.getheader("Location")
                    if not location:
                        raise urllib.error.HTTPError(
                            current_url,
                            response.status,
                            "Redirect response is missing a Location header",
                            response.headers,
                            None,
                        )
                    if redirect_count == _MAX_REDIRECTS:
                        raise ValueError(f"Too many redirects while fetching: {url}")
                    current_url = urljoin(current_url, location)
                    continue

                if not 200 <= response.status < 300:
                    raise urllib.error.HTTPError(
                        current_url,
                        response.status,
                        response.reason,
                        response.headers,
                        None,
                    )

                body = response.read()
                charset = response.headers.get_content_charset() or "utf-8"
                try:
                    return body.decode(charset, errors="replace")
                except LookupError:
                    return body.decode("utf-8", errors="replace")
            finally:
                connection.close()

        raise AssertionError("redirect loop terminated unexpectedly")

    @staticmethod
    def _resolve_target(url: str) -> _ResolvedTarget:
        """Validate a web URL and pin its public DNS results for one request."""
        try:
            parsed = urlsplit(url)
            host = parsed.hostname
            port = parsed.port
        except ValueError as exc:
            raise ValueError(f"Unsafe web URL: {exc}") from exc

        scheme = parsed.scheme.lower()
        if scheme not in _DEFAULT_PORTS or not host:
            raise ValueError(f"Expected an HTTP(S) URL, got: {url}")
        if parsed.username is not None or parsed.password is not None:
            raise ValueError("Unsafe web URL: credentials are not allowed")

        default_port = _DEFAULT_PORTS[scheme]
        if port not in (None, default_port):
            raise ValueError(
                f"Unsafe web URL: {scheme.upper()} requests must use port {default_port}"
            )

        if "%" in host:
            raise ValueError("Unsafe web URL: scoped IP addresses are not allowed")
        try:
            ascii_host = host.rstrip(".").encode("idna").decode("ascii")
        except UnicodeError as exc:
            raise ValueError("Unsafe web URL: invalid hostname") from exc
        if not ascii_host:
            raise ValueError("Unsafe web URL: hostname is required")

        try:
            resolved = socket.getaddrinfo(
                ascii_host,
                default_port,
                family=socket.AF_UNSPEC,
                type=socket.SOCK_STREAM,
            )
        except socket.gaierror as exc:
            raise ValueError(f"Could not resolve web URL host: {ascii_host}") from exc

        addresses: list[tuple] = []
        for family, socktype, proto, _canonname, sockaddr in resolved:
            if family not in (socket.AF_INET, socket.AF_INET6):
                continue
            address = ipaddress.ip_address(sockaddr[0].split("%", 1)[0])
            if not WebParser._is_public_address(address):
                raise ValueError(
                    f"Unsafe web URL: {ascii_host} resolves to non-public address {address}"
                )
            candidate = (family, socktype, proto, sockaddr)
            if candidate not in addresses:
                addresses.append(candidate)

        if not addresses:
            raise ValueError(f"Could not resolve web URL host: {ascii_host}")

        request_target = parsed.path or "/"
        if parsed.query:
            request_target = f"{request_target}?{parsed.query}"
        return _ResolvedTarget(
            scheme=scheme,
            host=ascii_host,
            port=default_port,
            request_target=request_target,
            addresses=tuple(addresses),
        )

    @staticmethod
    def _is_public_address(address: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
        if not address.is_global or address.is_multicast:
            return False
        if isinstance(address, ipaddress.IPv6Address):
            embedded = address.ipv4_mapped or address.sixtofour
            if embedded is not None and not WebParser._is_public_address(embedded):
                return False
            if address.teredo is not None:
                server, client = address.teredo
                if not all(WebParser._is_public_address(item) for item in (server, client)):
                    return False
        return True

    @staticmethod
    def _request(
        target: _ResolvedTarget,
    ) -> tuple[http.client.HTTPConnection, http.client.HTTPResponse]:
        sock = WebParser._connect(target)
        connection = http.client.HTTPConnection(
            target.host,
            target.port,
            timeout=_REQUEST_TIMEOUT,
        )
        connection.sock = sock
        host_header = f"[{target.host}]" if ":" in target.host else target.host
        try:
            connection.request(
                "GET",
                target.request_target,
                headers={"Host": host_header, "User-Agent": _USER_AGENT},
            )
            return connection, connection.getresponse()
        except Exception:
            connection.close()
            raise

    @staticmethod
    def _connect(target: _ResolvedTarget) -> socket.socket:
        """Connect only to an address returned by the validated resolution."""
        tls_context = ssl.create_default_context() if target.scheme == "https" else None
        last_error: OSError | None = None

        for family, socktype, proto, sockaddr in target.addresses:
            sock: socket.socket | None = None
            try:
                sock = socket.socket(family, socktype, proto)
                sock.settimeout(_REQUEST_TIMEOUT)
                sock.connect(sockaddr)
                if tls_context is not None:
                    sock = tls_context.wrap_socket(sock, server_hostname=target.host)
                return sock
            except OSError as exc:
                last_error = exc
                if sock is not None:
                    sock.close()

        raise ConnectionError(f"Could not connect to web URL host: {target.host}") from last_error

    def _extract_content(self, html: str) -> tuple[str, str]:
        """Extract readable text from HTML. Uses BeautifulSoup if available, else regex."""
        try:
            return self._extract_bs4(html)
        except ImportError:
            return self._extract_regex(html)

    @staticmethod
    def _extract_bs4(html: str) -> tuple[str, str]:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")

        for tag in soup(["script", "style", "nav", "header", "footer", "aside", "form"]):
            tag.decompose()

        title = soup.title.string.strip() if soup.title and soup.title.string else "Untitled"

        article = soup.find("article") or soup.find("main") or soup.find("body")
        if not article:
            article = soup

        paragraphs = []
        for elem in article.find_all(["p", "h1", "h2", "h3", "h4", "li", "blockquote", "pre"]):
            text = elem.get_text(strip=True)
            if len(text) > 20:
                if elem.name.startswith("h"):
                    text = f"\n## {text}\n"
                paragraphs.append(text)

        return title, "\n\n".join(paragraphs)

    @staticmethod
    def _extract_regex(html: str) -> tuple[str, str]:
        title_match = re.search(r"<title>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
        title = title_match.group(1).strip() if title_match else "Untitled"

        html = re.sub(r"<(script|style|nav|header|footer)[^>]*>.*?</\1>", "", html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r"<[^>]+>", "\n", html)
        html = re.sub(r"&nbsp;", " ", html)
        html = re.sub(r"&[a-z]+;", "", html)

        lines = [line.strip() for line in html.splitlines() if len(line.strip()) > 20]
        return title, "\n\n".join(lines)

    def _build_sections(
        self, text: str, title: str, source: str
    ) -> list[Section]:
        # The bs4 extractor already inserts "## heading" lines for h1..h4 tags.
        # Use the same heading-split logic as TextParser so long web pages
        # produce multiple sections instead of one giant blob.
        from skill_anything.parsers.text_parser import TextParser

        heading_sections = TextParser._split_by_headings(text)
        if not heading_sections or all(not h for h, _ in heading_sections):
            heading_sections = [(title or "Web Content", text)]

        sections: list[Section] = []
        chunk_idx = 0
        for sec_idx, (heading, body) in enumerate(heading_sections):
            if not body.strip():
                continue
            section_id = f"sec-{sec_idx + 1:03d}"
            section_title = heading or title or f"Section {sec_idx + 1}"
            section_chunks: list[KnowledgeChunk] = []
            for sub in self._split_into_chunks(body, max_chars=2000):
                section_chunks.append(
                    KnowledgeChunk(
                        content=sub,
                        section=section_title,
                        section_id=section_id,
                        chunk_index=chunk_idx,
                        metadata={"source": source, "title": title},
                    )
                )
                chunk_idx += 1
            if section_chunks:
                sections.append(
                    Section(
                        id=section_id,
                        title=section_title,
                        chunks=section_chunks,
                        metadata={"source": source, "title": title},
                    )
                )
        return sections

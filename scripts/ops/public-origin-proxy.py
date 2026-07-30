#!/usr/bin/env python3
"""Small always-on HTTP proxy for Cloudflare's legacy :7734 ingress."""

from __future__ import annotations

import http.client
import http.server
import os
import socket
import urllib.parse

ORIGIN = urllib.parse.urlparse(
    os.environ.get("AXON_X_ORIGIN", "http://127.0.0.1:4173")
)
ORIGIN_HOST = ORIGIN.hostname or "127.0.0.1"
ORIGIN_PORT = ORIGIN.port or 80
LISTEN_PORT = int(os.environ.get("AXON_PUBLIC_ORIGIN_PORT", "7734"))


class ProxyHandler(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt: str, *args: object) -> None:
        print(
            "[%s] %s" % (self.log_date_time_string(), fmt % args),
            flush=True,
        )

    def _proxy(self) -> None:
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length else None
        headers = {
            key: value
            for key, value in self.headers.items()
            if key.lower()
            not in {"host", "content-length", "transfer-encoding", "connection"}
        }
        headers["Host"] = f"{ORIGIN_HOST}:{ORIGIN_PORT}"
        headers["Connection"] = "close"
        connection = http.client.HTTPConnection(
            ORIGIN_HOST,
            ORIGIN_PORT,
            timeout=60,
        )
        try:
            connection.request(self.command, self.path, body=body, headers=headers)
            response = connection.getresponse()
            payload = response.read()
            self.send_response(response.status, response.reason)
            for key, value in response.getheaders():
                if key.lower() in {"transfer-encoding", "connection", "content-length"}:
                    continue
                self.send_header(key, value)
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Connection", "close")
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(payload)
        finally:
            connection.close()

    do_GET = _proxy
    do_POST = _proxy
    do_PUT = _proxy
    do_PATCH = _proxy
    do_DELETE = _proxy
    do_HEAD = _proxy
    do_OPTIONS = _proxy


class DualStackServer(http.server.ThreadingHTTPServer):
    """Listen on IPv4 and IPv6 so Cloudflare's localhost resolves either way."""

    address_family = socket.AF_INET6
    allow_reuse_address = True

    def server_bind(self) -> None:
        self.socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
        super().server_bind()


def main() -> None:
    with DualStackServer(("::", LISTEN_PORT), ProxyHandler) as server:
        print(
            f"proxy listening on [::]:{LISTEN_PORT} -> "
            f"{ORIGIN_HOST}:{ORIGIN_PORT}",
            flush=True,
        )
        server.serve_forever()


if __name__ == "__main__":
    main()

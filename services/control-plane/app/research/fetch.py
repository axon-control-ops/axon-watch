"""HTTPS fetch with SSRF guards and size limits."""

from __future__ import annotations

import html
import re
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.research.policy import load_policy, validate_url


def _strip_html(raw: str) -> str:
    without_scripts = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", raw)
    without_tags = re.sub(r"(?s)<[^>]+>", " ", without_scripts)
    collapsed = re.sub(r"\s+", " ", html.unescape(without_tags)).strip()
    return collapsed


def fetch_url(url: str) -> dict[str, object]:
    normalized, hostname = validate_url(url)
    policy = load_policy()
    max_bytes = int(policy.get("max_response_bytes") or 2_097_152)
    connect_timeout = int(policy.get("connect_timeout_seconds") or 5)
    total_timeout = int(policy.get("total_timeout_seconds") or 20)
    user_agent = str(policy.get("user_agent") or "Axon-X-Research/1.0")

    current = normalized
    redirects = 0
    max_redirects = int(policy.get("max_redirects") or 3)
    body = b""
    content_type = ""

    while True:
        request = Request(current, headers={"User-Agent": user_agent})
        try:
            with urlopen(request, timeout=total_timeout) as response:
                content_type = str(response.headers.get("Content-Type") or "")
                body = response.read(max_bytes + 1)
                if len(body) > max_bytes:
                    raise ValueError(f"response exceeded {max_bytes} bytes")
                final_url = str(response.geturl())
        except HTTPError as exc:
            raise ValueError(f"HTTP {exc.code} for {current}") from exc
        except URLError as exc:
            raise ValueError(f"fetch failed for {current}: {exc.reason}") from exc

        if final_url != current and redirects < max_redirects:
            current, hostname = validate_url(final_url)
            redirects += 1
            continue
        break

    charset = "utf-8"
    if "charset=" in content_type.lower():
        charset = content_type.lower().split("charset=", 1)[1].split(";", 1)[0].strip() or "utf-8"

    text = body.decode(charset, errors="replace")
    if "html" in content_type.lower():
        text = _strip_html(text)

    return {
        "url": final_url,
        "hostname": hostname,
        "title": hostname,
        "content": text[:12000],
        "content_type": content_type,
        "bytes_read": len(body),
    }

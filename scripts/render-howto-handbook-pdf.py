#!/usr/bin/env python3
"""Build Axon-X How-To Handbook PDF from docs/HOW-TO-HANDBOOK.md."""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path

import markdown

REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = REPO_ROOT / "docs"
SOURCE_MD = DOCS_DIR / "HOW-TO-HANDBOOK.md"
PRINT_CSS = DOCS_DIR / "how-to-handbook-print.css"
DEFAULT_HTML = DOCS_DIR / "HOW-TO-HANDBOOK.html"
DEFAULT_PDF = DOCS_DIR / "HOW-TO-HANDBOOK.pdf"
DEFAULT_DESKTOP_PDF = Path.home() / "Desktop" / "Axon-X-How-To-Handbook.pdf"

HOWTO_LINK_RE = re.compile(r"\]\((?:docs/)?how-to/([^)]+\.md)\)")

HEADING_RE = re.compile(r"^(#{2,3})\s+(.+)$")
VERIFIED_RE = re.compile(r"\*\*Last verified:\*\*\s*(.+?)(?:\n\n|\Z)", re.S)
NUMBERED_SECTION_RE = re.compile(r"^\d+\.\s")
PROBLEM_SECTION_RE = re.compile(r"^Problem:\s", re.I)
TIP_SECTION_RE = re.compile(r"^Tip\s+\d+:", re.I)


def demote_headings(text: str, levels: int = 1) -> str:
    out: list[str] = []
    for line in text.splitlines():
        match = re.match(r"^(#+)\s", line)
        if match:
            hashes = "#" * (len(match.group(1)) + levels)
            line = f"{hashes}{line[len(match.group(1)):]}"
        out.append(line)
    return "\n".join(out)


def bundle_howto_chapters(markdown_text: str) -> str:
    """Inline linked docs/how-to/*.md chapters so the PDF is self-contained."""
    seen: set[str] = set()
    appendices: list[str] = []
    for match in HOWTO_LINK_RE.finditer(markdown_text):
        rel = f"how-to/{match.group(1)}"
        if rel in seen:
            continue
        path = DOCS_DIR / rel
        if not path.is_file():
            continue
        seen.add(rel)
        body = demote_headings(path.read_text(encoding="utf-8").strip(), levels=1)
        appendices.append(f"\n\n---\n\n{body}\n")
    return markdown_text + "".join(appendices)


def chrome_binary() -> str | None:
    for candidate in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser"):
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
    return None


def slugify(text: str) -> str:
    cleaned = re.sub(r"[*_`]", "", text).strip().lower()
    cleaned = re.sub(r"[^a-z0-9]+", "-", cleaned)
    return cleaned.strip("-")


def is_major_section(title: str) -> bool:
    if NUMBERED_SECTION_RE.match(title):
        return False
    if PROBLEM_SECTION_RE.match(title):
        return False
    if TIP_SECTION_RE.match(title):
        return False
    lowered = title.lower()
    if lowered.startswith("shared contract verification"):
        return False
    if lowered.startswith("contract verification"):
        return False
    if lowered.startswith("full current verification bundle"):
        return False
    if lowered.startswith("frontend checks"):
        return False
    if lowered.startswith("python syntax checks"):
        return False
    if lowered.startswith("service tests"):
        return False
    if lowered.startswith("when adding "):
        return False
    return True


def extract_toc(markdown_text: str) -> list[tuple[str, str, int]]:
    entries: list[tuple[str, str, int]] = []
    for line in markdown_text.splitlines():
        match = HEADING_RE.match(line)
        if not match:
            continue
        level = len(match.group(1))
        title = match.group(2).strip()
        if level == 2 and is_major_section(title):
            entries.append((slugify(title), title, level))
    return entries


def extract_verified_line(markdown_text: str) -> str | None:
    match = VERIFIED_RE.search(markdown_text)
    if not match:
        return None
    return re.sub(r"\s+", " ", match.group(1).strip())


def inject_heading_ids(html: str, toc: list[tuple[str, str, int]]) -> str:
    for slug, title, _level in toc:
        pattern = re.compile(
            rf"<h2>({re.escape(title)})</h2>",
            re.I,
        )
        html, count = pattern.subn(rf'<h2 id="{slug}">\1</h2>', html, count=1)
        if count == 0:
            loose = re.compile(rf"<h2>(.*?{re.escape(title)}.*?)</h2>", re.I)
            html, _ = loose.subn(rf'<h2 id="{slug}">\1</h2>', html, count=1)
    return html


def wrap_major_chapters(html: str, toc: list[tuple[str, str, int]]) -> str:
    major = {slug: index for index, (slug, _title, _level) in enumerate(toc, start=1)}
    heading_re = re.compile(r'<h2 id="([a-z0-9-]+)">(.*?)</h2>', re.S)
    parts = heading_re.split(html)
    if len(parts) < 3:
        return html

    rebuilt: list[str] = [parts[0]]
    index = 1
    while index < len(parts):
        slug = parts[index]
        title_html = parts[index + 1]
        body_chunk = parts[index + 2] if index + 2 < len(parts) else ""
        index += 3

        if slug not in major:
            rebuilt.append(f'<h2 id="{slug}">{title_html}</h2>{body_chunk}')
            continue

        chapter_num = major[slug]
        rebuilt.append(
            f'<section class="chapter" id="chapter-{slug}">'
            f'<div class="chapter-header">'
            f'<span class="chapter-num">{chapter_num:02d}</span>'
            f'<h2 id="{slug}">{title_html}</h2>'
            f"</div>"
            f'<div class="chapter-body">{body_chunk}</div>'
            f"</section>"
        )
    return "".join(rebuilt)


def intro_panel_html() -> str:
    return """
<section class="intro-panel">
  <h2>Read this first</h2>
  <p>Practical guide for operators, reviewers, and developers working in the <strong>axon-watch</strong> repo — the greenfield home of <strong>Axon-X</strong>.</p>
  <ul>
    <li>Plans live in <code>axon-local/Plans/Axon-Watch/</code> — implement here, don't redefine semantics there.</li>
    <li>Start with <code>./scripts/dev/up.sh</code>, verify with <code>npm run verify</code>.</li>
    <li>Treat bootstrap-real and feature-real as different things — see parity ledger before assuming parity.</li>
  </ul>
</section>
"""


def markdown_to_html(text: str) -> str:
    return markdown.markdown(
        text,
        extensions=["tables", "fenced_code", "sane_lists"],
        output_format="html5",
    )


def cover_html(verified: str | None) -> str:
    verified_line = verified or "See source markdown for latest verification stamp"
    generated = datetime.now().strftime("%d %b %Y")
    return f"""
<section class="cover-page">
  <div class="cover-inner">
    <div class="cover-brand">
      <div class="cover-logo">AX</div>
      <div class="cover-brand-text">Axon-X · axon-watch</div>
    </div>
    <div class="cover-hero">
      <h1 class="cover-title">How-To <em>Handbook</em></h1>
      <p class="cover-subtitle">Your field guide for bootstrapping, verifying, troubleshooting, and shipping thin slices in the next-generation operator console.</p>
      <div class="cover-pills">
        <span class="cover-pill">Shell <code>:4173</code></span>
        <span class="cover-pill">Control plane <code>:8787</code></span>
        <span class="cover-pill">Watch <code>:8788</code></span>
      </div>
    </div>
    <div class="cover-footer">
      <div class="cover-meta">
        <strong>Last verified</strong> · {verified_line}<br/>
        Generated {generated}
      </div>
      <div class="cover-chips">
        <span class="cover-chip">console-web</span>
        <span class="cover-chip">control-plane</span>
        <span class="cover-chip">shared-types</span>
      </div>
    </div>
  </div>
</section>
"""


def toc_html(entries: list[tuple[str, str, int]]) -> str:
    items = "".join(
        f'<li class="toc-card"><span class="toc-num">{index}</span>'
        f'<a href="#chapter-{slug}">{title}</a></li>'
        for index, (slug, title, _level) in enumerate(entries, start=1)
    )
    return f"""
<nav class="toc" id="table-of-contents">
  <div class="toc-header">
    <div class="toc-kicker">Field guide</div>
    <h2>16 chapters</h2>
  </div>
  <ol class="toc-grid">{items}</ol>
</nav>
"""


def strip_doc_preamble(html: str) -> str:
    match = re.search(r'<section class="chapter"', html)
    if not match:
        return html
    return html[match.start():]


def build_html(markdown_text: str) -> str:
    toc = extract_toc(markdown_text)
    verified = extract_verified_line(markdown_text)
    raw_body = inject_heading_ids(markdown_to_html(markdown_text), toc)
    body = strip_doc_preamble(wrap_major_chapters(raw_body, toc))
    css_href = PRINT_CSS.resolve().as_uri()
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>Axon-X How-To Handbook</title>
  <link rel="stylesheet" href="{css_href}" />
</head>
<body>
  <main class="page">
    {cover_html(verified)}
    {toc_html(toc)}
    {intro_panel_html()}
    <article class="doc-body">
      {body}
    </article>
    <footer class="doc-footer">
      <span>Axon-X How-To Handbook</span>
      <span>docs/HOW-TO-HANDBOOK.md</span>
    </footer>
  </main>
</body>
</html>
"""


def render_pdf(html_path: Path, pdf_path: Path) -> None:
    chrome = chrome_binary()
    if chrome is None:
        raise SystemExit("No Chrome/Chromium binary found for PDF rendering.")
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        chrome,
        "--headless=new",
        "--disable-gpu",
        "--no-sandbox",
        "--no-pdf-header-footer",
        f"--print-to-pdf={pdf_path}",
        html_path.resolve().as_uri(),
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if not pdf_path.is_file() or pdf_path.stat().st_size < 2000:
        raise SystemExit(f"PDF render failed or too small: {pdf_path}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default=str(DEFAULT_PDF), help="Repo PDF output path")
    parser.add_argument(
        "--desktop",
        default=str(DEFAULT_DESKTOP_PDF),
        help="Desktop PDF copy (pass empty string to skip)",
    )
    parser.add_argument("--html", default=str(DEFAULT_HTML), help="HTML preview path")
    args = parser.parse_args()

    if not SOURCE_MD.is_file():
        raise SystemExit(f"Missing handbook source: {SOURCE_MD}")
    if not PRINT_CSS.is_file():
        raise SystemExit(f"Missing print CSS: {PRINT_CSS}")

    markdown_text = bundle_howto_chapters(SOURCE_MD.read_text(encoding="utf-8"))
    html_text = build_html(markdown_text)

    html_path = Path(args.html).expanduser().resolve()
    pdf_path = Path(args.output).expanduser().resolve()
    html_path.write_text(html_text, encoding="utf-8")

    with tempfile.TemporaryDirectory(prefix="axon-howto-pdf-") as tmp:
        tmp_html = Path(tmp) / "how-to-handbook.html"
        tmp_html.write_text(html_text, encoding="utf-8")
        render_pdf(tmp_html, pdf_path)

    print(f"HTML: {html_path}")
    print(f"PDF:  {pdf_path} ({pdf_path.stat().st_size:,} bytes)")

    desktop_arg = str(args.desktop).strip()
    if desktop_arg:
        desktop_pdf = Path(desktop_arg).expanduser().resolve()
        desktop_pdf.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(pdf_path, desktop_pdf)
        print(f"Desktop: {desktop_pdf} ({desktop_pdf.stat().st_size:,} bytes)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

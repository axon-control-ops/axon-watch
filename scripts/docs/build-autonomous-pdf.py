#!/usr/bin/env python3
"""Render Axon-X autonomy docs to Desktop/AUTONOMOUS.pdf."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path

import markdown

REPO_ROOT = Path(__file__).resolve().parents[2]
DOCS_DIR = REPO_ROOT / "docs"
PRINT_CSS = DOCS_DIR / "how-to-handbook-print.css"
PLAN_MD = DOCS_DIR / "AXON-X-AUTONOMY-MASTER-PLAN.md"
READINESS_MD = DOCS_DIR / "AXON-X-AUTONOMY-READINESS.md"
REPO_PDF = DOCS_DIR / "AUTONOMOUS.pdf"
DESKTOP_PDF = Path.home() / "Desktop" / "AUTONOMOUS.pdf"


def chrome_binary() -> str | None:
    for candidate in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser"):
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
    return None


def md_to_html_fragment(text: str) -> str:
    return markdown.markdown(
        text,
        extensions=["tables", "fenced_code", "toc", "sane_lists", "nl2br"],
        output_format="html5",
    )


def build_html() -> str:
    if not PLAN_MD.is_file():
        raise SystemExit(f"Missing plan: {PLAN_MD}")
    if not READINESS_MD.is_file():
        raise SystemExit(f"Missing readiness: {READINESS_MD}")
    if not PRINT_CSS.is_file():
        raise SystemExit(f"Missing print CSS: {PRINT_CSS}")

    plan_html = md_to_html_fragment(PLAN_MD.read_text(encoding="utf-8"))
    readiness_html = md_to_html_fragment(READINESS_MD.read_text(encoding="utf-8"))
    css_href = PRINT_CSS.resolve().as_uri()
    generated = datetime.now().strftime("%Y-%m-%d %H:%M")

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>AUTONOMOUS — Axon-X Autonomy Plan</title>
  <link rel="stylesheet" href="{css_href}" />
  <style>
    .cover-page h1 {{ font-size: 3rem; letter-spacing: 0.04em; }}
    .cover-page .cover-kicker {{ text-transform: uppercase; letter-spacing: 0.18em; opacity: 0.85; }}
    .cover-meta {{ margin-top: 2rem; opacity: 0.9; }}
    .section-break {{ break-before: page; page-break-before: always; }}
    .doc-body table {{ font-size: 0.92em; }}
    .doc-body pre, .doc-body code {{ font-size: 0.86em; }}
  </style>
</head>
<body>
  <main class="page">
    <section class="cover-page">
      <p class="cover-kicker">Axon-X</p>
      <h1>AUTONOMOUS</h1>
      <p>Master plan for bounded DashPro autonomy and the Axon-X mobile control plane.</p>
      <div class="cover-meta">
        <p>Generated {generated}</p>
        <p>Source: docs/AXON-X-AUTONOMY-MASTER-PLAN.md</p>
        <p>Assessment: docs/AXON-X-AUTONOMY-READINESS.md</p>
      </div>
    </section>

    <article class="doc-body">
      {plan_html}
    </article>

    <section class="section-break"></section>

    <article class="doc-body">
      <h1>Appendix — Autonomy readiness assessment</h1>
      {readiness_html}
    </article>

    <footer class="doc-footer">
      <span>AUTONOMOUS</span>
      <span>Axon-X · bounded autonomy plan</span>
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
    html_text = build_html()
    with tempfile.TemporaryDirectory(prefix="axon-autonomous-pdf-") as tmp:
        tmp_html = Path(tmp) / "autonomous.html"
        tmp_html.write_text(html_text, encoding="utf-8")
        render_pdf(tmp_html, REPO_PDF)

    DESKTOP_PDF.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(REPO_PDF, DESKTOP_PDF)
    print(f"Repo PDF: {REPO_PDF} ({REPO_PDF.stat().st_size:,} bytes)")
    print(f"Desktop:  {DESKTOP_PDF} ({DESKTOP_PDF.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

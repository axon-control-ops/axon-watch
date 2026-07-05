#!/usr/bin/env python3
"""Build print-ready HTML and PDF for docs/AXON-X-STARTER-GUIDE.md."""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

import markdown

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE = REPO_ROOT / "docs" / "AXON-X-STARTER-GUIDE.md"
HTML_OUT = REPO_ROOT / "docs" / "AXON-X-STARTER-GUIDE.html"
PDF_OUT = REPO_ROOT / "docs" / "AXON-X-STARTER-GUIDE.pdf"

PRINT_CSS = """
@page {
  size: A4;
  margin: 18mm 16mm 20mm 16mm;
}
* { box-sizing: border-box; }
body {
  font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
  font-size: 10.5pt;
  line-height: 1.45;
  color: #1a1a1a;
  max-width: 100%;
  margin: 0;
  padding: 0;
}
.cover {
  page-break-after: always;
  min-height: 90vh;
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 12mm 0;
}
.cover h1 {
  font-size: 28pt;
  margin: 0 0 8mm 0;
  letter-spacing: -0.02em;
}
.cover .subtitle {
  font-size: 13pt;
  color: #444;
  margin-bottom: 10mm;
}
.cover .meta {
  font-size: 10pt;
  color: #666;
  border-top: 1px solid #ddd;
  padding-top: 6mm;
}
h1, h2, h3 { color: #0f172a; page-break-after: avoid; }
h2 {
  font-size: 15pt;
  margin-top: 7mm;
  border-bottom: 1px solid #e2e8f0;
  padding-bottom: 2mm;
}
h3 { font-size: 12pt; margin-top: 5mm; }
p, li { orphans: 3; widows: 3; }
ul, ol { padding-left: 5mm; }
li { margin-bottom: 1.5mm; }
table {
  width: 100%;
  border-collapse: collapse;
  font-size: 9.5pt;
  margin: 4mm 0 6mm 0;
  page-break-inside: avoid;
}
th, td {
  border: 1px solid #cbd5e1;
  padding: 2.5mm 3mm;
  text-align: left;
  vertical-align: top;
}
th { background: #f1f5f9; font-weight: 600; }
code, pre {
  font-family: "SFMono-Regular", Consolas, "Liberation Mono", monospace;
  font-size: 9pt;
}
pre {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 4px;
  padding: 3mm 4mm;
  overflow-x: auto;
  page-break-inside: avoid;
}
code {
  background: #f1f5f9;
  padding: 0.5mm 1.5mm;
  border-radius: 3px;
}
hr {
  border: none;
  border-top: 1px solid #e2e8f0;
  margin: 6mm 0;
}
blockquote {
  margin: 4mm 0;
  padding: 3mm 4mm;
  border-left: 3px solid #64748b;
  background: #f8fafc;
  color: #334155;
}
.toc {
  page-break-after: always;
}
.toc h2 { border: none; }
.toc ul { list-style: none; padding-left: 0; }
.toc li { margin-bottom: 2mm; }
.footer-note {
  margin-top: 8mm;
  font-size: 9pt;
  color: #64748b;
}
@media print {
  a { color: inherit; text-decoration: none; }
}
"""


def _extract_title_block(text: str) -> tuple[str, str]:
    lines = text.splitlines()
    title = "Axon-X Starter Guide"
    subtitle = "Operator onboarding for the early bootstrap stage"
    if lines and lines[0].startswith("# "):
        title = lines[0][2:].strip()
    for line in lines[1:8]:
        if line.startswith("**For:**"):
            subtitle = line.replace("**For:**", "").strip()
            break
    return title, subtitle


def _build_toc(html_body: str) -> str:
    headings = re.findall(r"<h2 id=\"([^\"]+)\">([^<]+)</h2>", html_body)
    if not headings:
        headings = re.findall(r"<h2>([^<]+)</h2>", html_body)
        headings = [(re.sub(r"[^a-z0-9]+", "-", h.lower()).strip("-"), h) for h in headings]
    items = "".join(f'<li><a href="#{slug}">{label}</a></li>' for slug, label in headings)
    return f'<div class="toc"><h2>Contents</h2><ul>{items}</ul></div>'


def build_html() -> str:
    source_text = SOURCE.read_text(encoding="utf-8")
    title, subtitle = _extract_title_block(source_text)
    body_html = markdown.markdown(
        source_text,
        extensions=["tables", "fenced_code", "toc"],
        output_format="html5",
    )
    toc_html = _build_toc(body_html)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>{title}</title>
  <style>{PRINT_CSS}</style>
</head>
<body>
  <section class="cover">
    <h1>{title}</h1>
    <p class="subtitle">{subtitle}</p>
    <p class="meta">
      Axon-X · http://127.0.0.1:4173 · axon-watch repo<br />
      Early bootstrap guide · 2026-07-05 · Read in layers — you do not need the whole system at once.
    </p>
  </section>
  {toc_html}
  <main>{body_html}</main>
  <p class="footer-note">Generated from docs/AXON-X-STARTER-GUIDE.md · Rebuild: ./scripts/docs/build-starter-guide-pdf.sh</p>
</body>
</html>
"""


def build_pdf_with_chrome(html_path: Path, pdf_path: Path) -> bool:
    chrome = None
    for candidate in ("google-chrome-stable", "google-chrome", "chromium", "chromium-browser"):
        found = shutil.which(candidate)
        if found:
            chrome = found
            break
    if not chrome:
        return False

    html_url = html_path.resolve().as_uri()
    result = subprocess.run(
        [
            chrome,
            "--headless=new",
            "--disable-gpu",
            "--no-sandbox",
            f"--print-to-pdf={pdf_path}",
            html_url,
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0 and pdf_path.is_file() and pdf_path.stat().st_size > 0


def build_pdf_with_fpdf(html_path: Path, pdf_path: Path) -> None:
    from fpdf import FPDF

    text = SOURCE.read_text(encoding="utf-8")
    pdf = FPDF(format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 18)
    pdf.multi_cell(0, 10, "Axon-X Starter Guide")
    pdf.ln(4)
    pdf.set_font("Helvetica", "", 10)
    for line in text.splitlines():
        clean = line.strip()
        if not clean:
            pdf.ln(3)
            continue
        if clean.startswith("# "):
            pdf.ln(4)
            pdf.set_font("Helvetica", "B", 14)
            pdf.multi_cell(0, 7, clean[2:])
            pdf.set_font("Helvetica", "", 10)
            continue
        if clean.startswith("## "):
            pdf.ln(3)
            pdf.set_font("Helvetica", "B", 12)
            pdf.multi_cell(0, 6, clean[3:])
            pdf.set_font("Helvetica", "", 10)
            continue
        if clean.startswith("### "):
            pdf.ln(2)
            pdf.set_font("Helvetica", "B", 11)
            pdf.multi_cell(0, 6, clean[4:])
            pdf.set_font("Helvetica", "", 10)
            continue
        if clean.startswith("|") or clean.startswith("```"):
            continue
        if clean.startswith("- "):
            pdf.multi_cell(0, 5, f"  • {clean[2:]}")
            continue
        pdf.multi_cell(0, 5, clean)
    pdf.output(str(pdf_path))


def main() -> int:
    if not SOURCE.is_file():
        print(f"Missing source: {SOURCE}", file=sys.stderr)
        return 1

    html = build_html()
    HTML_OUT.write_text(html, encoding="utf-8")
    print(f"Wrote {HTML_OUT.relative_to(REPO_ROOT)}")

    if build_pdf_with_chrome(HTML_OUT, PDF_OUT):
        print(f"Wrote {PDF_OUT.relative_to(REPO_ROOT)} (Chrome print)")
        return 0

    print("Chrome PDF unavailable; using fpdf fallback", file=sys.stderr)
    build_pdf_with_fpdf(HTML_OUT, PDF_OUT)
    print(f"Wrote {PDF_OUT.relative_to(REPO_ROOT)} (fpdf fallback)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

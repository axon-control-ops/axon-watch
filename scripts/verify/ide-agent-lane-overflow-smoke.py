#!/usr/bin/env python3
"""Headed Playwright smoke: IDE Agent lane transcript must not overflow horizontally."""

from __future__ import annotations

import argparse
import json
import sys
import textwrap
import urllib.error
import urllib.request


LONG_AGENT_TEXT = textwrap.dedent(
    """\
    Lane B (agent) cannot start because no CLI runtime is ready: Cursor auth probe timed out.
    Run `cursor agent status` manually.; Codex/OpenAI API key was rejected. Fix keys in /vault
    or run `codex login`.; Authenticated via unlocked Axon-X vault.; Vault provider keys are
    available for CLI runtimes.. Open Runtime or /vault, then retry.
    https://www.youtube.com/watch?v=I-cvxBMue08&feature=share&utm_source=very-long-tracking-parameter
    """
)

LONG_MARKDOWN = textwrap.dedent(
    """\
    The search request itself was denied before it could run, so I'm testing a plain public fetch
    next to confirm whether general web access is still being blocked at the same layer.
    The search request itself was denied before it could run, so I'm testing a plain public fetch
    next to confirm whether general web access is still being blocked at the same layer.
    """
)


def _fetch(url: str, timeout_seconds: float) -> None:
    request = urllib.request.Request(url, headers={"Accept": "text/html"})
    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
        response.read()


def _inject_transcript_fixture() -> str:
    """Return JS that injects realistic transcript markup into the IDE agent dock."""
    payload = json.dumps({"agent": LONG_AGENT_TEXT, "markdown": LONG_MARKDOWN})
    return f"""
    () => {{
      const transcript = document.querySelector('.agent-dock__transcript .conversation-seam');
      if (!transcript) {{
        throw new Error('agent transcript container not found');
      }}

      const {{ agent: longAgent, markdown: longMarkdown }} = {payload};

      transcript.innerHTML = `
        <ul class="conversation-seam__list">
          <li class="conversation-seam__item conversation-seam__item--agent">
            <div class="conversation-seam__meta">
              <span class="conversation-seam__role">AGENT</span>
              <span class="conversation-seam__run-chip" title="run_2f6b9b">run run_2f6b9b...</span>
              <time class="conversation-seam__time">7 Jul, 12:21</time>
            </div>
            <div class="conversation-seam__blocks">
              <div class="conversation-seam__markdown-block">
                <div class="conversation-seam__markdown-toolbar">
                  <div class="conversation-seam__markdown-mode-toggle" role="group" aria-label="Markdown view mode">
                    <button type="button" class="conversation-seam__markdown-mode-button conversation-seam__markdown-mode-button--active">Preview</button>
                    <button type="button" class="conversation-seam__markdown-mode-button">Raw</button>
                  </div>
                  <button type="button" class="conversation-seam__block-button">Copy</button>
                </div>
                <div class="conversation-seam__content conversation-seam__content--markdown">
                  <p>${{longMarkdown}}</p>
                </div>
              </div>
              <p class="conversation-seam__content conversation-seam__content--agent">${{longAgent}}</p>
            </div>
          </li>
          <li class="conversation-seam__item conversation-seam__item--operator">
            <div class="conversation-seam__meta">
              <span class="conversation-seam__role">OPERATOR</span>
              <time class="conversation-seam__time">7 Jul, 12:20</time>
            </div>
            <p class="conversation-seam__content">search for this video: https://www.youtube.com/watch?v=I-cvxBMue08</p>
          </li>
        </ul>
      `;
    }}
    """


def _overflow_report_js() -> str:
    return """
    () => {
      const selectors = [
        '.agent-dock__transcript',
        '.agent-dock__transcript .conversation-seam',
        '.agent-dock__transcript .conversation-seam__list',
        '.agent-dock__transcript .conversation-seam__item',
        '.agent-dock__transcript .conversation-seam__content',
        '.agent-dock__transcript .conversation-seam__content--agent',
        '.agent-dock__transcript .conversation-seam__content--markdown',
        '.agent-dock__transcript .conversation-seam__markdown-block',
      ];

      const failures = [];
      const tolerance = 2;

      for (const selector of selectors) {
        for (const el of document.querySelectorAll(selector)) {
          if (el.scrollWidth > el.clientWidth + tolerance) {
            failures.push({
              selector,
              scrollWidth: el.scrollWidth,
              clientWidth: el.clientWidth,
              overflowPx: el.scrollWidth - el.clientWidth,
              sample: (el.textContent || '').trim().slice(0, 96),
            });
          }
        }
      }

      const docOverflow = document.documentElement.scrollWidth - window.innerWidth;
      if (docOverflow > tolerance) {
        failures.push({
          selector: 'document',
          scrollWidth: document.documentElement.scrollWidth,
          clientWidth: window.innerWidth,
          overflowPx: docOverflow,
          sample: 'page horizontal scrollbar',
        });
      }

      const dock = document.querySelector('.agent-dock');
      const dockRect = dock ? dock.getBoundingClientRect() : null;
      const viewportWidth = window.innerWidth;
      const markdownBlock = document.querySelector('.agent-dock__transcript .conversation-seam__markdown-block');
      const markdownParent = markdownBlock ? markdownBlock.parentElement : null;
      const markdownBlockRect = markdownBlock ? markdownBlock.getBoundingClientRect() : null;
      const markdownParentRect = markdownParent ? markdownParent.getBoundingClientRect() : null;
      const markdownWidthRatio = markdownBlockRect && markdownParentRect
        ? markdownBlockRect.width / markdownParentRect.width
        : null;

      if (markdownWidthRatio !== null && markdownWidthRatio < 0.98) {
        failures.push({
          selector: '.conversation-seam__markdown-block',
          scrollWidth: markdownBlockRect.width,
          clientWidth: markdownParentRect.width,
          overflowPx: markdownParentRect.width - markdownBlockRect.width,
          sample: `markdown block width ratio ${markdownWidthRatio.toFixed(3)}`,
        });
      }

      const previewToggle = document.querySelector('.conversation-seam__markdown-mode-button');
      const rawToggle = document.querySelectorAll('.conversation-seam__markdown-mode-button')[1];
      if (!previewToggle || !rawToggle) {
        failures.push({
          selector: '.conversation-seam__markdown-mode-toggle',
          scrollWidth: 0,
          clientWidth: 0,
          overflowPx: 0,
          sample: 'missing Preview/Raw toggle',
        });
      }

      return {
        failures,
        viewportWidth,
        dockRight: dockRect ? dockRect.right : null,
        dockWidth: dockRect ? dockRect.width : null,
        markdownWidthRatio,
      };
    }
    """


def run_smoke(
    *,
    console_base_url: str,
    headed: bool,
    timeout_seconds: float,
    pause_seconds: float,
    viewport_width: int,
    viewport_height: int,
) -> dict[str, object]:
    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
    from playwright.sync_api import sync_playwright

    console_base = console_base_url.rstrip("/")
    _fetch(console_base, timeout_seconds)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=not headed, slow_mo=80 if headed else 0)
        try:
            context = browser.new_context(
                viewport={"width": viewport_width, "height": viewport_height}
            )
            context.add_init_script(
                "sessionStorage.setItem('axon-x-boot-complete', '1');"
            )
            page = context.new_page()
            page.goto(console_base, wait_until="domcontentloaded", timeout=int(timeout_seconds * 1000))
            page.wait_for_selector(".console-shell--mockup", timeout=int(timeout_seconds * 1000))

            ide_button = page.get_by_role("button", name="IDE", exact=True)
            ide_button.click()
            page.wait_for_selector(
                ".console-shell--mockup[data-layout-mode='ide']",
                timeout=int(timeout_seconds * 1000),
            )
            page.wait_for_selector(".agent-dock__transcript", timeout=int(timeout_seconds * 1000))

            page.evaluate(_inject_transcript_fixture())
            page.wait_for_timeout(250)

            report = page.evaluate(_overflow_report_js())

            if pause_seconds > 0 and headed:
                page.wait_for_timeout(int(pause_seconds * 1000))

        except PlaywrightTimeoutError as exc:
            raise RuntimeError(f"IDE agent lane smoke timed out: {exc}") from exc
        finally:
            browser.close()

    return report


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--console-base-url",
        default="http://127.0.0.1:4173",
        help="Console dev server base URL",
    )
    parser.add_argument(
        "--headed",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Run Chromium headed (default: true)",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=45.0,
        help="Navigation and selector timeout",
    )
    parser.add_argument(
        "--pause-seconds",
        type=float,
        default=2.0,
        help="Headed pause before closing browser (0 to skip)",
    )
    parser.add_argument(
        "--viewport-width",
        type=int,
        default=1440,
        help="Browser viewport width",
    )
    parser.add_argument(
        "--viewport-height",
        type=int,
        default=900,
        help="Browser viewport height",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    try:
        report = run_smoke(
            console_base_url=args.console_base_url,
            headed=args.headed,
            timeout_seconds=args.timeout_seconds,
            pause_seconds=args.pause_seconds,
            viewport_width=args.viewport_width,
            viewport_height=args.viewport_height,
        )
    except urllib.error.URLError as exc:
        print(json.dumps({"status": "fail", "error": f"console unreachable: {exc}"}, indent=2))
        return 1
    except RuntimeError as exc:
        print(json.dumps({"status": "fail", "error": str(exc)}, indent=2))
        return 1
    except ImportError:
        print(json.dumps({"status": "fail", "error": "playwright not installed"}, indent=2))
        return 1

    failures = report.get("failures", [])
    payload = {
        "status": "pass" if not failures else "fail",
        "console_base_url": args.console_base_url,
        "headed": args.headed,
        "viewportWidth": report.get("viewportWidth"),
        "dockWidth": report.get("dockWidth"),
        "dockRight": report.get("dockRight"),
        "overflowFailures": failures,
    }
    print(json.dumps(payload, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())

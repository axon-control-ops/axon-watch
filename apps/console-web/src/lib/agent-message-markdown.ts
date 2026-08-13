import { marked } from 'marked';

import { linkifyWorkspacePathsInMarkdown } from './agent-markdown-file-links';
import { agentContentHasTranscriptBlocks } from './agent-transcript-blocks';
import { rewriteMarkdownImageSources } from './thread-image-url';

marked.setOptions({
  breaks: true,
  gfm: true,
});

marked.use({
  hooks: {
    postprocess(html) {
      return html.replace(/<table>/g, '<div class="markdown-table-wrap"><table>').replace(
        /<\/table>/g,
        '</table></div>',
      );
    },
  },
});

/**
 * Agents often emit key/value credential tables with empty/malformed headers:
 *   | |
 *   |---|---|
 *   | Username | alice |
 * marked/GFM will not parse that as a <table>, so pipes show as raw prose.
 * Promote empty headers to Field/Value (or Col N) using the divider width.
 */
export function normalizeEmptyHeaderMarkdownTables(markdown: string): string {
  const lines = String(markdown || '').split('\n');
  const out: string[] = [];
  for (let i = 0; i < lines.length; i += 1) {
    const header = lines[i] ?? '';
    const divider = lines[i + 1] ?? '';
    const dividerCells = divider.match(/\|/g);
    const dividerOk = /^\|\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$/.test(divider);
    const headerLooksEmpty = /^\|\s*(\|\s*)+$/.test(header.trim());
    if (headerLooksEmpty && dividerOk && dividerCells && dividerCells.length >= 3) {
      const columnCount = dividerCells.length - 1;
      const labels =
        columnCount === 2
          ? ['Field', 'Value']
          : Array.from({ length: columnCount }, (_, index) => `Col ${index + 1}`);
      out.push(`| ${labels.join(' | ')} |`);
      out.push(divider);
      i += 1;
      continue;
    }
    out.push(header);
  }
  return out.join('\n');
}

/**
 * Repair common agent prose that breaks GFM so replies don't show as raw pipes/bullets.
 * Example bug: `**Here's where things stand*| Step | … |` (bold glued to table).
 */
export function normalizeAgentProseMarkdown(markdown: string): string {
  let text = String(markdown || '').replace(/\r\n/g, '\n');
  if (!text.trim()) {
    return text;
  }

  // Unicode bullets → GFM list markers.
  text = text.replace(/(^|\n)\s*[•‣▪◦]\s+/g, '$1- ');

  // Bold label glued into a table header: **Title*| Col | → **Title**\n\n| Col |
  text = text.replace(
    /\*\*([^*\n|]+?)\*\|(\s*[^|\n]+\|)/g,
    (_full, title: string, rest: string) => `**${title.trim()}**\n\n|${rest}`,
  );
  // Same pattern without the stray closing star: **Title| Col |
  text = text.replace(
    /\*\*([^*\n|]+)\|(\s*[^|\n]+\|)/g,
    (_full, title: string, rest: string) => `**${title.trim()}**\n\n|${rest}`,
  );

  // Ensure a blank line before a GFM table that follows prose on the previous line.
  const lines = text.split('\n');
  const out: string[] = [];
  for (let i = 0; i < lines.length; i += 1) {
    const line = lines[i] ?? '';
    const prev = out.length ? (out[out.length - 1] ?? '') : '';
    const isTableRow = /^\|.+\|\s*$/.test(line.trim());
    const prevIsTable = /^\|.+\|\s*$/.test(prev.trim()) || /^\|?\s*:?-{3,}/.test(prev.trim());
    if (isTableRow && prev.trim() && !prevIsTable) {
      out.push('');
    }
    out.push(line);
  }
  return out.join('\n');
}

const MARKDOWN_HINT_PATTERN =
  /(^|\n)\s{0,3}(#{1,6}\s|[-*+]\s|\d+\.\s|```|>\s|\|.+\|)|(\*\*|__|`[^`]+`|\[[^\]]+\]\([^)]+\))/;

const EXECUTION_WRAPPER_PATTERN =
  /^(Executed `([^`]+)` \([^)]+\)[^\n]*)\n\n```(?:[^\n]*\n)?([\s\S]*?)```(?:\n\n([\s\S]+))?$/;

const INTERIM_STATUS_PATTERN =
  /^(?:i(?:'ll| will)\b|search(?:ing)?\b|trying\b|looking\b|checking\b|gathering\b|let me\b)/i;

export type AgentMessagePreviewParts = {
  preamble: string | null;
  markdownSource: string;
  postamble: string | null;
  executionIntent: string | null;
  hasMarkdownPreview: boolean;
};

export function agentMessageLooksLikeMarkdown(content: string): boolean {
  const trimmed = content.trim();
  if (!trimmed) {
    return false;
  }

  return MARKDOWN_HINT_PATTERN.test(trimmed);
}

export function isInterimAgentStatus(content: string): boolean {
  const trimmed = content.trim();
  if (!trimmed || trimmed.length > 280) {
    return false;
  }
  if (/^#{1,6}\s/m.test(trimmed)) {
    return false;
  }
  if (agentMessageLooksLikeMarkdown(trimmed)) {
    return false;
  }
  const lineCount = trimmed.split('\n').filter((line) => line.trim()).length;
  if (lineCount > 1) {
    return false;
  }
  const firstLine = trimmed.split('\n').map((line) => line.trim()).find(Boolean) ?? '';
  return INTERIM_STATUS_PATTERN.test(firstLine);
}

export function isAgentReportMarkdown(content: string): boolean {
  const trimmed = content.trim();
  if (!trimmed || isInterimAgentStatus(trimmed)) {
    return false;
  }
  if (/^#{1,3}\s+/m.test(trimmed)) {
    return true;
  }
  if (trimmed.length >= 500 && agentMessageLooksLikeMarkdown(trimmed)) {
    return true;
  }
  return false;
}

export function splitAgentMessageForPreview(content: string): AgentMessagePreviewParts {
  const trimmed = content.trim();
  const executionMatch = trimmed.match(EXECUTION_WRAPPER_PATTERN);

  if (executionMatch) {
    const [, preamble, intent, fencedBody, postamble] = executionMatch;
    const markdownSource = fencedBody.trim();
    const normalizedIntent = intent.trim();
    const hasMarkdownPreview =
      normalizedIntent === 'read_file' ||
      (normalizedIntent !== 'git_status' &&
        normalizedIntent !== 'health' &&
        agentMessageLooksLikeMarkdown(markdownSource));

    return {
      preamble,
      markdownSource,
      postamble: postamble?.trim() || null,
      executionIntent: normalizedIntent,
      hasMarkdownPreview,
    };
  }

  return {
    preamble: null,
    markdownSource: trimmed,
    postamble: null,
    executionIntent: null,
    hasMarkdownPreview: agentMessageLooksLikeMarkdown(trimmed),
  };
}

export function renderAgentMessageMarkdown(
  content: string,
  options: { workspaceId?: string | null } = {},
): string {
  const parts = splitAgentMessageForPreview(content);
  const normalized = normalizeEmptyHeaderMarkdownTables(
    normalizeAgentProseMarkdown(parts.markdownSource),
  );
  const linked = linkifyWorkspacePathsInMarkdown(normalized);
  const html = marked.parse(linked, { async: false }) as string;
  return rewriteMarkdownImageSources(html, options);
}

export function shouldOfferMarkdownPreview(content: string): boolean {
  return splitAgentMessageForPreview(content).hasMarkdownPreview;
}

/** Rich agent prose renders as inline markdown — not interim status or read_file stubs. */
export function shouldUseAgentMarkdownBlock(content: string, isComplete = true): boolean {
  return shouldRenderAgentProseMarkdown(content, { isComplete });
}

/** Agent dock prose lane — complete replies always render as markdown unless error/read_file. */
export function shouldRenderAgentProseMarkdown(
  content: string,
  options: { isComplete?: boolean; isErrorDump?: boolean } = {},
): boolean {
  const trimmed = content.trim();
  if (!trimmed || options.isErrorDump) {
    return false;
  }
  if (isMarkdownFileAgentResponse(trimmed)) {
    return false;
  }
  const isComplete = options.isComplete !== false;
  if (!isComplete && isInterimAgentStatus(trimmed)) {
    return false;
  }
  if (isComplete) {
    return true;
  }
  if (isInterimAgentStatus(trimmed)) {
    return false;
  }
  return agentMessageLooksLikeMarkdown(trimmed) || trimmed.length >= 120;
}

const MD_FILE_HEADING_RE = /^#{1,6}\s+(.+\.md)\s*$/im;

export function isMarkdownFileAgentResponse(content: string): boolean {
  const parts = splitAgentMessageForPreview(content);
  if (MD_FILE_HEADING_RE.test(parts.markdownSource)) {
    return true;
  }
  if (parts.executionIntent === 'read_file' && /\.md\b/i.test(parts.preamble ?? '')) {
    return true;
  }
  return false;
}

/** Workspace path from a read_file agent message that returned markdown file content. */
export function extractReadMarkdownFilePath(content: string): string | null {
  if (!isMarkdownFileAgentResponse(content)) {
    return null;
  }
  const parts = splitAgentMessageForPreview(content);
  const match = parts.markdownSource.match(MD_FILE_HEADING_RE);
  return match?.[1]?.trim() ?? null;
}

export function shouldHideAgentReportInThread(_content: string): boolean {
  return false;
}

export function shouldOfferOpenInEditor(content: string, isComplete = true): boolean {
  if (!isComplete) {
    return false;
  }
  return shouldAutoOpenAgentReportInEditor(content) || isAgentReportMarkdown(content);
}

export function shouldAutoOpenAgentReportInEditor(_content: string): boolean {
  // Cursor-style: agent prose stays in the chat lane; only workspace files belong in the editor.
  return false;
}

/** @deprecated use shouldUseAgentMarkdownBlock */
export function shouldRenderAgentTextBlock(content: string): boolean {
  return shouldUseAgentMarkdownBlock(content);
}

export function extractAgentReportMarkdown(content: string): string | null {
  const trimmed = content.trim();
  if (!trimmed) {
    return null;
  }

  if (!/^:::(thinking|edit|terminal|tool|research|debug-reproduce)\b/m.test(trimmed)) {
    if (shouldAutoOpenAgentReportInEditor(trimmed)) {
      return splitAgentMessageForPreview(trimmed).markdownSource;
    }
    return null;
  }

  const segments = trimmed.split(/\n(?=:::)/);
  let lastReport: string | null = null;
  for (const segment of segments) {
    if (/^:::(thinking|edit|terminal|tool|research|debug-reproduce)\b/m.test(segment.trim())) {
      continue;
    }
    const prose = segment.trim();
    if (shouldAutoOpenAgentReportInEditor(prose)) {
      lastReport = splitAgentMessageForPreview(prose).markdownSource;
    }
  }
  return lastReport;
}

export function deriveAgentReportTitle(content: string): string {
  const heading = content.match(/^#{1,6}\s+(.+)$/m);
  if (heading?.[1]) {
    return heading[1].trim().slice(0, 72);
  }
  const firstLine = content.split('\n').map((line) => line.trim()).find(Boolean);
  return firstLine ? firstLine.slice(0, 72) : 'Agent report';
}

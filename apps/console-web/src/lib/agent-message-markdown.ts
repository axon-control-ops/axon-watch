import { marked } from 'marked';

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
  const html = marked.parse(parts.markdownSource, { async: false }) as string;
  return rewriteMarkdownImageSources(html, options);
}

export function shouldOfferMarkdownPreview(content: string): boolean {
  return splitAgentMessageForPreview(content).hasMarkdownPreview;
}

/** Rich agent prose renders as inline markdown — not interim status or read_file stubs. */
export function shouldUseAgentMarkdownBlock(content: string, isComplete = true): boolean {
  const trimmed = content.trim();
  if (!trimmed) {
    return false;
  }
  if (!isComplete && isInterimAgentStatus(trimmed)) {
    return false;
  }
  if (isInterimAgentStatus(trimmed)) {
    return false;
  }
  if (isMarkdownFileAgentResponse(trimmed)) {
    return false;
  }
  return true;
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

  if (!/^:::(thinking|edit|terminal|tool|research)\b/m.test(trimmed)) {
    if (shouldAutoOpenAgentReportInEditor(trimmed)) {
      return splitAgentMessageForPreview(trimmed).markdownSource;
    }
    return null;
  }

  const segments = trimmed.split(/\n(?=:::)/);
  let lastReport: string | null = null;
  for (const segment of segments) {
    if (/^:::(thinking|edit|terminal|tool|research)\b/m.test(segment.trim())) {
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

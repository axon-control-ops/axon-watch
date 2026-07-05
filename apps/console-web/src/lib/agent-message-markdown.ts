import { marked } from 'marked';

marked.setOptions({
  breaks: true,
  gfm: true,
});

const MARKDOWN_HINT_PATTERN =
  /(^|\n)\s{0,3}(#{1,6}\s|[-*+]\s|\d+\.\s|```|>\s|\|.+\|)|(\*\*|__|`[^`]+`|\[[^\]]+\]\([^)]+\))/;

const EXECUTION_WRAPPER_PATTERN =
  /^(Executed `([^`]+)` \([^)]+\)[^\n]*)\n\n```(?:[^\n]*\n)?([\s\S]*?)```(?:\n\n([\s\S]+))?$/;

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

export function renderAgentMessageMarkdown(content: string): string {
  const parts = splitAgentMessageForPreview(content);
  return marked.parse(parts.markdownSource, { async: false }) as string;
}

export function shouldOfferMarkdownPreview(content: string): boolean {
  return splitAgentMessageForPreview(content).hasMarkdownPreview;
}

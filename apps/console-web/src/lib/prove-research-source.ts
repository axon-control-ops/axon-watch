import type { ResearchTranscriptItem } from './agent-transcript-blocks';
import {
  formatResearchKindLabel,
  formatResearchProviderLabel,
  type ResearchBlockKind,
} from './research-provider';

export function buildResearchEditorContent(title: string, url: string, snippet: string): string {
  const body = snippet.trim();
  if (!body) {
    return '';
  }
  if (!url || url === 'about:blank') {
    return body;
  }
  return `${body}\n\n---\n**Source:** [${title.trim() || url}](${url})`;
}

export function shouldOpenResearchInEditor(
  kind: ResearchBlockKind | undefined,
  snippet: string,
): boolean {
  return kind === 'fetch' && Boolean(snippet.trim());
}

export function researchBlockPreview(input: {
  query: string;
  items: ResearchTranscriptItem[];
  kind?: ResearchBlockKind;
  provider?: string;
  live?: boolean;
}): string {
  if (input.live) {
    return input.query.trim() || 'Research';
  }

  const kindLabel = formatResearchKindLabel(input.kind);
  const providerLabel = formatResearchProviderLabel(input.provider ?? '');
  const headline = kindLabel || input.query.trim() || 'Research';

  if (input.items.length === 0) {
    return providerLabel ? `${headline} · ${providerLabel}` : headline;
  }

  if (input.items.length === 1) {
    const title = input.items[0]?.title?.trim() || '1 source';
    return providerLabel ? `${headline} — ${title} · ${providerLabel}` : `${headline} — ${title}`;
  }

  const sourceLabel = `${input.items.length} sources`;
  return providerLabel ? `${headline} — ${sourceLabel} · ${providerLabel}` : `${headline} — ${sourceLabel}`;
}

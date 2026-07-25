export const AGENT_MARKDOWN_PREVIEW_DEFAULT_KEY = 'axon-x-agent-markdown-preview-default-v1';
export const AGENT_MARKDOWN_PREVIEW_MESSAGES_KEY = 'axon-x-agent-markdown-preview-messages-v1';

type MessagePreviewMap = Record<string, boolean>;

function readMessagePreviewMap(): MessagePreviewMap {
  if (typeof window === 'undefined') {
    return {};
  }

  const raw = window.localStorage.getItem(AGENT_MARKDOWN_PREVIEW_MESSAGES_KEY);
  if (!raw) {
    return {};
  }

  try {
    const parsed = JSON.parse(raw) as unknown;
    if (!parsed || typeof parsed !== 'object') {
      return {};
    }

    const map: MessagePreviewMap = {};
    for (const [messageId, enabled] of Object.entries(parsed)) {
      if (typeof enabled === 'boolean') {
        map[messageId] = enabled;
      }
    }
    return map;
  } catch {
    return {};
  }
}

function writeMessagePreviewMap(map: MessagePreviewMap): void {
  if (typeof window === 'undefined') {
    return;
  }

  window.localStorage.setItem(AGENT_MARKDOWN_PREVIEW_MESSAGES_KEY, JSON.stringify(map));
}

export function readAgentMarkdownPreviewDefault(): boolean {
  if (typeof window === 'undefined') {
    return true;
  }

  const raw = window.localStorage.getItem(AGENT_MARKDOWN_PREVIEW_DEFAULT_KEY);
  if (raw === 'false') {
    return false;
  }
  return true;
}

export function persistAgentMarkdownPreviewDefault(enabled: boolean): void {
  if (typeof window === 'undefined') {
    return;
  }

  window.localStorage.setItem(AGENT_MARKDOWN_PREVIEW_DEFAULT_KEY, enabled ? 'true' : 'false');
}

export function readAgentMessagePreviewEnabled(messageId: string): boolean | null {
  const map = readMessagePreviewMap();
  return map[messageId] ?? null;
}

export function persistAgentMessagePreviewEnabled(
  messageId: string,
  enabled: boolean,
): void {
  const map = readMessagePreviewMap();
  map[messageId] = enabled;
  writeMessagePreviewMap(map);
}

export function resolveAgentMessagePreviewEnabled(
  messageId: string,
  hasMarkdownPreview: boolean,
): boolean {
  if (!hasMarkdownPreview) {
    return false;
  }

  const stored = readAgentMessagePreviewEnabled(messageId);
  if (stored !== null) {
    return stored;
  }

  return readAgentMarkdownPreviewDefault();
}

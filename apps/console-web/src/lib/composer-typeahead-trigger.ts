export type ComposerTypeaheadKind = 'slash' | 'mention';

export type ComposerCaretToken = {
  kind: ComposerTypeaheadKind;
  /** Full token including `/` or `@`. */
  token: string;
  /** Filter text without the leading `/` or `@`. */
  query: string;
  start: number;
  end: number;
};

const MENTION_BOUNDARY = /[\s([{,]/;

/** Detect an active `/` or `@` token at the caret for composer typeahead. */
export function detectComposerCaretToken(
  text: string,
  caret: number,
): ComposerCaretToken | null {
  const safeCaret = Math.max(0, Math.min(caret, text.length));
  const mention = detectMentionToken(text, safeCaret);
  if (mention) {
    return mention;
  }
  return detectSlashToken(text, safeCaret);
}

function detectSlashToken(text: string, caret: number): ComposerCaretToken | null {
  const lead = text.match(/^\s*/)?.[0].length ?? 0;
  if (text[lead] !== '/') {
    return null;
  }
  const match = text.slice(lead).match(/^\/([^\s]*)/);
  if (!match) {
    return null;
  }
  const start = lead;
  const end = lead + match[0].length;
  if (caret < start || caret > end) {
    return null;
  }
  return {
    kind: 'slash',
    token: match[0],
    query: match[1] ?? '',
    start,
    end,
  };
}

function detectMentionToken(text: string, caret: number): ComposerCaretToken | null {
  let at = -1;
  for (let i = caret - 1; i >= 0; i -= 1) {
    const ch = text[i];
    if (ch === '@') {
      at = i;
      break;
    }
    if (ch === '\n' || /\s/.test(ch)) {
      return null;
    }
    if (caret - i > 120) {
      return null;
    }
  }
  if (at < 0) {
    return null;
  }
  if (at > 0 && !MENTION_BOUNDARY.test(text[at - 1] ?? '')) {
    return null;
  }
  const body = text.slice(at + 1, caret);
  if (/[\s\n]/.test(body)) {
    return null;
  }
  return {
    kind: 'mention',
    token: `@${body}`,
    query: body,
    start: at,
    end: caret,
  };
}

export function replaceComposerToken(
  text: string,
  token: Pick<ComposerCaretToken, 'start' | 'end'>,
  insertion: string,
): { next: string; caret: number } {
  const next = `${text.slice(0, token.start)}${insertion}${text.slice(token.end)}`;
  return {
    next,
    caret: token.start + insertion.length,
  };
}

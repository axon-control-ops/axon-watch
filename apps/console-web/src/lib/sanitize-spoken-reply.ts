import { OPERATOR_PERSONA_NAME } from './operator-persona-name';
import { stripLiteralSymbolWords } from './spoken-symbol-words';

const STREAM_BLOCK_START_RE = /^:::(?:thinking|tool|edit|terminal|research)\b/i;
const STREAM_BLOCK_CLOSE_RE = /^:::\s*$/;
const PATH_ONLY_RE = /^[\w./_-]+$/;
const MAX_DISPLAY_CHARS = 1600;
const MAX_SPOKEN_CHARS = 1400;
const SPEECH_CHUNK_CHARS = 900;

function stripStreamBlocks(text: string): string {
  const kept: string[] = [];
  let skipping = false;
  for (const line of text.split('\n')) {
    const stripped = line.trim();
    if (STREAM_BLOCK_START_RE.test(stripped)) {
      skipping = true;
      continue;
    }
    if (skipping) {
      if (STREAM_BLOCK_CLOSE_RE.test(stripped) || !stripped) {
        skipping = false;
      }
      continue;
    }
    if (stripped.startsWith(':::')) {
      continue;
    }
    kept.push(line);
  }
  return kept.join('\n').trim();
}

function dedupeDoubledText(text: string): string {
  const half = Math.floor(text.length / 2);
  if (half > 0 && text.slice(0, half).trim() === text.slice(half).trim()) {
    return text.slice(0, half).trim();
  }
  return text;
}

function stripMarkdownForSpeech(text: string): string {
  return text
    .replace(/```[\s\S]*?```/g, ' ')
    .replace(/`([^`]+)`/g, '$1')
    .replace(/\*\*([^*]+)\*\*/g, '$1')
    .replace(/\*([^*]+)\*/g, '$1')
    .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
    .replace(/"/g, ' ')
    .replace(/'/g, "'");
}

/** Keep TTS from reading punctuation / symbol names aloud. */
function softenSymbolsForSpeech(text: string): string {
  let out = text
    // Emoji / pictographs (incl. many "smiley" ranges).
    .replace(/[\u{1F300}-\u{1FAFF}\u{2700}-\u{27BF}\u{2600}-\u{26FF}]/gu, ' ')
    .replace(/\\/g, ' ')
    .replace(/\//g, ' ')
    .replace(/_/g, ' ')
    .replace(/\|/g, ' ')
    .replace(/#/g, ' ')
    .replace(/@/g, ' ')
    .replace(/\*/g, ' ')
    .replace(/→/g, ' ')
    .replace(/←/g, ' ')
    .replace(/=>/g, ' ');
  // Preserve clock times (12:30); turn every other colon into a pause.
  out = out.replace(/\b(\d{1,2}):(\d{2})\b/g, '$1\uE000$2');
  out = out.replace(/:/g, ', ');
  out = out.replace(/\uE000/g, ':');
  out = out.replace(/[<>{}[\]()`~^]/g, ' ');
  out = out.replace(/\s+,/g, ',').replace(/,\s*,+/g, ',');
  return out.replace(/\s+/g, ' ').trim();
}

function stripPersonaPrefix(text: string): string {
  return text
    .replace(/^["'`]+|["'`]+$/g, '')
    .replace(
      new RegExp(`^(${OPERATOR_PERSONA_NAME}|KAIRO|Jarvis)\\s*[:—-]\\s*`, 'i'),
      '',
    )
    .trim();
}

function readableParagraphs(text: string): string[] {
  const chunks = text
    .split(/\n\s*\n+/)
    .map((chunk) => chunk.trim())
    .filter(Boolean);
  const paragraphs: string[] = [];
  for (const chunk of chunks) {
    if (chunk.startsWith(':::')) {
      continue;
    }
    if (PATH_ONLY_RE.test(chunk)) {
      continue;
    }
    if (chunk.length < 16 && chunk.includes('/') && !chunk.includes(' ')) {
      continue;
    }
    const normalized = chunk.replace(/\s+/g, ' ').trim();
    if (!normalized) {
      continue;
    }
    if (paragraphs.length > 0 && paragraphs[paragraphs.length - 1].toLowerCase() === normalized.toLowerCase()) {
      continue;
    }
    paragraphs.push(normalized);
  }
  return paragraphs;
}

function truncateAtSentence(text: string, maxChars: number): string {
  if (text.length <= maxChars) {
    return text;
  }
  const trimmed = text.slice(0, maxChars);
  const cut = trimmed.lastIndexOf('. ');
  if (cut >= maxChars / 2) {
    return trimmed.slice(0, cut + 1).trim();
  }
  const lastSpace = trimmed.lastIndexOf(' ');
  const shortened = lastSpace > 0 ? trimmed.slice(0, lastSpace).trim() : trimmed.trim();
  return `${shortened}…`;
}

/** Strip agent stream noise while preserving readable answer paragraphs. */
export function cleanAgentReplyText(raw: string): string {
  const original = raw.trim();
  if (!original) {
    return '';
  }
  let text = stripStreamBlocks(original);
  text = stripMarkdownForSpeech(text);
  text = dedupeDoubledText(text);
  text = stripPersonaPrefix(text);
  return text.replace(/\n{3,}/g, '\n\n').trim();
}

/** Format a reply for on-screen display in the conversation bar. */
export function formatConversationDisplayReply(raw: string, maxChars = MAX_DISPLAY_CHARS): string {
  const cleaned = cleanAgentReplyText(raw);
  if (!cleaned) {
    return '';
  }
  const paragraphs = readableParagraphs(cleaned);
  const body = (paragraphs.length > 0 ? paragraphs.join('\n\n') : cleaned).trim();
  if (body.length <= maxChars) {
    return body;
  }
  return truncateAtSentence(body.replace(/\n+/g, ' '), maxChars);
}

/** Convert agent/model text into operator-facing speech (may still be long). */
export function sanitizeSpokenReply(raw: string, maxChars = MAX_SPOKEN_CHARS): string {
  const display = formatConversationDisplayReply(raw, maxChars);
  let spoken = softenSymbolsForSpeech(display.replace(/\n+/g, ' ').replace(/\s+/g, ' ').trim());
  spoken = stripLiteralSymbolWords(spoken);
  if (spoken && !/[.!?]$/.test(spoken)) {
    spoken = `${spoken}.`;
  }
  return spoken;
}

/** Split long spoken lines into Azure-safe chunks at sentence boundaries. */
export function splitSpokenReplyChunks(text: string, maxChunk = SPEECH_CHUNK_CHARS): string[] {
  const normalized = text.replace(/\s+/g, ' ').trim();
  if (!normalized) {
    return [];
  }
  if (normalized.length <= maxChunk) {
    return [normalized];
  }

  const sentences = normalized.match(/[^.!?]+[.!?]+|[^.!?]+$/g) ?? [normalized];
  const chunks: string[] = [];
  let current = '';

  for (const sentence of sentences) {
    const piece = sentence.trim();
    if (!piece) {
      continue;
    }
    const candidate = current ? `${current} ${piece}` : piece;
    if (candidate.length > maxChunk && current) {
      chunks.push(current.trim());
      current = piece;
      continue;
    }
    current = candidate;
  }

  if (current.trim()) {
    chunks.push(current.trim());
  }
  return chunks.length > 0 ? chunks : [normalized];
}

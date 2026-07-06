/** JARVIS-style spoken lines for KAIRO — assistant talk, not transcript readback. */

import type { NarrationMilestone } from './kairo-agent-narration';

export type KairoVoiceContext = {
  fullAccess: boolean;
  activeFile?: string | null;
};

export function jarvisAgentStartLine(context: KairoVoiceContext): string {
  if (context.fullAccess) {
    const file = context.activeFile ? friendlyFileName(context.activeFile) : null;
    if (file) {
      return `Understood. I'll take care of that in ${file} for you.`;
    }
    return "Understood. I'll handle that for you now.";
  }
  return "Right — let me take a look at that for you.";
}

/** Turn a narration milestone into a short assistant line, or null to stay quiet. */
export function jarvisSpokenLine(
  milestone: NarrationMilestone,
  context: KairoVoiceContext,
): string | null {
  const { key } = milestone;

  if (key === 'thinking:0') {
    return "One moment — I'm working out the best approach.";
  }

  if (key.startsWith('tool:')) {
    return jarvisToolLine(milestone.toolLabel ?? '');
  }

  if (key.startsWith('edit:')) {
    const file = friendlyFileName(milestone.editPath ?? 'the file');
    return `There — I've updated ${file} for you.`;
  }

  if (key === 'done') {
    if (milestone.editCount && milestone.editCount > 1) {
      return `All set — I've updated ${milestone.editCount} files for you. Take a look when you're ready.`;
    }
    if (milestone.editPath) {
      return `All set — ${friendlyFileName(milestone.editPath)} is updated. Take a look when you're ready.`;
    }
    return "All set — I'm ready when you are.";
  }

  return null;
}

/** Rewrite briefing/alert copy into assistant speech (never read UI labels aloud). */
export function jarvisAlertSpeech(message: string): string {
  let text = message.trim();
  text = text
    .replace(/^KAIRO:\s*/i, '')
    .replace(/^KAIRO attention:\s*/i, '')
    .replace(/^KAIRO —\s*/i, '');
  if (!text) {
    return '';
  }

  const lower = text.toLowerCase();
  if (lower.includes('approval') && lower.includes('review')) {
    return 'Sir — something needs your approval before I can continue.';
  }
  if (lower.includes('degraded')) {
    return 'Heads up — runtime looks degraded. Worth a quick check before we continue.';
  }
  if (lower.includes('briefing unavailable')) {
    return "I'm having trouble loading the briefing. Give me a moment, or check the connection.";
  }
  if (lower.includes('standing by while briefing')) {
    return 'Standing by — briefing is still loading.';
  }
  if (lower.includes("i'm listening") || lower.includes('ready')) {
    return "I'm here whenever you're ready.";
  }

  return text.endsWith('.') ? text : `${text}.`;
}

function jarvisToolLine(label: string): string | null {
  const trimmed = label.trim();
  if (!trimmed) {
    return null;
  }
  if (/^read\b/i.test(trimmed)) {
    const file = friendlyFileName(trimmed.replace(/^read\s+/i, ''));
    return `I'm pulling up ${file} for you.`;
  }
  if (/^edit\b/i.test(trimmed)) {
    const file = friendlyFileName(trimmed.replace(/^edit\s+(failed\s+)?/i, ''));
    return `I'm editing ${file} now.`;
  }
  if (/^shell\b/i.test(trimmed) || /^run\b/i.test(trimmed)) {
    return 'Running that command for you now.';
  }
  return null;
}

function friendlyFileName(path: string): string {
  const normalized = path.trim().replace(/\\/g, '/');
  const base = normalized.split('/').pop() || normalized;
  if (base.toLowerCase() === 'readme.md') {
    return 'the README';
  }
  return base;
}

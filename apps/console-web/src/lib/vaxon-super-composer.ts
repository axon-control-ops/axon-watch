import type { VaxonExecutiveComposerMode } from './vaxon-executive-composer';

export type VaxonQuickPrompt = {
  id: string;
  label: string;
  prompt: string;
  mode: VaxonExecutiveComposerMode;
  hint?: string;
};

export const VAXON_QUICK_PROMPTS: readonly VaxonQuickPrompt[] = [
  {
    id: 'status',
    label: 'Status',
    prompt: 'REPORT',
    mode: 'ask',
    hint: 'Fleet + run snapshot',
  },
  {
    id: 'brief',
    label: 'Brief',
    prompt: 'Brief me on what needs my attention right now.',
    mode: 'ask',
    hint: 'Executive summary',
  },
  {
    id: 'fleet',
    label: 'Fleet',
    prompt: 'Summarize fleet health, connectors, and anything degraded.',
    mode: 'ask',
    hint: 'Workspace mosaic',
  },
  {
    id: 'scan',
    label: 'Scan',
    prompt: 'Scan the host for pressure, stuck runs, and connector drift.',
    mode: 'ask',
    hint: 'Machine CEO sweep',
  },
  {
    id: 'dispatch-template',
    label: 'Mission',
    prompt: 'Objective:\nSuccess criteria:\nConstraints:',
    mode: 'dispatch',
    hint: 'Dispatch scaffold',
  },
] as const;

export function vaxonComposerAutoGrowHeight(textarea: HTMLTextAreaElement, maxPx = 220): void {
  textarea.style.height = 'auto';
  const next = Math.min(Math.max(textarea.scrollHeight, 44), maxPx);
  textarea.style.height = `${next}px`;
}

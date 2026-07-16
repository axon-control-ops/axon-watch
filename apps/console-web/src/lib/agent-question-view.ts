export type AgentQuestionOption = {
  id: string;
  label: string;
};

export type AgentQuestionView = {
  prompt: string;
  options: AgentQuestionOption[];
};

/** Synthetic Cursor-style free-response choice appended in the question card UI. */
export const AGENT_QUESTION_OTHER_ID = 'other';

export function isAgentQuestionOtherOption(option: Pick<AgentQuestionOption, 'id' | 'label'>): boolean {
  const id = option.id.trim().toLowerCase();
  const label = option.label.trim().toLowerCase();
  return id === AGENT_QUESTION_OTHER_ID || label === 'other';
}

/** Ensure the card always offers an Other free-text choice without duplicating model options. */
export function withOtherQuestionOption(options: AgentQuestionOption[]): AgentQuestionOption[] {
  if (options.some((option) => isAgentQuestionOtherOption(option))) {
    return options;
  }
  return [...options, { id: AGENT_QUESTION_OTHER_ID, label: 'Other' }];
}

const ASK_OPTION_PIPE_RE = /^\s*[-*]\s+(\d+)\s*\|\s+(.+?)\s*$/;
const ASK_OPTION_DASH_RE = /^\s*[-*]\s+(\d+)[.)]\s+(.+?)\s*$/;
const NUMBERED_OPTION_RE = /^\s*(\d+)[.)]\s+\*?(.+?)\*?\s*$/;

export function parseAskOptions(bodyLines: string[]): AgentQuestionOption[] {
  const options: AgentQuestionOption[] = [];
  for (const raw of bodyLines) {
    const line = raw.trim();
    if (!line || line === ':::') {
      continue;
    }
    const pipe = line.match(ASK_OPTION_PIPE_RE);
    if (pipe) {
      options.push({ id: pipe[1], label: pipe[2].trim() });
      continue;
    }
    const dashed = line.match(ASK_OPTION_DASH_RE);
    if (dashed) {
      options.push({ id: dashed[1], label: dashed[2].trim() });
      continue;
    }
    const numbered = line.match(NUMBERED_OPTION_RE);
    if (numbered) {
      options.push({ id: numbered[1], label: numbered[2].replace(/^\*+|\*+$/g, '').trim() });
    }
  }
  return options;
}

/** Upgrade plain "Reply with 1, 2, or 3" clarifying prose into a question card model. */
export function tryParseClarifyingMarkdown(text: string): AgentQuestionView | null {
  const trimmed = text.trim();
  if (!trimmed) {
    return null;
  }
  const lower = trimmed.toLowerCase();
  const looksLikeAsk =
    lower.includes('reply with') ||
    lower.includes('what should this plan focus') ||
    (/\b[123]\b/.test(trimmed) && (lower.includes('pick') || lower.includes('choose')));
  if (!looksLikeAsk) {
    return null;
  }

  const lines = trimmed.split('\n');
  const options = parseAskOptions(lines);
  if (options.length < 2) {
    return null;
  }

  const optionIds = new Set(options.map((option) => option.id));
  const promptLines = lines.filter((line) => {
    const t = line.trim();
    if (!t) {
      return false;
    }
    if (NUMBERED_OPTION_RE.test(t) || ASK_OPTION_PIPE_RE.test(t) || ASK_OPTION_DASH_RE.test(t)) {
      return false;
    }
    if (/^reply with\b/i.test(t)) {
      return false;
    }
    // Drop bare "1." lines already captured as options
    const numbered = t.match(/^(\d+)[.)]/);
    if (numbered && optionIds.has(numbered[1])) {
      return false;
    }
    return true;
  });

  const prompt =
    promptLines
      .join(' ')
      .replace(/\s+/g, ' ')
      .replace(/\*+/g, '')
      .trim() || 'Choose an option to continue';

  return { prompt, options };
}

export function formatQuestionAnswer(
  option: AgentQuestionOption,
  prompt?: string,
  customText?: string,
): string {
  const id = option.id.trim();
  const custom = customText?.trim() ?? '';
  const label = (isAgentQuestionOtherOption(option) && custom ? custom : option.label).trim();
  if (!id && !label) {
    return '';
  }
  // Matches ask_fence_instruction accepted forms: "Selected option N: <label>"
  const choice =
    label && id && id !== label
      ? `Selected option ${id}: ${label}`
      : `Selected option ${label || id}`;
  const trimmedPrompt = prompt?.trim();
  if (trimmedPrompt) {
    return `${choice}\n(answer to: ${trimmedPrompt})`;
  }
  return choice;
}

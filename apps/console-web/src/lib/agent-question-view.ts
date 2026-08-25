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
const NUMBERED_OPTION_RE = /^\s*(\d+)[.)]\s+(.+?)\s*$/;

const MAX_CLARIFYING_OPTIONS = 6;
const MAX_CLARIFYING_PROMPT_CHARS = 420;
/** Long audit/report prose with numbered lists must stay markdown — not a question card. */
const MAX_CLARIFYING_SOURCE_CHARS = 1200;

export const AGENT_QUESTION_PROMPT_MAX = 280;
export const AGENT_QUESTION_OPTION_LABEL_MAX = 160;

/** Strip markdown emphasis leftovers so option labels do not show `Database**`. */
export function normalizeAskOptionLabel(label: string): string {
  return label.replace(/\*+/g, '').replace(/\s+/g, ' ').trim();
}

export function isAskOptionLine(line: string): boolean {
  const trimmed = line.trim();
  if (!trimmed || trimmed === ':::') {
    return false;
  }
  return (
    ASK_OPTION_PIPE_RE.test(trimmed)
    || ASK_OPTION_DASH_RE.test(trimmed)
    || NUMBERED_OPTION_RE.test(trimmed)
  );
}

export function truncateQuestionPrompt(prompt: string, max = AGENT_QUESTION_PROMPT_MAX): string {
  const normalized = prompt.replace(/\s+/g, ' ').trim();
  if (!normalized) {
    return '';
  }
  if (normalized.length <= max) {
    return normalized;
  }
  return `${normalized.slice(0, max - 1).trimEnd()}…`;
}

export function truncateQuestionOptionLabel(
  label: string,
  max = AGENT_QUESTION_OPTION_LABEL_MAX,
): string {
  const normalized = label.replace(/\s+/g, ' ').trim();
  if (!normalized) {
    return '';
  }
  if (normalized.length <= max) {
    return normalized;
  }
  return `${normalized.slice(0, max - 1).trimEnd()}…`;
}

/** Keep ask cards readable when the model dumps status prose into the fence body. */
export function resolveAskBlockPrompt(input: {
  headerPrompt: string;
  bodyLines: string[];
  options: AgentQuestionOption[];
}): string {
  const header = input.headerPrompt.trim();
  if (header) {
    return truncateQuestionPrompt(header);
  }

  const bodyPromptLines = input.bodyLines
    .map((entry) => entry.trim())
    .filter((entry) => entry && !isAskOptionLine(entry));

  const questionLine = bodyPromptLines.find(
    (line) => line.endsWith('?') && line.length <= AGENT_QUESTION_PROMPT_MAX,
  );
  if (questionLine) {
    return questionLine;
  }

  const joined = bodyPromptLines.slice(0, 2).join(' ').replace(/\s+/g, ' ').trim();
  const looksLikeStatusDump =
    joined.length > 0
    && !joined.endsWith('?')
    && (
      /(?:^|\s)(?:error|failed|traceback|coverage|pytest|ActionRequired)/i.test(joined)
      || bodyPromptLines.length >= 2
    );

  if (joined && joined.length <= AGENT_QUESTION_PROMPT_MAX && !looksLikeStatusDump) {
    return joined;
  }

  if (input.options.length > 0) {
    return 'Choose an option to continue';
  }

  return truncateQuestionPrompt(joined || 'Choose an option to continue');
}

export function parseAskOptions(bodyLines: string[]): AgentQuestionOption[] {
  const options: AgentQuestionOption[] = [];
  for (const raw of bodyLines) {
    const line = raw.trim();
    if (!line || line === ':::') {
      continue;
    }
    const pipe = line.match(ASK_OPTION_PIPE_RE);
    if (pipe) {
      options.push({ id: pipe[1], label: normalizeAskOptionLabel(pipe[2]) });
      continue;
    }
    const dashed = line.match(ASK_OPTION_DASH_RE);
    if (dashed) {
      options.push({ id: dashed[1], label: normalizeAskOptionLabel(dashed[2]) });
      continue;
    }
    const numbered = line.match(NUMBERED_OPTION_RE);
    if (numbered) {
      options.push({ id: numbered[1], label: normalizeAskOptionLabel(numbered[2]) });
    }
  }
  return options;
}

/** Upgrade plain "Reply with 1, 2, or 3" clarifying prose into a question card model. */
export function tryParseClarifyingMarkdown(text: string): AgentQuestionView | null {
  const trimmed = text.trim();
  if (!trimmed || trimmed.length > MAX_CLARIFYING_SOURCE_CHARS) {
    return null;
  }
  const lines = trimmed.split('\n');
  const lower = trimmed.toLowerCase();
  const hasExplicitQuestion = lines.some((line) => {
    const candidate = line.trim();
    return candidate.endsWith('?') && candidate.length <= MAX_CLARIFYING_PROMPT_CHARS;
  });
  // Use word boundaries — "picking" / "chosen" in status dumps must not promote asks.
  const looksLikeAsk =
    /\breply with\b/.test(lower)
    || lower.includes('what should this plan focus')
    || (/\b[123]\b/.test(trimmed) && /\b(?:pick|choose)\b/.test(lower))
    || hasExplicitQuestion;
  if (!looksLikeAsk) {
    return null;
  }

  const options = parseAskOptions(lines);
  if (options.length < 2 || options.length > MAX_CLARIFYING_OPTIONS) {
    return null;
  }

  const optionIds = options.map((option) => option.id);
  if (new Set(optionIds).size !== optionIds.length) {
    // Duplicate ids (e.g. two "1." sections in a report) → not a single ask card.
    return null;
  }

  const prompt = resolveAskBlockPrompt({
    headerPrompt: '',
    bodyLines: lines,
    options,
  });
  if (prompt.length > MAX_CLARIFYING_PROMPT_CHARS) {
    return null;
  }

  return { prompt, options };
}

/** Human-readable choice line for collapsed answered ask cards. */
export function formatAnsweredQuestionChoice(option: AgentQuestionOption): string {
  const id = option.id.trim();
  const label = option.label.trim();

  if (isAgentQuestionOtherOption(option)) {
    if (label && label.toLowerCase() !== AGENT_QUESTION_OTHER_ID) {
      return truncateQuestionOptionLabel(label);
    }
    return 'Other';
  }

  if (!label) {
    return id;
  }

  if (/^\d+$/.test(id) || id.toLowerCase() === label.toLowerCase()) {
    return truncateQuestionOptionLabel(label);
  }

  return truncateQuestionOptionLabel(label);
}

/** Move radio selection up/down for keyboard navigation in question cards. */
export function moveQuestionOptionSelection(
  options: readonly AgentQuestionOption[],
  currentId: string,
  direction: 'next' | 'prev',
): string {
  if (!options.length) {
    return currentId;
  }

  const currentIndex = options.findIndex((option) => option.id === currentId);
  const startIndex = currentIndex >= 0 ? currentIndex : 0;
  const delta = direction === 'next' ? 1 : -1;
  const nextIndex = (startIndex + delta + options.length) % options.length;
  return options[nextIndex]?.id ?? currentId;
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

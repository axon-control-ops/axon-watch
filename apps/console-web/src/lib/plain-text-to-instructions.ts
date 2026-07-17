/**
 * Turn plain-language requests into Instructions markdown without inventing
 * work or dropping the operator's wording.
 */

export type InstructionsSections = {
  goal: string;
  inScope: string[];
  outOfScope: string[];
  steps: string[];
  constraints: string[];
  /** Full original request — never truncated away. */
  sourceRequest: string;
};

const ALREADY_INSTRUCTIONS_RE = /^#\s*Instructions\b/im;
const STEP_LINE_RE = /^\s*(?:[-*]|\d+[.)])\s+(.+)$/;

function collapseWhitespace(text: string): string {
  return text.replace(/\s+/g, ' ').trim();
}

function splitSentences(text: string): string[] {
  const normalized = text.replace(/\r\n/g, '\n').trim();
  if (!normalized) return [];
  return normalized
    .split(/(?<=[.!?])\s+|\n+/)
    .map((part) =>
      collapseWhitespace(part.replace(/^[-*]\s+/, '').replace(/^\d+[.)]\s+/, '')),
    )
    .filter(Boolean);
}

function extractExplicitSteps(plain: string): string[] {
  const steps: string[] = [];
  for (const line of plain.split(/\r?\n/)) {
    const match = STEP_LINE_RE.exec(line);
    if (match?.[1]) {
      steps.push(collapseWhitespace(match[1]));
    }
  }
  return steps;
}

function firstSentence(plain: string, sentences: string[]): string {
  const fromSplit = sentences[0]?.trim();
  if (fromSplit) {
    return fromSplit;
  }
  const cut = plain.search(/[.!?]\s/);
  if (cut > 0) {
    return collapseWhitespace(plain.slice(0, cut + 1));
  }
  return collapseWhitespace(plain);
}

function inferOutOfScope(plain: string): string[] {
  const items = splitSentences(plain).filter((sentence) =>
    /\b(?:never|don'?t|do not|no|out of scope|exclude|without)\b/i.test(sentence),
  );
  items.push('Any task that was not asked for');
  return [...new Set(items)];
}

/**
 * Goal = first full sentence (or whole request if one line). Never cut at "and".
 */
function inferGoal(sentences: string[], plain: string): string {
  const goal = firstSentence(plain, sentences);
  return goal || 'Complete the stated request without inventing extra work.';
}

/**
 * In scope = remaining request sentences (and non-list lines), verbatim.
 * No domain hardcodes (CI / agents / etc.).
 */
function inferInScope(sentences: string[], plain: string, goal: string): string[] {
  const items: string[] = [];
  const seen = new Set<string>();
  const add = (raw: string): void => {
    const item = collapseWhitespace(raw);
    if (!item || item === goal || seen.has(item.toLowerCase())) {
      return;
    }
    // Skip pure negation lines — those belong in Out of scope / Constraints.
    if (/^(?:i\s+)?(?:never|don'?t|do not|no)\b/i.test(item) && /commit|push|merge/i.test(item)) {
      return;
    }
    seen.add(item.toLowerCase());
    items.push(item);
  };

  for (const sentence of sentences) {
    add(sentence);
  }

  // Preserve non-empty paragraph lines that sentence-split missed (short clauses).
  for (const line of plain.split(/\r?\n/)) {
    const trimmed = collapseWhitespace(line.replace(STEP_LINE_RE, '$1'));
    if (trimmed.length >= 8 && !STEP_LINE_RE.test(line)) {
      add(trimmed);
    }
  }

  // Goal is already listed under ## Goal — keep In scope as "what else matters".
  const withoutGoal = items.filter((item) => item.toLowerCase() !== goal.toLowerCase());
  if (withoutGoal.length > 0) {
    return withoutGoal;
  }
  return items.length > 0 ? items : ['Do only what the request states'];
}

/**
 * Steps = explicit bullets/numbers only. If none, one step: follow the request.
 * Never invent CI/agent/workflow steps from keywords.
 */
function inferSteps(plain: string): string[] {
  const explicit = extractExplicitSteps(plain);
  if (explicit.length > 0) {
    return explicit;
  }
  return [
    'Follow the Goal and In scope exactly as written in the Source request',
  ];
}

function inferConstraints(): string[] {
  return [
    'Follow only the Goal, In scope, and Steps above',
    'Do not invent tasks that were not asked for',
    'Preserve every requirement from the Source request',
  ];
}

export function projectInstructionsSections(plainText: string): InstructionsSections {
  const plain = plainText.replace(/\r\n/g, '\n').trim();
  const sentences = splitSentences(plain);
  const goal = inferGoal(sentences, plain);
  return {
    goal,
    inScope: inferInScope(sentences, plain, goal),
    outOfScope: inferOutOfScope(plain),
    steps: inferSteps(plain),
    constraints: inferConstraints(),
    sourceRequest: plain,
  };
}

function renderList(items: string[]): string {
  return items.map((item) => `- ${item}`).join('\n');
}

function renderNumbered(items: string[]): string {
  return items.map((item, index) => `${index + 1}. ${item}`).join('\n');
}

export function plainTextToInstructionsMarkdown(plainText: string): string {
  const plain = plainText.replace(/\r\n/g, '\n').trim();
  if (!plain) {
    return [
      '# Instructions',
      '',
      '## Goal',
      'Describe the outcome in one sentence.',
      '',
      '## In scope',
      '- …',
      '',
      '## Out of scope',
      '- Any task that was not asked for',
      '',
      '## Steps',
      '1. …',
      '',
      '## Constraints',
      '- Follow only the Goal, In scope, and Steps above',
      '- Do not invent tasks that were not asked for',
      '',
      '## Source request',
      '(paste the original ask here)',
      '',
    ].join('\n');
  }
  if (ALREADY_INSTRUCTIONS_RE.test(plain)) {
    return plain.endsWith('\n') ? plain : `${plain}\n`;
  }

  const sections = projectInstructionsSections(plain);
  return [
    '# Instructions',
    '',
    '## Goal',
    sections.goal,
    '',
    '## In scope',
    renderList(sections.inScope),
    '',
    '## Out of scope',
    renderList(sections.outOfScope),
    '',
    '## Steps',
    renderNumbered(sections.steps),
    '',
    '## Constraints',
    renderList(sections.constraints),
    '',
    '## Source request',
    sections.sourceRequest,
    '',
  ].join('\n');
}

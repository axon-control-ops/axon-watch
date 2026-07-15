/**
 * Turn plain-language requests into concise Instructions markdown
 * so agents follow stated intent and do not invent extra tasks.
 */

export type InstructionsSections = {
  goal: string;
  inScope: string[];
  outOfScope: string[];
  steps: string[];
  constraints: string[];
};

const ALREADY_INSTRUCTIONS_RE = /^#\s*Instructions\b/im;

const OUT_OF_SCOPE_HINTS: Array<{ pattern: RegExp; item: string }> = [
  {
    pattern: /\b(never|don'?t|do not|no)\b.{0,40}\bcommit(ting|s)?\b/i,
    item: 'Committing, amending, or inventing commit chores',
  },
  {
    pattern: /\b(never|don'?t|do not|no)\b.{0,40}\b(push|merge|release|deploy)\b/i,
    item: 'Pushing, merging, releasing, or deploying unless later asked',
  },
  {
    pattern: /\bi never said\b.{0,60}\bcommit/i,
    item: 'Committing or suggesting commits',
  },
];

const STEP_LINE_RE = /^\s*(?:[-*]|\d+[.)])\s+(.+)$/;

function collapseWhitespace(text: string): string {
  return text.replace(/\s+/g, ' ').trim();
}

function splitSentences(text: string): string[] {
  const normalized = text.replace(/\r\n/g, '\n').trim();
  if (!normalized) return [];
  return normalized
    .split(/(?<=[.!?])\s+|\n+/)
    .map((part) => collapseWhitespace(part.replace(/^[-*]\s+/, '').replace(/^\d+[.)]\s+/, '')))
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

function inferOutOfScope(plain: string): string[] {
  const items: string[] = [];
  const seen = new Set<string>();
  for (const hint of OUT_OF_SCOPE_HINTS) {
    if (hint.pattern.test(plain) && !seen.has(hint.item)) {
      seen.add(hint.item);
      items.push(hint.item);
    }
  }
  items.push('Any task that was not asked for');
  return items;
}

function inferGoal(sentences: string[], plain: string): string {
  const lookMatch = plain.match(
    /\b(?:look at|read|check|review)\b(.{0,120}?)(?:\band\b|\.|$)/i,
  );
  const planMatch = plain.match(
    /\b(?:plan|figure out|map|decide)\b(.{0,120}?)(?:\band\b|\.|$)/i,
  );
  if (lookMatch && planMatch) {
    return collapseWhitespace(
      `Review${lookMatch[1]} and plan${planMatch[1]}`.replace(/\s+/g, ' '),
    );
  }
  if (planMatch) {
    return collapseWhitespace(`Plan${planMatch[1]}`);
  }
  if (lookMatch) {
    return collapseWhitespace(`Review${lookMatch[1]}`);
  }
  return sentences[0] || 'Complete the stated request without inventing extra work.';
}

function inferInScope(sentences: string[], plain: string): string[] {
  const items: string[] = [];
  if (/\bci\b|build|pipeline|github|workflow/i.test(plain)) {
    items.push('Use the existing CI / build notes as the source of truth');
  }
  if (/\bagents?\b|employees?\b|company\b|watchers?\b/i.test(plain)) {
    items.push('Map work to the agents already staffed for this workspace');
  }
  if (/instruction|plain text|precise steps/i.test(plain)) {
    items.push('Improve how plain requests become precise instruction steps');
  }
  for (const sentence of sentences.slice(0, 4)) {
    if (/commit|push|merge/i.test(sentence) && /never|don'?t|do not|wrong/i.test(sentence)) {
      continue;
    }
    if (sentence.length > 12 && sentence.length < 160 && !items.includes(sentence)) {
      items.push(sentence);
    }
  }
  if (items.length === 0) {
    items.push('Do only what the request states');
  }
  return items.slice(0, 6);
}

function inferSteps(plain: string, sentences: string[], inScope: string[]): string[] {
  const explicit = extractExplicitSteps(plain);
  if (explicit.length > 0) {
    return explicit;
  }
  const steps: string[] = [];
  if (/\bci\b|build|pipeline|deploy/i.test(plain)) {
    steps.push('Read the latest CI / deploy triage notes for this workspace');
  }
  if (/\bagents?\b|employees?\b|company\b/i.test(plain)) {
    steps.push('Map detection, triage, fix, and escalation to the staffed agents');
  }
  if (/without.{0,40}babysit|while.{0,40}server|always.?on|cloud agents?/i.test(plain)) {
    steps.push('Plan how watchers and builders keep working without constant human prompting');
  }
  if (/instruction|plain text|precise steps/i.test(plain)) {
    steps.push('Produce Instructions markdown with Goal, In scope, Out of scope, Steps, and Constraints');
  }
  if (steps.length === 0) {
    for (const item of inScope.slice(0, 4)) {
      steps.push(item);
    }
  }
  if (steps.length === 0 && sentences[0]) {
    steps.push(sentences[0]);
  }
  steps.push('Reply with a short summary of what changed — do not add unrequested chores');
  return steps;
}

function inferConstraints(plain: string): string[] {
  const constraints = [
    'Follow only the steps listed above',
    'Do not invent tasks that were not asked for',
  ];
  if (/\bcommit/i.test(plain) && /\b(never|don'?t|do not|wrong|no)\b/i.test(plain)) {
    constraints.push('Do not commit, suggest commits, or clear a “local desk” via git unless explicitly asked');
  }
  return constraints;
}

export function projectInstructionsSections(plainText: string): InstructionsSections {
  const plain = plainText.replace(/\r\n/g, '\n').trim();
  const sentences = splitSentences(plain);
  const inScope = inferInScope(sentences, plain);
  return {
    goal: inferGoal(sentences, plain),
    inScope,
    outOfScope: inferOutOfScope(plain),
    steps: inferSteps(plain, sentences, inScope),
    constraints: inferConstraints(plain),
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
      '- Follow only the steps listed above',
      '- Do not invent tasks that were not asked for',
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
  ].join('\n');
}

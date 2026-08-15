export type LeadReviewFinding = {
  owner: string;
  status: string;
  outcome?: string;
  excerpt?: string;
  runIds: string[];
};

export type LeadReviewParsed = {
  headline: string;
  goal?: string;
  planId?: string;
  outcome?: string;
  workspaceId?: string;
  runId?: string;
  leadNext?: string;
  findings: LeadReviewFinding[];
  footer?: string;
  kind: 'team_rollup' | 'adhoc_handoff' | 'raw';
};

export function parseFindingLine(raw: string): LeadReviewFinding {
  const runMatch = raw.match(/\s·\s*runs\s+(.+)$/i);
  const runIds = runMatch
    ? runMatch[1].split(',').map((part) => part.trim()).filter(Boolean)
    : [];
  let body = runMatch ? raw.slice(0, runMatch.index).trim() : raw;

  const dashSplit = body.split(' — ');
  const excerpt = dashSplit.length > 1 ? dashSplit.slice(1).join(' — ').trim() : undefined;
  body = dashSplit[0] ?? body;

  const parenMatch = body.match(/^(.+?):\s*(.+?)\s*\(([^)]*)\)\s*$/);
  if (parenMatch) {
    return {
      owner: parenMatch[1].trim(),
      status: parenMatch[2].trim(),
      outcome: parenMatch[3].trim() || undefined,
      excerpt,
      runIds,
    };
  }

  const colonMatch = body.match(/^(.+?):\s*(.+)$/);
  if (colonMatch) {
    return {
      owner: colonMatch[1].trim(),
      status: colonMatch[2].trim(),
      excerpt,
      runIds,
    };
  }

  return { owner: 'Specialist', status: body, excerpt, runIds };
}

/** Parse a VAXON operator-thread Lead rollup into structured review sections. */
export function parseLeadReviewMessage(content: string): LeadReviewParsed {
  const lines = String(content || '')
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean);

  if (!lines.length) {
    return { headline: 'Lead review', findings: [], kind: 'raw' };
  }

  const headline = lines[0] ?? 'Lead review';
  let goal: string | undefined;
  let planId: string | undefined;
  let outcome: string | undefined;
  let workspaceId: string | undefined;
  let runId: string | undefined;
  let leadNext: string | undefined;
  const findings: LeadReviewFinding[] = [];
  const footerLines: string[] = [];

  for (const line of lines.slice(1)) {
    if (line.startsWith('Goal:')) {
      goal = line.slice('Goal:'.length).trim();
      continue;
    }
    if (line.startsWith('Plan:')) {
      planId = line.slice('Plan:'.length).trim();
      continue;
    }
    if (line.startsWith('Outcome:')) {
      outcome = line.slice('Outcome:'.length).trim();
      continue;
    }
    if (line.startsWith('Workspace:')) {
      workspaceId = line.slice('Workspace:'.length).trim();
      continue;
    }
    if (line.startsWith('Run:')) {
      runId = line.slice('Run:'.length).trim();
      continue;
    }
    if (line.startsWith('Lead summary:')) {
      outcome = line.slice('Lead summary:'.length).trim();
      continue;
    }
    if (line.startsWith('Lead next:')) {
      leadNext = line.slice('Lead next:'.length).trim();
      continue;
    }
    if (line.startsWith('- ')) {
      findings.push(parseFindingLine(line.slice(2)));
      continue;
    }
    if (
      /^Ask me REPORT/i.test(line) ||
      /^Open .+ thread/i.test(line) ||
      /^Lead shift rollup/i.test(line) ||
      /^Lead has the takeover rollup/i.test(line)
    ) {
      footerLines.push(line);
      continue;
    }
  }

  const lowered = headline.toLowerCase();
  const kind: LeadReviewParsed['kind'] = lowered.includes('team rollup')
    ? 'team_rollup'
    : lowered.includes('just ')
      ? 'adhoc_handoff'
      : 'raw';

  return {
    headline,
    goal,
    planId,
    outcome,
    workspaceId,
    runId,
    leadNext,
    findings,
    footer: footerLines.length ? footerLines.join('\n') : undefined,
    kind,
  };
}

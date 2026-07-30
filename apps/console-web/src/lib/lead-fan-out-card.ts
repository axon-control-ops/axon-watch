/** Lead fan-out / decompose AgentDock card payload. */

export type LeadFanOutAssignment = {
  role: string;
  goal: string;
};

export type LeadFanOutCard = {
  planId: string;
  mode: 'decompose' | 'fan_out' | string;
  leadName: string;
  title: string;
  queued: number;
  deferred: number;
  assignments: LeadFanOutAssignment[];
  notes: string[];
};

function asObject(value: unknown): Record<string, unknown> | null {
  return value && typeof value === 'object' && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : null;
}

export function parseLeadFanOutFenceBody(
  body: string,
  titleHint = 'Fan-out',
): LeadFanOutCard | null {
  const trimmed = body.trim();
  if (!trimmed) {
    return null;
  }
  try {
    const parsed = asObject(JSON.parse(trimmed));
    if (!parsed) {
      return null;
    }
    const assignmentsRaw = Array.isArray(parsed.assignments) ? parsed.assignments : [];
    const assignments: LeadFanOutAssignment[] = assignmentsRaw
      .map((row) => {
        const item = asObject(row);
        if (!item) {
          return null;
        }
        const role = String(item.role ?? '').trim() || '?';
        const goal = String(item.goal ?? '').trim() || '(no goal)';
        return { role, goal };
      })
      .filter((row): row is LeadFanOutAssignment => Boolean(row));
    const notes = Array.isArray(parsed.notes)
      ? parsed.notes.map((line) => String(line ?? '').trim()).filter(Boolean)
      : [];
    const mode = String(parsed.mode ?? '').trim().toLowerCase() || 'decompose';
    return {
      planId: String(parsed.plan_id ?? '').trim(),
      mode,
      leadName: String(parsed.lead_name ?? 'Lead').trim() || 'Lead',
      title: titleHint.trim() || (mode === 'decompose' ? 'Decomposed' : 'Fan-out'),
      queued: Number(parsed.queued) || 0,
      deferred: Number(parsed.deferred) || 0,
      assignments,
      notes,
    };
  } catch {
    return null;
  }
}

/**
 * Upgrade legacy plain-text Lead decompose / fan-out essays into a card payload
 * so existing AgentDock history is not stuck as raw prose.
 */
export function tryParseLegacyLeadFanOutText(text: string): LeadFanOutCard | null {
  const raw = text.replace(/\r\n/g, '\n').trim();
  if (!raw) {
    return null;
  }
  const decomposed = /decomposed the work and assigned specialists/i.test(raw);
  const fanOut = /assigned the specialists via Lead fan-out/i.test(raw);
  if (!decomposed && !fanOut) {
    return null;
  }

  const planMatch = raw.match(/plan\s+`([^`]+)`/i) ?? raw.match(/\(plan\s+([^\s)]+)\)/i);
  const planId = planMatch?.[1]?.trim() ?? '';
  const leadMatch = raw.match(/—\s*([A-Za-z][\w .'-]{0,40})\s*$/m);
  const leadName = leadMatch?.[1]?.trim() || 'Lead';

  const assignments: LeadFanOutAssignment[] = [];
  for (const line of raw.split('\n')) {
    const match = line.match(/^-+\s*([a-z][\w-]{1,24})\s*:\s*(.+)$/i);
    if (!match) {
      continue;
    }
    assignments.push({
      role: match[1].trim().toLowerCase(),
      goal: match[2].trim(),
    });
  }

  const queuedMatch = raw.match(/Queued runs:\s*(\d+)/i) ?? raw.match(/queued\s+(\d+)\s+ready runs/i);
  const deferredMatch = raw.match(/Deferred \(dependencies\):\s*(\d+)/i);
  const notes: string[] = [];
  for (const line of raw.split('\n')) {
    const cleaned = line.trim();
    if (/^Fleet:/i.test(cleaned) || /specialist run/i.test(cleaned) || /Continuous workers/i.test(cleaned)) {
      notes.push(cleaned);
    }
  }

  // Need assignments or an explicit plan id — avoid promoting short intro sentences.
  if (!assignments.length && !planId) {
    return null;
  }

  return {
    planId,
    mode: decomposed ? 'decompose' : 'fan_out',
    leadName,
    title: decomposed ? 'Decomposed' : 'Fan-out',
    queued: Number(queuedMatch?.[1] ?? 0) || 0,
    deferred: Number(deferredMatch?.[1] ?? 0) || 0,
    assignments,
    notes,
  };
}

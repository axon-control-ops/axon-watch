/** Explicit "assign / have <Name>" routing — force the named teammate's thread. */

import type { TeammateRouteEmployee } from './composer-teammate-route';
import { normalizeTeammateRole } from './composer-teammate-route';

const ASSIGN_VERBS = String.raw`(?:assign|dispatch|hand[\s-]?off|give|send|route|pass)`;
const HAVE_VERBS = String.raw`(?:have|ask|tell|get)`;

export type NamedAssignMatch = {
  employee: TeammateRouteEmployee;
  matchedAs: string;
};

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function nameTokens(name: string): string[] {
  const full = name.trim();
  if (!full) {
    return [];
  }
  const first = full.split(/\s+/)[0] ?? full;
  const tokens = [full];
  if (first && first.toLowerCase() !== full.toLowerCase() && first.length >= 2) {
    tokens.push(first);
  }
  return tokens;
}

/**
 * Detect an explicit operator assign to a roster teammate by name.
 * Returns the longest matching name so "Sol" does not beat "Solomon".
 */
export function matchNamedAssignEmployee(
  prompt: string,
  roster: readonly TeammateRouteEmployee[] | null | undefined,
): NamedAssignMatch | null {
  const text = String(prompt || '').trim();
  if (!text) {
    return null;
  }
  const employees = (roster ?? []).filter((row) => row.employee_id?.trim() && row.name?.trim());
  if (!employees.length) {
    return null;
  }

  const ranked = [...employees].sort(
    (left, right) =>
      right.name.trim().length - left.name.trim().length ||
      left.name.localeCompare(right.name),
  );

  for (const employee of ranked) {
    for (const token of nameTokens(employee.name)) {
      const escaped = escapeRegExp(token);
      const patterns = [
        new RegExp(String.raw`\b${ASSIGN_VERBS}\b[\s\S]{0,48}\b${escaped}\b`, 'i'),
        new RegExp(String.raw`\b${HAVE_VERBS}\b\s+${escaped}\b`, 'i'),
        new RegExp(String.raw`\b${escaped}\b[\s\S]{0,24}\b(?:should|needs?\s+to|will|can)\b`, 'i'),
        new RegExp(String.raw`@\s*${escaped}\b`, 'i'),
        new RegExp(
          String.raw`\b(?:to|for)\s+${escaped}\b[\s\S]{0,24}\b(?:task|job|work|this|it)\b`,
          'i',
        ),
        new RegExp(
          String.raw`\b(?:task|job|work)\b[\s\S]{0,24}\b(?:to|for)\s+${escaped}\b`,
          'i',
        ),
      ];
      for (const pattern of patterns) {
        if (pattern.test(text)) {
          return { employee, matchedAs: token };
        }
      }
    }
  }
  return null;
}

/** Strip assign-framing so the specialist receives an actionable prompt. */
export function rewriteNamedAssignPrompt(
  prompt: string,
  employeeName: string,
): string {
  const body = namedAssignActionBody(prompt, employeeName);
  return (
    `You own this assignment from Lead. Complete it and report back when done.\n\n` +
    `Operator ask: ${
      body ??
      'Lead did not include a concrete task body in this handoff. Ask Lead/operator for the specific goal, expected files, and acceptance criteria.'
    }`
  );
}

export function namedAssignActionBody(
  prompt: string,
  employeeName: string,
): string | null {
  const text = String(prompt || '').trim();
  if (!text) {
    return null;
  }
  const name = employeeName.trim();
  const first = name.split(/\s+/)[0] || name;
  const tokens = [...new Set([name, first].filter((token) => token.length >= 2))];
  let cleaned = text;
  for (const token of tokens) {
    const escaped = escapeRegExp(token);
    cleaned = cleaned
      .replace(new RegExp(String.raw`\b${ASSIGN_VERBS}\b\s+${escaped}\b`, 'ig'), ' ')
      .replace(new RegExp(String.raw`\b${ASSIGN_VERBS}\b\s+(?:this|the\s+task|it)\s+to\s+${escaped}\b`, 'ig'), ' ')
      .replace(new RegExp(String.raw`\b${HAVE_VERBS}\b\s+${escaped}\b`, 'ig'), ' ')
      .replace(new RegExp(String.raw`@\s*${escaped}\b`, 'ig'), ' ');
  }
  cleaned = cleaned
    .replace(/\b(?:and\s+)?have\s+(?:him|her|them)\s+report\s+back\b/gi, ' ')
    .replace(/\breport\s+back\b/gi, ' ')
    .replace(/\bthe\s+task\b/gi, ' ')
    .replace(/\s{2,}/g, ' ')
    .replace(/^[\s,.;:!?-]+|[\s,.;:!?-]+$/g, '')
    .trim();

  if (cleaned.length < 8) {
    return null;
  }
  if (/^(?:it|this|that|task|job|work|handoff|assignment)$/i.test(cleaned)) {
    return null;
  }
  return cleaned;
}

export function isVagueNamedAssignPrompt(prompt: string, employeeName: string): boolean {
  return namedAssignActionBody(prompt, employeeName) === null;
}

export function namedAssignRouteReason(employee: TeammateRouteEmployee): string {
  return `named_assign_${normalizeTeammateRole(employee.role)}`;
}

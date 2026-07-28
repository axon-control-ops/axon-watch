import type { BriefingAction } from '../../contracts/canonical';

export type ReportTheaterSectionId =
  | 'attention'
  | 'work_in_flight'
  | 'lead_rollups'
  | 'fleet'
  | 'next_move';

export interface ReportTheaterSections {
  attention: string[];
  work_in_flight: string[];
  lead_rollups: string[];
  fleet: string[];
  next_move: string;
}

export interface ReportTheaterPayload {
  sections: ReportTheaterSections;
  fingerprint?: string | null;
  reply?: string;
  spokenReply?: string | null;
}

export interface ReportTheaterStage {
  id: ReportTheaterSectionId;
  title: string;
  lines: string[];
}

export const REPORT_THEATER_STAGE_ORDER: ReportTheaterSectionId[] = [
  'attention',
  'work_in_flight',
  'lead_rollups',
  'fleet',
  'next_move',
];

export const REPORT_THEATER_TITLES: Record<ReportTheaterSectionId, string> = {
  attention: 'Attention',
  work_in_flight: 'Work in flight',
  lead_rollups: 'Lead rollups',
  fleet: 'Fleet',
  next_move: 'Next move',
};

export function emptyReportTheaterSections(): ReportTheaterSections {
  return {
    attention: [],
    work_in_flight: [],
    lead_rollups: [],
    fleet: [],
    next_move: '',
  };
}

export function normalizeReportTheaterSections(
  raw: Partial<ReportTheaterSections> | null | undefined,
): ReportTheaterSections {
  const defaults = emptyReportTheaterSections();
  if (!raw) {
    return defaults;
  }
  const scrub = (item: string): string =>
    String(item || '')
      .replace(/[#*`_]+/g, ' ')
      .replace(/\bLead-team\b/gi, 'Lead team')
      .replace(/\s+/g, ' ')
      .replace(/(?:^|\.\s*)Lead next:\s*$/i, '')
      .trim()
      .replace(/^[:\-\s]+|[:\-\s]+$/g, '');
  return {
    attention: Array.isArray(raw.attention)
      ? raw.attention.map(scrub).filter(Boolean)
      : [],
    work_in_flight: Array.isArray(raw.work_in_flight)
      ? raw.work_in_flight.map(scrub).filter(Boolean)
      : [],
    lead_rollups: Array.isArray(raw.lead_rollups)
      ? raw.lead_rollups.map(scrub).filter(Boolean)
      : [],
    fleet: Array.isArray(raw.fleet) ? raw.fleet.map(scrub).filter(Boolean) : [],
    next_move: scrub(String(raw.next_move || '')),
  };
}

/** Fallback when the API omits structured sections — keep theater usable from flat reply. */
export function parseReportSectionsFromReply(reply: string): ReportTheaterSections {
  const text = String(reply || '').trim();
  const sections = emptyReportTheaterSections();
  if (!text) {
    return sections;
  }

  const attention = text.match(/Attention[,:]\s*(.+?)(?=\s+Work in flight[,:]|$)/i);
  const work = text.match(/Work in flight[,:]\s*(.+?)(?=\s+Lead rollups[,:]|\s+Fleet[,:]|$)/i);
  const lead = text.match(/Lead rollups[,:]\s*(.+?)(?=\s+Fleet[,:]|$)/i);
  const fleet = text.match(/Fleet[,:]\s*(.+?)(?=\s+Next move[,:]|$)/i);
  const next = text.match(/Next move[,:]\s*(.+)$/i);

  const splitBits = (value: string | undefined): string[] => {
    if (!value) {
      return [];
    }
    const cleaned = value.trim().replace(/\.$/, '');
    if (!cleaned || /^nothing screaming$/i.test(cleaned) || /^idle$/i.test(cleaned)) {
      return [];
    }
    if (/^none verified yet$/i.test(cleaned)) {
      return [];
    }
    return cleaned
      .split(/;\s*|,\s+(?=[A-Z])/)
      .map((item) => item.trim())
      .filter(Boolean)
      .slice(0, 6);
  };

  sections.attention = splitBits(attention?.[1]);
  sections.work_in_flight = splitBits(work?.[1]);
  sections.lead_rollups = splitBits(lead?.[1]);
  sections.fleet = splitBits(fleet?.[1]);
  sections.next_move = (next?.[1] || '').trim().replace(/\.$/, '');
  if (!sections.next_move && !sections.attention.length && !sections.work_in_flight.length) {
    sections.next_move = text.slice(0, 280);
  }
  return sections;
}

export function buildReportTheaterStages(
  sections: ReportTheaterSections,
): ReportTheaterStage[] {
  return REPORT_THEATER_STAGE_ORDER.map((id) => {
    if (id === 'next_move') {
      const line = sections.next_move.trim();
      return {
        id,
        title: REPORT_THEATER_TITLES[id],
        lines: line ? [line] : ['Nothing urgent — standing by for your next order.'],
      };
    }
    const lines = sections[id];
    return {
      id,
      title: REPORT_THEATER_TITLES[id],
      lines: lines.length
        ? lines
        : [
            id === 'attention'
              ? 'Nothing screaming.'
              : id === 'work_in_flight'
                ? 'Idle.'
                : id === 'lead_rollups'
                  ? 'Lead standing by on the board.'
                  : 'Fleet telemetry quiet.',
          ],
    };
  });
}

export function reportTheaterStageDurationMs(stage: ReportTheaterStage): number {
  const chars = stage.lines.join(' ').length;
  return Math.max(2200, Math.min(7000, 1600 + chars * 18));
}

export function pickReportTheaterActions(
  actions: BriefingAction[] | null | undefined,
  limit = 3,
): BriefingAction[] {
  if (!Array.isArray(actions) || !actions.length) {
    return [];
  }
  return actions.slice(0, limit);
}

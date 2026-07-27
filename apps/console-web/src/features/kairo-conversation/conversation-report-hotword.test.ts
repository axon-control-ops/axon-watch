import { describe, expect, it } from 'vitest';

import {
  expandReportHotword,
  REPORT_EXPANDED_PROMPT,
} from './conversation-report-hotword';

describe('expandReportHotword', () => {
  it('expands bare REPORT', () => {
    expect(expandReportHotword('REPORT')).toBe(REPORT_EXPANDED_PROMPT);
    expect(expandReportHotword('report')).toBe(REPORT_EXPANDED_PROMPT);
    expect(expandReportHotword('Status report.')).toBe(REPORT_EXPANDED_PROMPT);
  });

  it('expands update and status aliases', () => {
    expect(expandReportHotword('update')).toBe(REPORT_EXPANDED_PROMPT);
    expect(expandReportHotword('Status')).toBe(REPORT_EXPANDED_PROMPT);
  });

  it('expands stand-up phrasing', () => {
    expect(expandReportHotword('standup')).toBe(REPORT_EXPANDED_PROMPT);
    expect(expandReportHotword('where are we stand')).toBeNull();
    expect(expandReportHotword('where do we stand')).toBe(REPORT_EXPANDED_PROMPT);
  });

  it('leaves ordinary asks alone', () => {
    expect(expandReportHotword('report this Sentry spike to Dana')).toBeNull();
    expect(expandReportHotword('Open DashPro workspace')).toBeNull();
  });
});

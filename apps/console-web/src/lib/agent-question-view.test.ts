import { describe, expect, it } from 'vitest';

import {
  formatAnsweredQuestionChoice,
  formatQuestionAnswer,
  moveQuestionOptionSelection,
  normalizeAskOptionLabel,
  parseAskOptions,
  resolveAskBlockPrompt,
  truncateQuestionOptionLabel,
  tryParseClarifyingMarkdown,
  withOtherQuestionOption,
} from './agent-question-view';
import { parseAgentTranscriptBlocks } from './agent-transcript-blocks';

describe('agent question view', () => {
  it('parses :::ask fences into question segments', () => {
    const segments = parseAgentTranscriptBlocks(
      [
        ':::ask What should this plan focus on?',
        '- 1 | Employee / coordination gaps',
        '- 2 | Mobile remote control',
        '- 3 | Both, phased',
        ':::',
      ].join('\n'),
    );
    expect(segments).toHaveLength(1);
    expect(segments[0]).toMatchObject({
      kind: 'question',
      prompt: 'What should this plan focus on?',
    });
    if (segments[0]?.kind === 'question') {
      expect(segments[0].options).toEqual([
        { id: '1', label: 'Employee / coordination gaps' },
        { id: '2', label: 'Mobile remote control' },
        { id: '3', label: 'Both, phased' },
      ]);
    }
  });

  it('upgrades plain clarifying markdown into a question card', () => {
    const text = [
      'What should this plan focus on?',
      '',
      '1. Employee / coordination gaps',
      '2. Mobile remote control',
      '3. Both, phased',
      '',
      'Reply with `1`, `2`, or `3`.',
    ].join('\n');
    const parsed = tryParseClarifyingMarkdown(text);
    expect(parsed?.options).toHaveLength(3);
    expect(parsed?.prompt.toLowerCase()).toContain('what should this plan focus');

    const segments = parseAgentTranscriptBlocks(text);
    expect(segments.some((segment) => segment.kind === 'question')).toBe(true);
  });

  it('parses pipe options and formats answers with id and label', () => {
    expect(
      parseAskOptions(['- 1 | Alpha', '- 2 | Beta']),
    ).toEqual([
      { id: '1', label: 'Alpha' },
      { id: '2', label: 'Beta' },
    ]);
    expect(formatQuestionAnswer({ id: '3', label: 'Both, phased' })).toBe(
      'Selected option 3: Both, phased',
    );
    expect(
      formatQuestionAnswer({ id: '3', label: 'Both, phased' }, 'What should this plan focus on?'),
    ).toBe(
      ['Selected option 3: Both, phased', '(answer to: What should this plan focus on?)'].join(
        '\n',
      ),
    );
  });

  it('uses a short header prompt when ask body is a status dump', () => {
    const dump = 'ActionRequiredError: out of usage. '.repeat(40);
    const segments = parseAgentTranscriptBlocks(
      [
        ':::ask Ready to proceed?',
        dump,
        '- 1 | Added tests/test_connector_signal.py',
        '- 2 | Updated scripts/verify/run_contract_unit_tests.sh',
        ':::',
      ].join('\n'),
    );
    expect(segments).toHaveLength(1);
    expect(segments[0]).toMatchObject({
      kind: 'question',
      prompt: 'Ready to proceed?',
    });
  });

  it('falls back to a generic prompt when ask body is prose without a header', () => {
    const segments = parseAgentTranscriptBlocks(
      [
        ':::ask',
        'ActionRequiredError: out of usage.',
        'Coverage is still missing for connector signals.',
        '- 1 | Added tests/test_connector_signal.py',
        '- 2 | Updated scripts/verify/run_contract_unit_tests.sh',
        ':::',
      ].join('\n'),
    );
    expect(segments[0]).toMatchObject({
      kind: 'question',
      prompt: 'Choose an option to continue',
    });
  });

  it('does not upgrade long status dumps into question cards', () => {
    const text = [
      'ActionRequiredError: out of usage.',
      'Coverage is still missing for connector signals.',
      '1. Added tests/test_connector_signal.py',
      '2. Updated scripts/verify/run_contract_unit_tests.sh',
    ].join('\n');
    expect(tryParseClarifyingMarkdown(text)).toBeNull();
  });

  it('does not upgrade reports with duplicate numbered sections into ask cards', () => {
    const report = [
      'Status after picking a birthday child.',
      '',
      '1. **Database** — Added party_pack.collected_at (migration applied).',
      '2. **Backend** — Edge function supports marking party pack handouts.',
      '3. **Teacher UI** — After picking a birthday child and marking payments:',
      '1. Pick the birthday child',
      '2. Mark who paid (R25)',
      '3. Open **Party packs** > mark each learner',
    ].join('\n');
    expect(tryParseClarifyingMarkdown(report)).toBeNull();
  });

  it('does not treat "picking" in status prose as an ask cue', () => {
    const text = [
      'After picking a birthday child and marking payments:',
      '1. Database migration applied',
      '2. Backend deployed',
      '3. Teacher UI updated',
    ].join('\n');
    expect(tryParseClarifyingMarkdown(text)).toBeNull();
  });

  it('strips markdown emphasis from option labels', () => {
    expect(normalizeAskOptionLabel('**Database** — Added columns')).toBe(
      'Database — Added columns',
    );
    expect(
      parseAskOptions([
        '1. **Database** — Added party_pack.collected_at',
        '2. Open **Party packs** > mark each learner',
      ]),
    ).toEqual([
      { id: '1', label: 'Database — Added party_pack.collected_at' },
      { id: '2', label: 'Open Party packs > mark each learner' },
    ]);
  });

  it('truncates long option labels for display', () => {
    const label = 'Updated '.concat('scripts/verify/run_contract_unit_tests.sh '.repeat(8));
    expect(truncateQuestionOptionLabel(label).endsWith('…')).toBe(true);
    expect(resolveAskBlockPrompt({
      headerPrompt: 'Proceed?',
      bodyLines: [],
      options: [{ id: '1', label: 'Yes' }],
    })).toBe('Proceed?');
  });

  it('formats answered choices without raw option ids', () => {
    expect(formatAnsweredQuestionChoice({ id: '2', label: 'Mobile remote control' })).toBe(
      'Mobile remote control',
    );
    expect(formatAnsweredQuestionChoice({ id: 'other', label: 'Use local docs only' })).toBe(
      'Use local docs only',
    );
    expect(formatAnsweredQuestionChoice({ id: 'other', label: 'Other' })).toBe('Other');
  });

  it('moves question option selection with wrap-around', () => {
    const options = [
      { id: '1', label: 'Alpha' },
      { id: '2', label: 'Beta' },
      { id: 'other', label: 'Other' },
    ];
    expect(moveQuestionOptionSelection(options, '1', 'next')).toBe('2');
    expect(moveQuestionOptionSelection(options, '2', 'next')).toBe('other');
    expect(moveQuestionOptionSelection(options, 'other', 'next')).toBe('1');
    expect(moveQuestionOptionSelection(options, '1', 'prev')).toBe('other');
  });

  it('appends a single Other option and formats free-text answers', () => {
    expect(withOtherQuestionOption([
      { id: '1', label: 'Alpha' },
      { id: '2', label: 'Beta' },
    ])).toEqual([
      { id: '1', label: 'Alpha' },
      { id: '2', label: 'Beta' },
      { id: 'other', label: 'Other' },
    ]);
    expect(
      withOtherQuestionOption([
        { id: '1', label: 'Alpha' },
        { id: 'other', label: 'Other' },
      ]),
    ).toHaveLength(2);
    expect(
      formatQuestionAnswer({ id: 'other', label: 'Other' }, 'Ready?', 'Use local docs only'),
    ).toBe(
      [
        'Selected option other: Use local docs only',
        '(answer to: Ready?)',
      ].join('\n'),
    );
  });
});

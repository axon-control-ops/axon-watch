import { describe, expect, it } from 'vitest';

import {
  formatSupportedCommandsHint,
  OPERATOR_SUPPORTED_COMMANDS,
} from './operator-supported-commands';

describe('operator supported commands', () => {
  it('lists the v1 command executor surface', () => {
    expect(OPERATOR_SUPPORTED_COMMANDS.map((command) => command.id)).toEqual([
      'health_probe',
      'list_files',
      'read_file',
      'git_status',
      'resume_from_review',
    ]);
  });

  it('formats a hint block for unsupported command responses', () => {
    expect(formatSupportedCommandsHint()).toContain('git status');
    expect(formatSupportedCommandsHint()).toContain('resume from review');
  });
});

export interface OperatorSupportedCommand {
  id: string;
  examples: string[];
  description: string;
}

/** Keep in sync with services/control-plane/app/chat/command_executor.py hints. */
export const OPERATOR_SUPPORTED_COMMANDS: OperatorSupportedCommand[] = [
  {
    id: 'health_probe',
    examples: ['health', 'api/health'],
    description: 'Probe control-plane health',
  },
  {
    id: 'list_files',
    examples: ['ls', 'list files'],
    description: 'List workspace files',
  },
  {
    id: 'read_file',
    examples: ['read README.md', 'cat notes.txt'],
    description: 'Read a workspace file',
  },
  {
    id: 'git_status',
    examples: ['git status'],
    description: 'Show git status in the workspace project root',
  },
  {
    id: 'resume_from_review',
    examples: ['resume from review'],
    description: 'Resume the primary review_ready run',
  },
  {
    id: 'shell_command',
    examples: [
      'run npm test',
      'run ./scripts/dev/check-health.sh',
      'check-health',
      'ota canary',
      'verify',
      'run npm run verify:production-operator',
    ],
    description: 'Run a bounded shell command in the workspace project root',
  },
];

export function formatSupportedCommandsHint(): string {
  return OPERATOR_SUPPORTED_COMMANDS.map((command) => {
    const example = command.examples[0] ?? command.id;
    return `• ${example} — ${command.description}`;
  }).join('\n');
}

import type { OperatorThreadEntry } from './operator-thread';

const COMMAND_EXECUTION_RE =
  /^Executed `([^`]+)` \((ok|failed)\) for run (\S+)\.\n\n```(?:[^\n]*\n)?([\s\S]*?)```(?:\n\n([\s\S]+))?$/i;

export interface CommandExecutionDisplay {
  intent: string;
  status: 'ok' | 'failed';
  runId: string;
  output: string;
  footer: string | null;
}

export type ConversationDisplayItem =
  | {
      kind: 'command_turn';
      messageId: string;
      command: string;
      runId: string | null;
      createdAt: string;
      execution: CommandExecutionDisplay;
      compact?: boolean;
      repeatCount?: number;
    }
  | {
      kind: 'message';
      message: OperatorThreadEntry;
    }
  | {
      kind: 'dock_banner';
      messageId: string;
      text: string;
    };

export interface OperatorConversationDockView {
  items: ConversationDisplayItem[];
  hiddenCount: number;
}

const REPEAT_COLLAPSE_COMMANDS = new Set([
  'git status',
  'check-health',
  'run npm test',
  'run ./scripts/dev/check-health.sh',
]);

const DEFAULT_OPERATOR_CONVERSATION_LIMIT = 6;

function normalizeCommandKey(command: string): string {
  return command.trim().toLowerCase();
}

function shouldCollapseRepeatedCommand(command: string): boolean {
  return REPEAT_COLLAPSE_COMMANDS.has(normalizeCommandKey(command));
}

function isCommandTurnItem(
  item: ConversationDisplayItem,
): item is Extract<ConversationDisplayItem, { kind: 'command_turn' }> {
  return item.kind === 'command_turn';
}

export function isCommandDispatchAck(content: string): boolean {
  const trimmed = content.trim();
  return (
    /^Run run_\S+ dispatched/i.test(trimmed) ||
    /^Command linked to run run_/i.test(trimmed)
  );
}

export function isCommandExecutionReply(content: string): boolean {
  return /^Executed `[^`]+`/i.test(content.trim());
}

export function parseCommandExecutionContent(content: string): CommandExecutionDisplay | null {
  const trimmed = content.trim();
  const match = trimmed.match(COMMAND_EXECUTION_RE);
  if (!match) {
    return null;
  }

  const [, intent, status, runId, output, footerRaw] = match;
  const footer = footerRaw?.trim() || null;
  const normalizedFooter =
    footer && /^phase is now /i.test(footer) && !/review when ready/i.test(footer)
      ? footer
      : footer && !/review when ready/i.test(footer)
        ? footer
        : null;

  return {
    intent: intent.trim(),
    status: status.toLowerCase() === 'failed' ? 'failed' : 'ok',
    runId: runId.trim(),
    output: output.trim(),
    footer: normalizedFooter,
  };
}

function hasRenderableContent(message: OperatorThreadEntry): boolean {
  return Boolean(message.content.trim());
}

export function buildOperatorConversationDisplay(
  messages: OperatorThreadEntry[],
): ConversationDisplayItem[] {
  const items: ConversationDisplayItem[] = [];

  for (let index = 0; index < messages.length; index += 1) {
    const operator = messages[index];
    if (!operator || !hasRenderableContent(operator)) {
      continue;
    }

    const system = messages[index + 1];
    const agent = messages[index + 2];

    if (
      operator.role === 'operator' &&
      system?.role === 'system' &&
      isCommandDispatchAck(system.content) &&
      agent?.role === 'agent' &&
      isCommandExecutionReply(agent.content)
    ) {
      const execution = parseCommandExecutionContent(agent.content);
      if (execution) {
        items.push({
          kind: 'command_turn',
          messageId: agent.message_id,
          command: operator.content.trim(),
          runId: agent.run_id ?? execution.runId,
          createdAt: agent.created_at,
          execution,
        });
        index += 2;
        continue;
      }
    }

    if (operator.role === 'system' && isCommandDispatchAck(operator.content)) {
      continue;
    }

    if (
      operator.role === 'agent' &&
      isCommandExecutionReply(operator.content) &&
      parseCommandExecutionContent(operator.content)
    ) {
      const execution = parseCommandExecutionContent(operator.content);
      if (execution) {
        items.push({
          kind: 'command_turn',
          messageId: operator.message_id,
          command: execution.intent.replace(/_/g, ' '),
          runId: operator.run_id ?? execution.runId,
          createdAt: operator.created_at,
          execution,
        });
        continue;
      }
    }

    items.push({
      kind: 'message',
      message: operator,
    });
  }

  return items;
}

export function collapseRepeatedOperatorCommands(
  items: ConversationDisplayItem[],
): ConversationDisplayItem[] {
  const lastIndexByCommand = new Map<string, number>();
  for (let index = 0; index < items.length; index += 1) {
    const item = items[index];
    if (!isCommandTurnItem(item) || !shouldCollapseRepeatedCommand(item.command)) {
      continue;
    }
    lastIndexByCommand.set(normalizeCommandKey(item.command), index);
  }

  const repeatCounts = new Map<string, number>();
  for (const item of items) {
    if (!isCommandTurnItem(item) || !shouldCollapseRepeatedCommand(item.command)) {
      continue;
    }
    const key = normalizeCommandKey(item.command);
    repeatCounts.set(key, (repeatCounts.get(key) ?? 0) + 1);
  }

  const collapsed: ConversationDisplayItem[] = [];
  for (let index = 0; index < items.length; index += 1) {
    const item = items[index];
    if (!isCommandTurnItem(item) || !shouldCollapseRepeatedCommand(item.command)) {
      collapsed.push(item);
      continue;
    }

    const key = normalizeCommandKey(item.command);
    if (lastIndexByCommand.get(key) !== index) {
      continue;
    }

    const repeatCount = repeatCounts.get(key) ?? 1;
    collapsed.push({
      ...item,
      compact: repeatCount > 1,
      repeatCount,
    });
  }

  return collapsed;
}

export function prepareOperatorConversationDock(
  messages: OperatorThreadEntry[],
  options?: { maxItems?: number },
): OperatorConversationDockView {
  const maxItems = options?.maxItems ?? DEFAULT_OPERATOR_CONVERSATION_LIMIT;
  const expanded = buildOperatorConversationDisplay(messages);
  const collapsed = collapseRepeatedOperatorCommands(expanded);
  const hiddenCount = Math.max(0, collapsed.length - maxItems);
  const visible = collapsed.slice(-maxItems);

  const items: ConversationDisplayItem[] = [];
  if (hiddenCount > 0) {
    items.push({
      kind: 'dock_banner',
      messageId: `dock_banner_${hiddenCount}`,
      text: `${hiddenCount} earlier conversation entries hidden. Mission Control holds the run queue — use Complete all to clear verification backlog.`,
    });
  }

  return {
    items: [...items, ...visible],
    hiddenCount,
  };
}

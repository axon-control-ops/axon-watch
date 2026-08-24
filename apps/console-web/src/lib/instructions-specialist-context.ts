import type { CompanyEmployeeRecord, WorkspaceRecord } from '../contracts/canonical';
import type { GenerateInstructionsRequest } from '../api/chat-api';
import type { ComposerMode } from '../composables/useAgentDockComposer';

export function instructionsSpecialistLabel(
  employee: CompanyEmployeeRecord | null | undefined,
): string {
  const roleLabel = employee?.role_label?.trim() || employee?.role?.trim();
  const agentName = employee?.name?.trim();
  if (roleLabel && agentName) {
    return `${roleLabel} instructions for ${agentName}`;
  }
  if (roleLabel) {
    return `${roleLabel} instructions`;
  }
  return 'detailed Markdown instructions';
}

export function buildInstructionsSpecialistContext(input: {
  workspace: WorkspaceRecord;
  employee: CompanyEmployeeRecord | null | undefined;
  composerMode: ComposerMode;
}): NonNullable<GenerateInstructionsRequest['specialist_context']> {
  const employee = input.employee;
  return {
    role: employee?.role ?? null,
    agent_name: employee?.name ?? null,
    employee_id: employee?.employee_id ?? null,
    workspace_id: input.workspace.workspace_id,
    workspace_label: input.workspace.display_name ?? null,
    composer_mode: input.composerMode,
    requested_delivery_mode: input.composerMode,
    allowed_paths: null,
    read_scope: null,
    write_scope: null,
    delivery_capabilities: null,
    owns: employee?.owns ?? null,
  };
}

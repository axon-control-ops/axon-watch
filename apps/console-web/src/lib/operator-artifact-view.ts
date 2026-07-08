import { ref } from 'vue';

import type { ChatUiAction } from './chat-ui-action';
import type { KairoConverseArtifact } from './kairo-converse-client';

export interface OperatorArtifactSource {
  label: string;
  detail: string;
}

export interface OperatorArtifactAction {
  label: string;
  uiAction: ChatUiAction | null;
}

export interface OperatorArtifactRecord {
  artifactId: string;
  title: string;
  summary: string;
  body: string;
  createdAt: string;
  sources: OperatorArtifactSource[];
  actions: OperatorArtifactAction[];
}

export const operatorArtifactRecords = ref<OperatorArtifactRecord[]>([]);

export function clearOperatorArtifacts(): void {
  operatorArtifactRecords.value = [];
}

export function recordOperatorArtifacts(
  artifacts: KairoConverseArtifact[],
  parseUiAction: (value: unknown) => ChatUiAction | null,
): void {
  if (!artifacts.length) {
    return;
  }
  const existing = new Map(
    operatorArtifactRecords.value.map((artifact) => [artifact.artifactId, artifact]),
  );
  for (const artifact of artifacts) {
    const next: OperatorArtifactRecord = {
      artifactId: artifact.artifact_id,
      title: artifact.title.trim() || 'VAXON artifact',
      summary: artifact.summary.trim(),
      body: artifact.body.trim(),
      createdAt: new Date().toISOString(),
      sources: (artifact.sources ?? [])
        .map((source) => ({
          label: source.label.trim(),
          detail: source.detail.trim(),
        }))
        .filter((source) => source.label || source.detail),
      actions: (artifact.actions ?? [])
        .map((action) => ({
          label: String(action.label ?? '').trim(),
          uiAction: parseUiAction(action.ui_action),
        }))
        .filter((action) => action.label),
    };
    existing.set(next.artifactId, next);
  }
  operatorArtifactRecords.value = [...existing.values()]
    .sort((left, right) => left.createdAt.localeCompare(right.createdAt))
    .slice(-8);
}

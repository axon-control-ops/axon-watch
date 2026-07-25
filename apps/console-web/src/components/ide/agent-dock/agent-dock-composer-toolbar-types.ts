export type AgentDockComposerRuntimeTarget = {
  id: string;
  label: string;
  ready: boolean;
  available: boolean;
  auth: { message?: string };
};

export type AgentDockComposerAttachmentChip = {
  key: string;
  label: string;
  kind: string;
  title?: string;
};

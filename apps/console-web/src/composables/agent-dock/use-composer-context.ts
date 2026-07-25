import { computed, ref } from 'vue';

import {
  composerDraftIncludesToken,
  readStoredTerminalSnippet,
  SELECTION_CONTEXT_TOKEN,
  TERMINAL_CONTEXT_TOKEN,
} from '../../lib/ide-composer-context-tokens';
import {
  composerSkillSlugFromPath,
  isComposerSkillFilePath,
  listComposerSkillFileTokens,
  prependComposerSkillFileTokens,
  stripComposerSkillFileTokens,
  type ComposerSkillFileToken,
} from '../../lib/composer-slash-skills-view';
import { useShellStore } from '../../stores/shell';

type ShellStore = ReturnType<typeof useShellStore>;

export type ComposerSkillAttachment = {
  path: string;
  slug: string;
  label: string;
};

export function useComposerContext(shell: ShellStore) {
  const contextWorkspace = ref(false);
  const contextActiveFile = ref(false);
  const contextSelection = ref(false);
  const contextTerminal = ref(false);
  const contextIde = ref(false);
  const contextPinned = ref(false);
  const skillAttachments = ref<ComposerSkillAttachment[]>([]);

  const activeFileToken = computed(() =>
    shell.activeWorkspaceFilePath ? `@file:${shell.activeWorkspaceFilePath}` : null,
  );
  const workspaceToken = computed(() =>
    shell.currentWorkspace?.workspace_id ? `@workspace:${shell.currentWorkspace.workspace_id}` : null,
  );
  const ideToken = '@ide-context';
  const pinnedToken = '@pin-context';
  const selectionToken = SELECTION_CONTEXT_TOKEN;
  const terminalToken = TERMINAL_CONTEXT_TOKEN;
  const hasTerminalSnippet = computed(() =>
    shell.currentWorkspace?.workspace_id
      ? Boolean(readStoredTerminalSnippet(shell.currentWorkspace.workspace_id))
      : false,
  );
  const selectionChipLabel = computed(() => {
    const selection = shell.editorSelection;
    if (!selection?.text.trim()) {
      return 'Selection';
    }
    if (selection.startLine === selection.endLine) {
      return `L${selection.startLine}`;
    }
    return `L${selection.startLine}-${selection.endLine}`;
  });

  function toSkillAttachment(token: ComposerSkillFileToken | ComposerSkillAttachment): ComposerSkillAttachment {
    return {
      path: token.path,
      slug: token.slug,
      label: token.label || token.slug,
    };
  }

  function upsertSkillAttachment(path: string, label?: string): void {
    const cleaned = path.trim();
    if (!cleaned || !isComposerSkillFilePath(cleaned)) {
      return;
    }
    const slug = composerSkillSlugFromPath(cleaned);
    const next: ComposerSkillAttachment = {
      path: cleaned,
      slug,
      label: (label ?? slug).trim() || slug,
    };
    if (skillAttachments.value.some((row) => row.path === cleaned)) {
      return;
    }
    skillAttachments.value = [...skillAttachments.value, next];
  }

  function clearSkillAttachments(): void {
    skillAttachments.value = [];
  }

  function promoteSkillTokensFromDraft(): void {
    const tokens = listComposerSkillFileTokens(shell.ideComposerDraft);
    if (!tokens.length) {
      return;
    }
    for (const token of tokens) {
      upsertSkillAttachment(token.path, token.label);
    }
    shell.ideComposerDraft = stripComposerSkillFileTokens(shell.ideComposerDraft);
  }

  function withSkillTokensForSubmit(draft: string): string {
    return prependComposerSkillFileTokens(
      draft,
      skillAttachments.value.map((row) => row.path),
    );
  }

  const attachmentChips = computed(() => {
    const chips: Array<{ key: string; label: string; kind: string; title?: string }> = [];
    for (const skill of skillAttachments.value) {
      chips.push({
        key: `skill:${skill.path}`,
        kind: 'skill',
        label: skill.label,
        title: skill.path,
      });
    }
    if (contextWorkspace.value && shell.currentWorkspace?.workspace_id) {
      chips.push({
        key: 'workspace',
        kind: 'workspace',
        label: shell.currentWorkspace.workspace_id,
      });
    }
    if (contextActiveFile.value && shell.activeWorkspaceFilePath) {
      chips.push({
        key: 'file',
        kind: 'file',
        label: shell.activeWorkspaceFilePath,
      });
    }
    if (contextSelection.value && shell.hasEditorSelection) {
      chips.push({
        key: 'selection',
        kind: 'selection',
        label: selectionChipLabel.value,
      });
    }
    if (contextTerminal.value && hasTerminalSnippet.value) {
      chips.push({
        key: 'terminal',
        kind: 'terminal',
        label: 'Terminal output',
      });
    }
    if (contextIde.value) {
      chips.push({ key: 'ide', kind: 'ide', label: 'IDE context' });
    }
    if (contextPinned.value) {
      chips.push({ key: 'pin', kind: 'pin', label: 'Pinned' });
    }
    return chips;
  });

  function normalizeDraft(text: string): string {
    return text
      .replace(/[ \t]+\n/g, '\n')
      .replace(/\n{3,}/g, '\n\n')
      .trim();
  }

  function setTokenEnabled(token: string | null, enabled: boolean): void {
    if (!token) return;
    const escaped = token.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const pattern = new RegExp(`(^|\\s)${escaped}(?=\\s|$)`, 'g');
    let draft = shell.ideComposerDraft;
    draft = draft.replace(pattern, ' ').replace(/[ ]{2,}/g, ' ');
    draft = normalizeDraft(draft);
    if (enabled) {
      draft = draft ? `${token}\n${draft}` : token;
    }
    shell.ideComposerDraft = draft;
  }

  function toggleContext(kind: 'workspace' | 'file' | 'selection' | 'terminal' | 'ide' | 'pin'): void {
    if (kind === 'workspace') {
      contextWorkspace.value = !contextWorkspace.value;
      setTokenEnabled(workspaceToken.value, contextWorkspace.value);
      return;
    }
    if (kind === 'file') {
      contextActiveFile.value = !contextActiveFile.value;
      setTokenEnabled(activeFileToken.value, contextActiveFile.value);
      return;
    }
    if (kind === 'selection') {
      contextSelection.value = !contextSelection.value;
      setTokenEnabled(selectionToken, contextSelection.value);
      return;
    }
    if (kind === 'terminal') {
      contextTerminal.value = !contextTerminal.value;
      setTokenEnabled(terminalToken, contextTerminal.value);
      return;
    }
    if (kind === 'ide') {
      contextIde.value = !contextIde.value;
      setTokenEnabled(ideToken, contextIde.value);
      return;
    }
    contextPinned.value = !contextPinned.value;
    setTokenEnabled(pinnedToken, contextPinned.value);
  }

  function removeChip(key: string): void {
    if (key.startsWith('skill:')) {
      const path = key.slice('skill:'.length);
      skillAttachments.value = skillAttachments.value.filter((row) => row.path !== path);
      return;
    }
    if (key === 'workspace') {
      contextWorkspace.value = false;
      setTokenEnabled(workspaceToken.value, false);
      return;
    }
    if (key === 'file') {
      contextActiveFile.value = false;
      setTokenEnabled(activeFileToken.value, false);
      return;
    }
    if (key === 'selection') {
      contextSelection.value = false;
      setTokenEnabled(selectionToken, false);
      return;
    }
    if (key === 'terminal') {
      contextTerminal.value = false;
      setTokenEnabled(terminalToken, false);
      return;
    }
    if (key === 'ide') {
      contextIde.value = false;
      setTokenEnabled(ideToken, false);
      return;
    }
    contextPinned.value = false;
    setTokenEnabled(pinnedToken, false);
  }

  function syncContextFromDraft(): void {
    promoteSkillTokensFromDraft();
    const draft = shell.ideComposerDraft;
    if (workspaceToken.value) {
      contextWorkspace.value = composerDraftIncludesToken(draft, workspaceToken.value);
    }
    if (activeFileToken.value) {
      contextActiveFile.value = composerDraftIncludesToken(draft, activeFileToken.value);
    }
    contextSelection.value = composerDraftIncludesToken(draft, selectionToken);
    contextTerminal.value = composerDraftIncludesToken(draft, terminalToken);
    contextIde.value = composerDraftIncludesToken(draft, ideToken);
    contextPinned.value = composerDraftIncludesToken(draft, pinnedToken);
  }

  return {
    contextWorkspace,
    contextActiveFile,
    contextSelection,
    contextTerminal,
    contextIde,
    contextPinned,
    skillAttachments,
    activeFileToken,
    workspaceToken,
    ideToken,
    pinnedToken,
    selectionToken,
    terminalToken,
    hasTerminalSnippet,
    selectionChipLabel,
    attachmentChips,
    normalizeDraft,
    setTokenEnabled,
    toggleContext,
    removeChip,
    syncContextFromDraft,
    upsertSkillAttachment,
    clearSkillAttachments,
    promoteSkillTokensFromDraft,
    withSkillTokensForSubmit,
    toSkillAttachment,
  };
}

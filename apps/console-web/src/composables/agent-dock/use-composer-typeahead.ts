import { computed, nextTick, ref, type Ref } from 'vue';

import { fetchSkillsSnapshot, type OperatorSkillRecord } from '../../api/skills-api';
import {
  buildMentionFileRows,
  mentionInsertionForPath,
  type MentionFileRow,
} from '../../lib/composer-mention-files-view';
import {
  applySlashSkillToDraft,
  buildSlashPaletteCatalog,
  filterSlashPaletteRows,
  isComposerSkillFilePath,
  longestCommonSlashPrefix,
  resolveSlashTabAction,
  SLASH_STATUS_PROMPT,
  slashHelpText,
  type SlashPaletteRow,
} from '../../lib/composer-slash-skills-view';
import {
  detectComposerCaretToken,
  replaceComposerToken,
  type ComposerCaretToken,
} from '../../lib/composer-typeahead-trigger';
import { useShellStore } from '../../stores/shell';
import type { ComposerMode } from './use-composer-menus';

type ShellStore = ReturnType<typeof useShellStore>;

export type ComposerTypeaheadRow = SlashPaletteRow | MentionFileRow;

type UseComposerTypeaheadOptions = {
  shell: ShellStore;
  composerMode: Ref<ComposerMode>;
  inputRef: Ref<HTMLTextAreaElement | null>;
  getDraft: () => string;
  setDraft: (value: string) => void;
  closeToolbarMenus: () => void;
  /** Attach a skill as a Cursor-style chip instead of raw `@file:` text. */
  attachSkill?: (path: string, label?: string) => void;
};

export function useComposerTypeahead(options: UseComposerTypeaheadOptions) {
  const {
    shell,
    composerMode,
    inputRef,
    getDraft,
    setDraft,
    closeToolbarMenus,
    attachSkill,
  } = options;

  const open = ref(false);
  const kind = ref<'slash' | 'mention' | null>(null);
  const query = ref('');
  const selectedIndex = ref(0);
  const activeToken = ref<ComposerCaretToken | null>(null);
  const loading = ref(false);
  const skillsCache = ref<OperatorSkillRecord[]>([]);
  const skillsLoaded = ref(false);

  const leadThread = computed(() => {
    const role = String(shell.activeIdeEmployeeRecord?.role || '')
      .trim()
      .toLowerCase();
    return role === 'lead';
  });

  const slashCatalog = computed(() =>
    buildSlashPaletteCatalog(skillsCache.value, shell.currentWorkspace?.workspace_id, {
      leadThread: leadThread.value,
    }),
  );

  const slashRows = computed(() => {
    if (kind.value !== 'slash') {
      return [] as SlashPaletteRow[];
    }
    return filterSlashPaletteRows(slashCatalog.value, query.value);
  });

  const mentionRows = computed(() => {
    if (kind.value !== 'mention') {
      return [] as MentionFileRow[];
    }
    return buildMentionFileRows(shell.workspaceFileEntries, query.value);
  });

  const rows = computed<ComposerTypeaheadRow[]>(() =>
    kind.value === 'mention' ? mentionRows.value : slashRows.value,
  );

  const caption = computed(() => {
    if (kind.value === 'mention') {
      return 'Mention a file';
    }
    if (kind.value === 'slash') {
      return leadThread.value
        ? 'Lead commands — /ask answers · /agent fans out'
        : 'Commands & skills';
    }
    return '';
  });

  const emptyHint = computed(() => {
    if (kind.value !== 'slash' || loading.value) {
      return 'No matches';
    }
    const q = query.value.trim();
    if (!q) {
      return 'No commands available';
    }
    return `No matches for /${q.replace(/^\//, '')} — try /ask, /status, or /help`;
  });

  function closeTypeahead(): void {
    open.value = false;
    kind.value = null;
    query.value = '';
    selectedIndex.value = 0;
    activeToken.value = null;
    loading.value = false;
  }

  async function ensureSkillsLoaded(): Promise<void> {
    if (skillsLoaded.value) {
      return;
    }
    loading.value = true;
    try {
      const snapshot = await fetchSkillsSnapshot();
      skillsCache.value = snapshot.items;
      skillsLoaded.value = true;
    } catch {
      skillsCache.value = [];
      skillsLoaded.value = true;
    } finally {
      loading.value = false;
    }
  }

  async function ensureFilesLoaded(): Promise<void> {
    if (shell.workspaceFileEntries.length > 0) {
      return;
    }
    loading.value = true;
    try {
      await shell.loadWorkspaceFiles();
    } finally {
      loading.value = false;
    }
  }

  function restoreCaret(caret: number): void {
    void nextTick(() => {
      const el = inputRef.value;
      if (!el) {
        return;
      }
      el.focus();
      el.setSelectionRange(caret, caret);
    });
  }

  function clampSelectedIndex(previousId?: string): void {
    const list = rows.value;
    if (!list.length) {
      selectedIndex.value = 0;
      return;
    }
    if (previousId) {
      const kept = list.findIndex((row) => 'id' in row && row.id === previousId);
      if (kept >= 0) {
        selectedIndex.value = kept;
        return;
      }
    }
    selectedIndex.value = Math.max(0, Math.min(selectedIndex.value, list.length - 1));
  }

  let syncSeq = 0;

  async function syncTypeaheadFromComposer(): Promise<void> {
    const seq = ++syncSeq;
    const el = inputRef.value;
    const draft = getDraft();
    const caret = el?.selectionStart ?? draft.length;
    const token = detectComposerCaretToken(draft, caret);
    if (!token) {
      closeTypeahead();
      return;
    }

    const previousId =
      rows.value[selectedIndex.value] && 'id' in rows.value[selectedIndex.value]
        ? (rows.value[selectedIndex.value] as { id: string }).id
        : undefined;
    const queryChanged = token.query !== query.value || token.kind !== kind.value;

    closeToolbarMenus();
    activeToken.value = token;
    kind.value = token.kind;
    query.value = token.query;
    open.value = true;
    if (queryChanged) {
      selectedIndex.value = 0;
    }

    if (token.kind === 'slash') {
      await ensureSkillsLoaded();
    } else {
      await ensureFilesLoaded();
    }
    if (seq !== syncSeq) {
      return;
    }

    clampSelectedIndex(queryChanged ? undefined : previousId);
  }

  function completeSlashTokenText(command: string): boolean {
    const token = activeToken.value;
    if (!token || token.kind !== 'slash') {
      return false;
    }
    const insertion = command.startsWith('/') ? command : `/${command}`;
    if (token.token === insertion) {
      return false;
    }
    const result = replaceComposerToken(getDraft(), token, insertion);
    setDraft(result.next);
    restoreCaret(result.caret);
    void syncTypeaheadFromComposer();
    return true;
  }

  function applyRow(row: ComposerTypeaheadRow): void {
    const token = activeToken.value;
    if (!token) {
      return;
    }

    if (token.kind === 'mention' && 'path' in row) {
      if (attachSkill && isComposerSkillFilePath(row.path)) {
        attachSkill(row.path, row.label);
        const result = replaceComposerToken(getDraft(), token, '');
        setDraft(result.next.trimStart());
        closeTypeahead();
        restoreCaret(Math.min(result.caret, getDraft().length));
        return;
      }
      const insertion = mentionInsertionForPath(row.path);
      const result = replaceComposerToken(getDraft(), token, insertion);
      setDraft(result.next);
      closeTypeahead();
      restoreCaret(result.caret);
      return;
    }

    if (token.kind !== 'slash' || !('command' in row)) {
      return;
    }

    if (row.kind === 'mode' && row.mode) {
      composerMode.value = row.mode;
      const result = replaceComposerToken(getDraft(), token, '');
      setDraft(result.next.trimStart());
      closeTypeahead();
      restoreCaret(Math.min(result.caret, getDraft().length));
      return;
    }

    if (row.kind === 'command' && row.command === '/status') {
      composerMode.value = 'ask';
      setDraft(SLASH_STATUS_PROMPT);
      closeTypeahead();
      restoreCaret(SLASH_STATUS_PROMPT.length);
      return;
    }

    if (row.kind === 'command' && row.command === '/help') {
      const catalog = slashCatalog.value;
      setDraft(slashHelpText(catalog));
      closeTypeahead();
      restoreCaret(getDraft().length);
      return;
    }

    if (row.kind === 'skill' && row.skillPath) {
      const result = applySlashSkillToDraft(getDraft(), token, row.skillPath);
      setDraft(result.next);
      attachSkill?.(row.skillPath, row.label || row.skillSlug);
      if (composerMode.value === 'kairo' || composerMode.value === 'ask') {
        composerMode.value = 'agent';
      }
      closeTypeahead();
      restoreCaret(result.caret);
    }
  }

  function applySelectedRow(): boolean {
    const row = rows.value[selectedIndex.value];
    if (!open.value || !row) {
      return false;
    }
    applyRow(row);
    return true;
  }

  function completeSelectedSlashWithTab(): boolean {
    const row = rows.value[selectedIndex.value];
    const token = activeToken.value;
    if (!open.value || !row || !token || token.kind !== 'slash' || !('command' in row)) {
      return applySelectedRow();
    }

    const filteredCommands = slashRows.value.map((item) => item.command);
    const action = resolveSlashTabAction({
      query: token.query,
      selectedCommand: row.command,
      filteredCommands,
    });

    if (action === 'complete-common') {
      const common = longestCommonSlashPrefix(filteredCommands);
      if (common) {
        return completeSlashTokenText(`/${common}`);
      }
    }
    if (action === 'complete-selected') {
      return completeSlashTokenText(row.command);
    }
    return applySelectedRow();
  }

  function handleTypeaheadKeydown(event: KeyboardEvent): boolean {
    if (!open.value) {
      return false;
    }

    if (event.key === 'Escape') {
      event.preventDefault();
      closeTypeahead();
      return true;
    }

    if (rows.value.length === 0) {
      // Keep Enter from submitting while the palette is open but empty/loading.
      if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        return true;
      }
      if (event.key === 'Tab') {
        event.preventDefault();
        return true;
      }
      return false;
    }

    if (event.key === 'ArrowDown') {
      event.preventDefault();
      selectedIndex.value = (selectedIndex.value + 1) % rows.value.length;
      return true;
    }
    if (event.key === 'ArrowUp') {
      event.preventDefault();
      selectedIndex.value =
        (selectedIndex.value - 1 + rows.value.length) % rows.value.length;
      return true;
    }
    if (event.key === 'Tab') {
      event.preventDefault();
      if (kind.value === 'slash') {
        return completeSelectedSlashWithTab();
      }
      return applySelectedRow();
    }
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      return applySelectedRow();
    }
    return false;
  }

  return {
    typeaheadOpen: open,
    typeaheadKind: kind,
    typeaheadRows: rows,
    typeaheadCaption: caption,
    typeaheadEmptyHint: emptyHint,
    typeaheadSelectedIndex: selectedIndex,
    typeaheadLoading: loading,
    closeTypeahead,
    syncTypeaheadFromComposer,
    handleTypeaheadKeydown,
    applyTypeaheadRow: applyRow,
    selectTypeaheadIndex: (index: number) => {
      selectedIndex.value = index;
    },
  };
}

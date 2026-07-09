import type * as Monaco from 'monaco-editor';

import EditorWorker from 'monaco-editor/esm/vs/editor/editor.worker?worker';

import {
  defineMockupMonacoTheme,
  MOCKUP_MONACO_THEME_ID,
  mockupEditorFontOptions,
} from './mockup-workbench-theme';

export interface MonacoEditorOptions {
  value: string;
  language: string;
  readOnly?: boolean;
  minimapEnabled?: boolean;
  onValueChange?: (value: string) => void;
  onCursorChange?: (position: { line: number; column: number }) => void;
  onSelectionChange?: (selection: EditorSelectionSnapshot | null) => void;
  variant?: 'default' | 'mockup';
}

export interface EditorSelectionSnapshot {
  startLine: number;
  startColumn: number;
  endLine: number;
  endColumn: number;
  text: string;
}

export interface MonacoEditorController {
  dispose: () => void;
  setLanguage: (language: string) => void;
  replaceDocument: (value: string, language: string) => void;
  setReadOnly: (readOnly: boolean) => void;
  setMinimapEnabled: (enabled: boolean) => void;
  setValue: (value: string) => void;
  getValue: () => string;
  getSelection: () => EditorSelectionSnapshot | null;
  focus: () => void;
  layout: () => void;
  revealLine: (line: number, column?: number) => void;
  findAndReveal: (searchText: string) => boolean;
}

let monacoPromise: Promise<typeof Monaco> | null = null;

function loadMonaco(): Promise<typeof Monaco> {
  if (!monacoPromise) {
    monacoPromise = import('monaco-editor').then((monaco) => {
      globalThis.MonacoEnvironment = {
        getWorker() {
          return new EditorWorker();
        },
      };
      return monaco;
    });
  }
  return monacoPromise;
}

export async function createMonacoEditor(
  container: HTMLElement,
  options: MonacoEditorOptions,
): Promise<MonacoEditorController> {
  const monaco = await loadMonaco();
  const useMockupTheme = options.variant === 'mockup';
  if (useMockupTheme) {
    defineMockupMonacoTheme(monaco);
  }

  const minimapEnabled = options.minimapEnabled ?? useMockupTheme;
  const model = monaco.editor.createModel(options.value, options.language);
  const editor = monaco.editor.create(container, {
    model,
    theme: useMockupTheme ? MOCKUP_MONACO_THEME_ID : 'vs-dark',
    automaticLayout: true,
    minimap: {
      enabled: minimapEnabled,
      scale: 2,
      showSlider: 'mouseover',
      renderCharacters: false,
      maxColumn: 80,
    },
    stickyScroll: {
      enabled: useMockupTheme,
    },
    bracketPairColorization: {
      enabled: useMockupTheme,
    },
    guides: {
      bracketPairs: useMockupTheme,
      bracketPairsHorizontal: useMockupTheme,
      indentation: true,
      highlightActiveIndentation: useMockupTheme,
    },
    folding: useMockupTheme,
    showFoldingControls: useMockupTheme ? 'mouseover' : 'never',
    smoothScrolling: true,
    cursorBlinking: 'smooth',
    cursorSmoothCaretAnimation: 'on',
    renderLineHighlight: useMockupTheme ? 'all' : 'line',
    renderWhitespace: useMockupTheme ? 'selection' : 'none',
    fontSize: useMockupTheme ? mockupEditorFontOptions.fontSize : 15,
    lineHeight: useMockupTheme ? mockupEditorFontOptions.lineHeight : 22,
    fontFamily: useMockupTheme
      ? mockupEditorFontOptions.fontFamily
      : 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
    fontLigatures: useMockupTheme ? false : undefined,
    scrollBeyondLastLine: false,
    readOnly: options.readOnly ?? false,
    padding: { top: 16, bottom: 16 },
    overviewRulerBorder: false,
    scrollbar: {
      verticalScrollbarSize: 6,
      horizontalScrollbarSize: 6,
      arrowSize: 0,
      useShadows: false,
      verticalHasArrows: false,
      horizontalHasArrows: false,
    },
    matchBrackets: 'always',
    wordWrap: 'off',
  });

  const emitCursor = () => {
    const position = editor.getPosition();
    options.onCursorChange?.({
      line: position?.lineNumber ?? 1,
      column: position?.column ?? 1,
    });
  };

  let activeModel = model;

  const emitSelection = () => {
    if (!options.onSelectionChange) {
      return;
    }
    const selection = editor.getSelection();
    if (!selection || selection.isEmpty()) {
      options.onSelectionChange(null);
      return;
    }
    const text = activeModel.getValueInRange(selection);
    options.onSelectionChange({
      startLine: selection.startLineNumber,
      startColumn: selection.startColumn,
      endLine: selection.endLineNumber,
      endColumn: selection.endColumn,
      text,
    });
  };

  if (options.onValueChange) {
    editor.onDidChangeModelContent(() => {
      options.onValueChange?.(activeModel.getValue());
      emitCursor();
      emitSelection();
    });
  }

  if (options.onCursorChange) {
    editor.onDidChangeCursorPosition(() => {
      emitCursor();
    });
    emitCursor();
  }

  if (options.onSelectionChange) {
    editor.onDidChangeCursorSelection(() => {
      emitSelection();
    });
    emitSelection();
  }

  const scheduleLayout = (): void => {
    requestAnimationFrame(() => {
      editor.layout();
      requestAnimationFrame(() => {
        editor.layout();
      });
    });
  };
  scheduleLayout();

  return {
    dispose() {
      editor.setModel(null);
      editor.dispose();
      activeModel.dispose();
    },
    setLanguage(language: string) {
      monaco.editor.setModelLanguage(activeModel, language);
      scheduleLayout();
    },
    replaceDocument(value: string, language: string) {
      const nextModel = monaco.editor.createModel(value, language);
      editor.setModel(nextModel);
      activeModel.dispose();
      activeModel = nextModel;
      scheduleLayout();
    },
    setReadOnly(readOnly: boolean) {
      editor.updateOptions({ readOnly });
    },
    setMinimapEnabled(enabled: boolean) {
      editor.updateOptions({ minimap: { enabled } });
    },
    setValue(value: string) {
      activeModel.setValue(value);
      emitCursor();
      scheduleLayout();
    },
    getValue() {
      return activeModel.getValue();
    },
    getSelection() {
      const selection = editor.getSelection();
      if (!selection || selection.isEmpty()) {
        return null;
      }
      return {
        startLine: selection.startLineNumber,
        startColumn: selection.startColumn,
        endLine: selection.endLineNumber,
        endColumn: selection.endColumn,
        text: activeModel.getValueInRange(selection),
      };
    },
    focus() {
      editor.focus();
    },
    layout() {
      editor.layout();
    },
    revealLine(line: number, column = 1) {
      const safeLine = Math.max(1, Math.min(line, activeModel.getLineCount()));
      const safeColumn = Math.max(1, column);
      editor.revealLineInCenter(safeLine);
      editor.setPosition({ lineNumber: safeLine, column: safeColumn });
      editor.focus();
    },
    findAndReveal(searchText: string) {
      const needle = searchText.trim();
      if (!needle) {
        return false;
      }
      const matches = activeModel.findMatches(needle, false, false, false, null, false);
      if (!matches.length) {
        return false;
      }
      const match = matches[0];
      editor.revealRangeInCenter(match.range);
      editor.setSelection(match.range);
      editor.focus();
      return true;
    },
  };
}

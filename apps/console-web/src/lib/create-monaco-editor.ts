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
  setReadOnly: (readOnly: boolean) => void;
  setValue: (value: string) => void;
  getValue: () => string;
  getSelection: () => EditorSelectionSnapshot | null;
  focus: () => void;
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

  const model = monaco.editor.createModel(options.value, options.language);
  const editor = monaco.editor.create(container, {
    model,
    theme: useMockupTheme ? MOCKUP_MONACO_THEME_ID : 'vs-dark',
    automaticLayout: true,
    minimap: { enabled: false },
    fontSize: useMockupTheme ? mockupEditorFontOptions.fontSize : 15,
    lineHeight: useMockupTheme ? mockupEditorFontOptions.lineHeight : 22,
    fontFamily: useMockupTheme
      ? mockupEditorFontOptions.fontFamily
      : 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
    fontLigatures: useMockupTheme ? false : undefined,
    scrollBeyondLastLine: false,
    readOnly: options.readOnly ?? false,
    padding: { top: 12, bottom: 12 },
  });

  const emitCursor = () => {
    const position = editor.getPosition();
    options.onCursorChange?.({
      line: position?.lineNumber ?? 1,
      column: position?.column ?? 1,
    });
  };

  const emitSelection = () => {
    if (!options.onSelectionChange) {
      return;
    }
    const selection = editor.getSelection();
    if (!selection || selection.isEmpty()) {
      options.onSelectionChange(null);
      return;
    }
    const text = model.getValueInRange(selection);
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
      options.onValueChange?.(model.getValue());
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

  return {
    dispose() {
      editor.dispose();
      model.dispose();
    },
    setLanguage(language: string) {
      monaco.editor.setModelLanguage(model, language);
    },
    setReadOnly(readOnly: boolean) {
      editor.updateOptions({ readOnly });
    },
    setValue(value: string) {
      model.setValue(value);
      emitCursor();
    },
    getValue() {
      return model.getValue();
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
        text: model.getValueInRange(selection),
      };
    },
    focus() {
      editor.focus();
    },
  };
}

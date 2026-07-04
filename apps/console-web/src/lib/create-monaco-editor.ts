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
  variant?: 'default' | 'mockup';
}

export interface MonacoEditorController {
  dispose: () => void;
  setLanguage: (language: string) => void;
  setReadOnly: (readOnly: boolean) => void;
  setValue: (value: string) => void;
  getValue: () => string;
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

  if (options.onValueChange) {
    editor.onDidChangeModelContent(() => {
      options.onValueChange?.(model.getValue());
    });
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
    },
    getValue() {
      return model.getValue();
    },
  };
}

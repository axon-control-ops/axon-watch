import type * as Monaco from 'monaco-editor';

import EditorWorker from 'monaco-editor/esm/vs/editor/editor.worker?worker';

export interface MonacoEditorOptions {
  value: string;
  language: string;
  readOnly?: boolean;
  onValueChange?: (value: string) => void;
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
  const model = monaco.editor.createModel(options.value, options.language);
  const editor = monaco.editor.create(container, {
    model,
    theme: 'vs-dark',
    automaticLayout: true,
    minimap: { enabled: false },
    fontSize: 15,
    lineHeight: 22,
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

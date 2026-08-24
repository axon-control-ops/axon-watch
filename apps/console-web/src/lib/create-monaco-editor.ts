import type * as Monaco from 'monaco-editor';

import EditorWorker from 'monaco-editor/esm/vs/editor/editor.worker.js?worker';
import CssWorker from 'monaco-editor/esm/vs/language/css/css.worker.js?worker';
import HtmlWorker from 'monaco-editor/esm/vs/language/html/html.worker.js?worker';
import JsonWorker from 'monaco-editor/esm/vs/language/json/json.worker.js?worker';
import TsWorker from 'monaco-editor/esm/vs/language/typescript/ts.worker.js?worker';

import {
  defineMockupMonacoTheme,
  MOCKUP_MONACO_THEME_ID,
  mockupEditorFontOptions,
} from './mockup-workbench-theme';
import {
  CURSOR_MONACO_THEME_ID,
  cursorEditorFontOptions,
  cursorMinimapOptions,
  defineCursorMonacoTheme,
  mockupMinimapOptions,
} from './cursor-editor-theme';
import { registerCsvLanguage } from './register-csv-language';

export interface MonacoEditorOptions {
  value: string;
  language: string;
  readOnly?: boolean;
  minimapEnabled?: boolean;
  onValueChange?: (value: string) => void;
  onCursorChange?: (position: { line: number; column: number }) => void;
  onSelectionChange?: (selection: EditorSelectionSnapshot | null) => void;
  variant?: 'default' | 'mockup';
  themeProfile?: 'mockup' | 'cursor';
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

type MonacoTsLanguageApi = {
  typescriptDefaults: {
    setDiagnosticsOptions: (options: {
      noSemanticValidation?: boolean;
      noSyntaxValidation?: boolean;
      noSuggestionDiagnostics?: boolean;
    }) => void;
    setEagerModelSync: (value: boolean) => void;
    setCompilerOptions: (options: Record<string, unknown>) => void;
    getCompilerOptions: () => Record<string, unknown>;
  };
  javascriptDefaults: {
    setDiagnosticsOptions: (options: {
      noSemanticValidation?: boolean;
      noSyntaxValidation?: boolean;
      noSuggestionDiagnostics?: boolean;
    }) => void;
    setEagerModelSync: (value: boolean) => void;
  };
  ScriptTarget: { ESNext: number };
  ModuleKind: { ESNext: number };
  ModuleResolutionKind: { NodeJs: number };
};

function configureLanguageDefaults(monaco: typeof Monaco): void {
  // Monaco 0.55 types mark languages.typescript as deprecated; runtime API is still present.
  const tsApi = (monaco.languages as unknown as { typescript?: MonacoTsLanguageApi }).typescript;
  if (tsApi?.typescriptDefaults && tsApi.javascriptDefaults) {
    // Operator console is a viewer/editor shell, not a full language service host.
    // Keep syntax highlighting; skip semantic work that freezes the tab on large TS files.
    const diagnosticOptions = {
      noSemanticValidation: true,
      noSyntaxValidation: false,
      noSuggestionDiagnostics: true,
    };
    tsApi.typescriptDefaults.setDiagnosticsOptions(diagnosticOptions);
    tsApi.javascriptDefaults.setDiagnosticsOptions(diagnosticOptions);
    tsApi.typescriptDefaults.setEagerModelSync(true);
    tsApi.javascriptDefaults.setEagerModelSync(true);
    tsApi.typescriptDefaults.setCompilerOptions({
      ...tsApi.typescriptDefaults.getCompilerOptions(),
      allowNonTsExtensions: true,
      allowJs: true,
      checkJs: false,
      noLib: true,
      target: tsApi.ScriptTarget.ESNext,
      module: tsApi.ModuleKind.ESNext,
      moduleResolution: tsApi.ModuleResolutionKind.NodeJs,
    });
  }

  // Vue SFCs are opened as html for highlighting; turn off HTML schema validation noise.
  const htmlDefaults = (
    monaco.languages as unknown as {
      html?: { htmlDefaults?: { setOptions: (options: Record<string, unknown>) => void } };
    }
  ).html?.htmlDefaults;
  htmlDefaults?.setOptions({
    validate: false,
  });
}

function installMonacoEnvironment(): void {
  globalThis.MonacoEnvironment = {
    getWorker(_workerId: string, label: string) {
      switch (label) {
        case 'json':
          return new JsonWorker();
        case 'css':
        case 'scss':
        case 'less':
          return new CssWorker();
        case 'html':
        case 'handlebars':
        case 'razor':
          return new HtmlWorker();
        case 'typescript':
        case 'javascript':
          return new TsWorker();
        default:
          return new EditorWorker();
      }
    },
  };
}

function loadMonaco(): Promise<typeof Monaco> {
  if (!monacoPromise) {
    monacoPromise = import('monaco-editor').then((monaco) => {
      installMonacoEnvironment();
      configureLanguageDefaults(monaco);
      registerCsvLanguage(monaco);
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
  const useCursorTheme = useMockupTheme && options.themeProfile === 'cursor';
  if (useCursorTheme) {
    defineCursorMonacoTheme(monaco);
  } else if (useMockupTheme) {
    defineMockupMonacoTheme(monaco);
  }

  const minimapEnabled = options.minimapEnabled ?? useMockupTheme;
  const fontOptions = useCursorTheme ? cursorEditorFontOptions : mockupEditorFontOptions;
  const minimapLayout = useCursorTheme ? cursorMinimapOptions : mockupMinimapOptions;
  const model = monaco.editor.createModel(options.value, options.language);
  const editor = monaco.editor.create(container, {
    model,
    theme: useCursorTheme ? CURSOR_MONACO_THEME_ID : useMockupTheme ? MOCKUP_MONACO_THEME_ID : 'vs-dark',
    automaticLayout: true,
    // Monaco 0.55 defaults editContext to true; with our shell CSS it can leave
    // a blank pane while the model still has content (status bar line count OK).
    editContext: false,
    // Inlay hints / code actions hit the language worker; keep them off in this shell.
    inlayHints: { enabled: 'off' },
    quickSuggestions: false,
    suggestOnTriggerCharacters: false,
    parameterHints: { enabled: false },
    hover: { enabled: true },
    minimap: {
      enabled: minimapEnabled,
      ...minimapLayout,
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
    fontSize: useMockupTheme ? fontOptions.fontSize : 15,
    lineHeight: useMockupTheme ? fontOptions.lineHeight : 22,
    fontFamily: useMockupTheme
      ? fontOptions.fontFamily
      : 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
    fontLigatures: useMockupTheme ? fontOptions.fontLigatures : undefined,
    scrollBeyondLastLine: false,
    readOnly: options.readOnly ?? false,
    padding: useCursorTheme ? { top: 8, bottom: 8 } : { top: 16, bottom: 16 },
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
      editor.updateOptions({ minimap: { enabled, ...minimapLayout } });
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

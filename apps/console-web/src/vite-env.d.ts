/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_DEV_SEAMS?: string;
  readonly VITE_CONTROL_PLANE_BASE_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}

declare module 'monaco-editor/esm/vs/editor/editor.worker.js?worker' {
  const WorkerFactory: new () => Worker;
  export default WorkerFactory;
}

declare module 'monaco-editor/esm/vs/language/json/json.worker.js?worker' {
  const WorkerFactory: new () => Worker;
  export default WorkerFactory;
}

declare module 'monaco-editor/esm/vs/language/css/css.worker.js?worker' {
  const WorkerFactory: new () => Worker;
  export default WorkerFactory;
}

declare module 'monaco-editor/esm/vs/language/html/html.worker.js?worker' {
  const WorkerFactory: new () => Worker;
  export default WorkerFactory;
}

declare module 'monaco-editor/esm/vs/language/typescript/ts.worker.js?worker' {
  const WorkerFactory: new () => Worker;
  export default WorkerFactory;
}

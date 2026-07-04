/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_DEV_SEAMS?: string;
  readonly VITE_CONTROL_PLANE_BASE_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}

declare module 'monaco-editor/esm/vs/editor/editor.worker?worker' {
  const WorkerFactory: new () => Worker;
  export default WorkerFactory;
}

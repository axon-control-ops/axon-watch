declare namespace NodeJS {
  interface ProcessEnv {
    EXPO_PUBLIC_AXON_CONTROL_PLANE_URL?: string;
  }
}

declare const process: {
  env: NodeJS.ProcessEnv;
};

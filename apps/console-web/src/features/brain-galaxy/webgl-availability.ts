export type WebGlProbeResult = {
  ok: boolean;
  webgl2: boolean;
  webgl: boolean;
  experimental: boolean;
  caveatBlocked: boolean;
  error: string | null;
  renderer: string | null;
};

const SOFT_OPTS: WebGLContextAttributes = {
  alpha: true,
  failIfMajorPerformanceCaveat: false,
};

const STRICT_OPTS: WebGLContextAttributes = {
  alpha: true,
  failIfMajorPerformanceCaveat: true,
};

function readRenderer(gl: WebGLRenderingContext | WebGL2RenderingContext): string | null {
  try {
    const info = gl.getExtension('WEBGL_debug_renderer_info');
    if (!info) {
      return String(gl.getParameter(gl.RENDERER) ?? '');
    }
    return String(gl.getParameter(info.UNMASKED_RENDERER_WEBGL) ?? '');
  } catch {
    return null;
  }
}

function lose(gl: WebGLRenderingContext | WebGL2RenderingContext | null): void {
  try {
    gl?.getExtension('WEBGL_lose_context')?.loseContext();
  } catch {
    // ignore
  }
}

function tryContext(
  canvas: HTMLCanvasElement,
  opts: WebGLContextAttributes,
): {
  gl: WebGLRenderingContext | WebGL2RenderingContext | null;
  webgl2: boolean;
  webgl: boolean;
  experimental: boolean;
} {
  const gl2 = canvas.getContext('webgl2', opts);
  if (gl2) {
    return { gl: gl2, webgl2: true, webgl: false, experimental: false };
  }
  const gl = canvas.getContext('webgl', opts);
  if (gl) {
    return { gl, webgl2: false, webgl: true, experimental: false };
  }
  const experimental = canvas.getContext('experimental-webgl', opts) as WebGLRenderingContext | null;
  if (experimental) {
    return { gl: experimental, webgl2: false, webgl: false, experimental: true };
  }
  return { gl: null, webgl2: false, webgl: false, experimental: false };
}

/**
 * Probe WebGL with software-fallback allowed. Strict browser probes often
 * return null when the GPU path is blocklisted (common on Linux/VM).
 */
export function probeWebGlAvailability(): WebGlProbeResult {
  const result: WebGlProbeResult = {
    ok: false,
    webgl2: false,
    webgl: false,
    experimental: false,
    caveatBlocked: false,
    error: null,
    renderer: null,
  };
  if (typeof document === 'undefined') {
    result.error = 'no-document';
    return result;
  }
  try {
    const strictCanvas = document.createElement('canvas');
    const softCanvas = document.createElement('canvas');
    const strict = tryContext(strictCanvas, STRICT_OPTS);
    lose(strict.gl);
    const soft = tryContext(softCanvas, SOFT_OPTS);
    result.webgl2 = soft.webgl2;
    result.webgl = soft.webgl;
    result.experimental = soft.experimental;
    result.caveatBlocked = !strict.gl && Boolean(soft.gl);
    if (!soft.gl) {
      result.error = 'getContext returned null';
      return result;
    }
    result.ok = true;
    result.renderer = readRenderer(soft.gl);
    lose(soft.gl);
    return result;
  } catch (error) {
    result.error = error instanceof Error ? error.message : String(error);
    return result;
  }
}

/** Azure REST short-audio accepts ogg/opus or wav — not WebM. */
const CLOUD_UPLOAD_MIME_CANDIDATES = ['audio/ogg;codecs=opus', 'audio/wav'] as const;
const TARGET_SAMPLE_RATE = 16000;

export type CloudCaptureAutoStopOptions = {
  /** Minimum capture time before silence can end the clip. */
  minMs?: number;
  /** Quiet stretch after speech that ends the clip. */
  silenceMs?: number;
  /** Hard cap so ambient cloud capture cannot run forever. */
  maxMs?: number;
  onAutoStop: () => void;
};

export function isCloudUploadMimeType(mimeType: string): boolean {
  const lowered = mimeType.trim().toLowerCase();
  return lowered.includes('audio/ogg') || lowered.includes('audio/wav');
}

export function preferredCloudRecorderMimeType(): string {
  if (typeof MediaRecorder === 'undefined') {
    return '';
  }
  for (const mime of CLOUD_UPLOAD_MIME_CANDIDATES) {
    if (MediaRecorder.isTypeSupported(mime)) {
      return mime;
    }
  }
  return '';
}

function audioContextConstructor(): typeof AudioContext | null {
  if (typeof window === 'undefined') {
    return null;
  }
  return (
    window.AudioContext ||
    (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext ||
    null
  );
}

/** Cloud capture works whenever we can getUserMedia + AudioContext (PCM WAV fallback). */
export function isCloudAudioCaptureSupported(): boolean {
  return (
    typeof navigator !== 'undefined' &&
    Boolean(navigator.mediaDevices?.getUserMedia) &&
    audioContextConstructor() !== null
  );
}

function rmsFromAnalyser(analyser: AnalyserNode, buffer: Uint8Array): number {
  analyser.getByteTimeDomainData(buffer);
  let sum = 0;
  for (let i = 0; i < buffer.length; i += 1) {
    const centered = (buffer[i] ?? 128) - 128;
    sum += centered * centered;
  }
  return Math.sqrt(sum / Math.max(1, buffer.length)) / 128;
}

/** Encode mono float samples as 16-bit PCM WAV (Azure-friendly). */
export function encodePcmWav(samples: Float32Array, sampleRate: number): Blob {
  const dataLength = samples.length * 2;
  const buffer = new ArrayBuffer(44 + dataLength);
  const view = new DataView(buffer);
  const writeString = (offset: number, value: string) => {
    for (let i = 0; i < value.length; i += 1) {
      view.setUint8(offset + i, value.charCodeAt(i));
    }
  };
  writeString(0, 'RIFF');
  view.setUint32(4, 36 + dataLength, true);
  writeString(8, 'WAVE');
  writeString(12, 'fmt ');
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, 1, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * 2, true);
  view.setUint16(32, 2, true);
  view.setUint16(34, 16, true);
  writeString(36, 'data');
  view.setUint32(40, dataLength, true);
  let offset = 44;
  for (let i = 0; i < samples.length; i += 1) {
    const clamped = Math.max(-1, Math.min(1, samples[i] ?? 0));
    view.setInt16(offset, clamped < 0 ? clamped * 0x8000 : clamped * 0x7fff, true);
    offset += 2;
  }
  return new Blob([buffer], { type: 'audio/wav' });
}

function downsampleToRate(
  input: Float32Array,
  inputRate: number,
  outputRate: number,
): Float32Array {
  if (inputRate === outputRate) {
    return input;
  }
  if (inputRate <= 0 || outputRate <= 0) {
    return input;
  }
  const ratio = inputRate / outputRate;
  const newLength = Math.max(1, Math.round(input.length / ratio));
  const output = new Float32Array(newLength);
  for (let i = 0; i < newLength; i += 1) {
    const start = Math.floor(i * ratio);
    const end = Math.min(input.length, Math.floor((i + 1) * ratio));
    let sum = 0;
    let count = 0;
    for (let j = start; j < end; j += 1) {
      sum += input[j] ?? 0;
      count += 1;
    }
    output[i] = count > 0 ? sum / count : (input[start] ?? 0);
  }
  return output;
}

export class CloudAudioCaptureSession {
  private mediaStream: MediaStream | null = null;

  private recorder: MediaRecorder | null = null;

  private chunks: BlobPart[] = [];

  private mimeType = '';

  private audioContext: AudioContext | null = null;

  private analyser: AnalyserNode | null = null;

  private processor: ScriptProcessorNode | null = null;

  private sourceNode: MediaStreamAudioSourceNode | null = null;

  private pcmChunks: Float32Array[] = [];

  private pcmSampleCount = 0;

  private usePcm = false;

  private monitorTimer: number | null = null;

  private autoStop: CloudCaptureAutoStopOptions | null = null;

  private startedAt = 0;

  private heardSpeech = false;

  private quietSince: number | null = null;

  /** Diagnostics from the most recent stop() — sample count for PCM path. */
  lastStopStats: {
    pcmSamples: number;
    mimeType: string;
    blobSize: number;
    heardSpeech: boolean;
    elapsedMs: number;
  } | null = null;

  async start(options?: { autoStop?: CloudCaptureAutoStopOptions }): Promise<boolean> {
    if (!isCloudAudioCaptureSupported()) {
      return false;
    }
    this.stopImmediate();
    this.autoStop = options?.autoStop ?? null;
    try {
      this.mediaStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });
    } catch {
      return false;
    }

    const mediaRecorderMime = preferredCloudRecorderMimeType();
    this.chunks = [];
    this.pcmChunks = [];
    this.pcmSampleCount = 0;
    this.startedAt = Date.now();
    this.heardSpeech = false;
    this.quietSince = null;

    // Prefer MediaRecorder only when it can emit Azure-accepted containers.
    // Chromium/WebKit often only offer webm — fall back to PCM WAV instead.
    if (mediaRecorderMime) {
      this.usePcm = false;
      this.mimeType = mediaRecorderMime;
      try {
        this.recorder = new MediaRecorder(this.mediaStream, { mimeType: this.mimeType });
      } catch {
        this.recorder = null;
      }
      if (this.recorder) {
        this.recorder.ondataavailable = (event: BlobEvent) => {
          if (event.data.size > 0) {
            this.chunks.push(event.data);
          }
        };
        this.recorder.start(250);
        if (this.autoStop) {
          this.beginSilenceMonitor();
        }
        return true;
      }
    }

    return await this.startPcmCapture();
  }

  private async startPcmCapture(): Promise<boolean> {
    const Ctx = audioContextConstructor();
    if (!Ctx || !this.mediaStream) {
      this.releaseStream();
      return false;
    }
    try {
      this.usePcm = true;
      this.mimeType = 'audio/wav';
      try {
        this.audioContext = new Ctx({ sampleRate: TARGET_SAMPLE_RATE });
      } catch {
        this.audioContext = new Ctx();
      }
      await this.audioContext.resume();
      if (this.audioContext.state !== 'running') {
        this.stopImmediate();
        return false;
      }
      this.sourceNode = this.audioContext.createMediaStreamSource(this.mediaStream);
      this.analyser = this.audioContext.createAnalyser();
      this.analyser.fftSize = 2048;
      // ScriptProcessor is deprecated but widely available; keeps capture self-contained.
      this.processor = this.audioContext.createScriptProcessor(4096, 1, 1);
      this.processor.onaudioprocess = (event: AudioProcessingEvent) => {
        const input = event.inputBuffer.getChannelData(0);
        this.pcmChunks.push(new Float32Array(input));
        this.pcmSampleCount += input.length;
      };
      const mute = this.audioContext.createGain();
      mute.gain.value = 0;
      this.sourceNode.connect(this.analyser);
      this.sourceNode.connect(this.processor);
      this.processor.connect(mute);
      mute.connect(this.audioContext.destination);
      if (this.autoStop) {
        this.beginSilenceMonitor(true);
      }
      return true;
    } catch {
      this.stopImmediate();
      return false;
    }
  }

  private beginSilenceMonitor(reuseGraph = false): void {
    if (!this.mediaStream || !this.autoStop) {
      return;
    }
    try {
      if (!reuseGraph) {
        const Ctx = audioContextConstructor();
        if (!Ctx) {
          return;
        }
        this.audioContext = new Ctx();
        const source = this.audioContext.createMediaStreamSource(this.mediaStream);
        this.analyser = this.audioContext.createAnalyser();
        this.analyser.fftSize = 2048;
        source.connect(this.analyser);
      }
      if (!this.analyser) {
        return;
      }
      const buffer = new Uint8Array(this.analyser.fftSize);
      const minMs = this.autoStop.minMs ?? 700;
      const silenceMs = this.autoStop.silenceMs ?? 850;
      const maxMs = this.autoStop.maxMs ?? 12000;
      const speechThreshold = 0.028;
      const quietThreshold = 0.014;

      this.monitorTimer = window.setInterval(() => {
        if (!this.analyser || !this.autoStop) {
          return;
        }
        const elapsed = Date.now() - this.startedAt;
        const level = rmsFromAnalyser(this.analyser, buffer);
        if (level >= speechThreshold) {
          this.heardSpeech = true;
          this.quietSince = null;
        } else if (this.heardSpeech && level <= quietThreshold) {
          if (this.quietSince === null) {
            this.quietSince = Date.now();
          }
        } else if (!this.heardSpeech) {
          this.quietSince = null;
        }

        const quietFor =
          this.quietSince !== null ? Date.now() - this.quietSince : 0;
        const shouldStop =
          elapsed >= maxMs ||
          (this.heardSpeech && elapsed >= minMs && quietFor >= silenceMs);
        if (shouldStop) {
          const cb = this.autoStop.onAutoStop;
          this.clearMonitor(false);
          cb();
        }
      }, 100);
    } catch {
      // Monitor is best-effort; manual/max stop still works via stop().
    }
  }

  private clearMonitor(closeContext: boolean): void {
    if (this.monitorTimer !== null) {
      window.clearInterval(this.monitorTimer);
      this.monitorTimer = null;
    }
    this.autoStop = null;
    if (closeContext && this.audioContext && !this.usePcm) {
      void this.audioContext.close().catch(() => undefined);
      this.audioContext = null;
      this.analyser = null;
    }
  }

  async stop(): Promise<Blob | null> {
    const heardSpeech = this.heardSpeech;
    const elapsedMs = Date.now() - this.startedAt;
    this.clearMonitor(!this.usePcm);
    if (this.usePcm) {
      const blob = this.stopPcmCapture();
      this.lastStopStats = {
        pcmSamples: blob ? Math.floor((blob.size - 44) / 2) : 0,
        mimeType: this.mimeType || 'audio/wav',
        blobSize: blob?.size ?? 0,
        heardSpeech,
        elapsedMs,
      };
      return blob;
    }
    const recorder = this.recorder;
    if (!recorder || recorder.state === 'inactive') {
      this.releaseStream();
      this.lastStopStats = {
        pcmSamples: 0,
        mimeType: this.mimeType,
        blobSize: 0,
        heardSpeech,
        elapsedMs,
      };
      return null;
    }
    const blob = await new Promise<Blob | null>((resolve) => {
      recorder.onstop = () => {
        if (!this.chunks.length) {
          resolve(null);
          return;
        }
        resolve(new Blob(this.chunks, { type: this.mimeType || 'audio/ogg' }));
      };
      try {
        recorder.stop();
      } catch {
        resolve(null);
      }
    });
    this.recorder = null;
    this.releaseStream();
    this.lastStopStats = {
      pcmSamples: 0,
      mimeType: this.mimeType || 'audio/ogg',
      blobSize: blob?.size ?? 0,
      heardSpeech,
      elapsedMs,
    };
    return blob;
  }

  private stopPcmCapture(): Blob | null {
    if (this.processor) {
      this.processor.onaudioprocess = null;
      try {
        this.processor.disconnect();
      } catch {
        // ignore
      }
      this.processor = null;
    }
    if (this.sourceNode) {
      try {
        this.sourceNode.disconnect();
      } catch {
        // ignore
      }
      this.sourceNode = null;
    }
    const inputRate = this.audioContext?.sampleRate ?? TARGET_SAMPLE_RATE;
    if (this.audioContext) {
      void this.audioContext.close().catch(() => undefined);
      this.audioContext = null;
    }
    this.analyser = null;
    this.releaseStream();

    if (!this.pcmSampleCount) {
      this.pcmChunks = [];
      return null;
    }
    const merged = new Float32Array(this.pcmSampleCount);
    let offset = 0;
    for (const chunk of this.pcmChunks) {
      merged.set(chunk, offset);
      offset += chunk.length;
    }
    this.pcmChunks = [];
    this.pcmSampleCount = 0;
    const resampled = downsampleToRate(merged, inputRate, TARGET_SAMPLE_RATE);
    return encodePcmWav(resampled, TARGET_SAMPLE_RATE);
  }

  stopImmediate(): void {
    this.clearMonitor(true);
    if (this.processor) {
      this.processor.onaudioprocess = null;
      try {
        this.processor.disconnect();
      } catch {
        // ignore
      }
      this.processor = null;
    }
    if (this.sourceNode) {
      try {
        this.sourceNode.disconnect();
      } catch {
        // ignore
      }
      this.sourceNode = null;
    }
    if (this.recorder && this.recorder.state !== 'inactive') {
      try {
        this.recorder.ondataavailable = null;
        this.recorder.onstop = null;
        this.recorder.stop();
      } catch {
        // ignore
      }
    }
    this.recorder = null;
    this.chunks = [];
    this.pcmChunks = [];
    this.pcmSampleCount = 0;
    this.usePcm = false;
    if (this.audioContext) {
      void this.audioContext.close().catch(() => undefined);
      this.audioContext = null;
    }
    this.analyser = null;
    this.releaseStream();
  }

  private releaseStream(): void {
    if (this.mediaStream) {
      for (const track of this.mediaStream.getTracks()) {
        track.stop();
      }
      this.mediaStream = null;
    }
  }
}

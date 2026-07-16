/** Azure REST short-audio accepts ogg/opus or wav — not WebM. */
const CLOUD_UPLOAD_MIME_CANDIDATES = ['audio/ogg;codecs=opus', 'audio/wav'] as const;

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

export function isCloudAudioCaptureSupported(): boolean {
  return (
    typeof navigator !== 'undefined' &&
    Boolean(navigator.mediaDevices?.getUserMedia) &&
    preferredCloudRecorderMimeType() !== ''
  );
}

export class CloudAudioCaptureSession {
  private mediaStream: MediaStream | null = null;

  private recorder: MediaRecorder | null = null;

  private chunks: BlobPart[] = [];

  private mimeType = '';

  async start(): Promise<boolean> {
    if (!isCloudAudioCaptureSupported()) {
      return false;
    }
    this.stop();
    this.mimeType = preferredCloudRecorderMimeType();
    try {
      this.mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch {
      return false;
    }
    try {
      this.recorder = new MediaRecorder(this.mediaStream, { mimeType: this.mimeType });
    } catch {
      this.releaseStream();
      return false;
    }
    this.chunks = [];
    this.recorder.ondataavailable = (event: BlobEvent) => {
      if (event.data.size > 0) {
        this.chunks.push(event.data);
      }
    };
    this.recorder.start();
    return true;
  }

  async stop(): Promise<Blob | null> {
    const recorder = this.recorder;
    if (!recorder || recorder.state === 'inactive') {
      this.releaseStream();
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
    this.chunks = [];
    this.releaseStream();
    return blob;
  }

  stopImmediate(): void {
    const recorder = this.recorder;
    if (recorder && recorder.state !== 'inactive') {
      try {
        recorder.stop();
      } catch {
        // ignore
      }
    }
    this.recorder = null;
    this.chunks = [];
    this.releaseStream();
  }

  private releaseStream(): void {
    if (!this.mediaStream) {
      return;
    }
    for (const track of this.mediaStream.getTracks()) {
      track.stop();
    }
    this.mediaStream = null;
  }
}

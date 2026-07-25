import { describe, expect, it } from 'vitest';

import { encodePcmWav, isCloudUploadMimeType } from './cloud-audio-capture';

describe('cloud-audio-capture', () => {
  it('accepts only ogg and wav upload mime types for Azure', () => {
    expect(isCloudUploadMimeType('audio/ogg;codecs=opus')).toBe(true);
    expect(isCloudUploadMimeType('audio/wav')).toBe(true);
    expect(isCloudUploadMimeType('audio/webm;codecs=opus')).toBe(false);
    expect(isCloudUploadMimeType('audio/webm')).toBe(false);
  });

  it('encodes pcm samples as a wav blob', async () => {
    const samples = new Float32Array([0, 0.5, -0.5, 1, -1]);
    const blob = encodePcmWav(samples, 16000);
    expect(blob.type).toBe('audio/wav');
    expect(blob.size).toBe(44 + samples.length * 2);
    const bytes = new Uint8Array(await blob.arrayBuffer());
    expect(String.fromCharCode(...bytes.slice(0, 4))).toBe('RIFF');
    expect(String.fromCharCode(...bytes.slice(8, 12))).toBe('WAVE');
  });
});

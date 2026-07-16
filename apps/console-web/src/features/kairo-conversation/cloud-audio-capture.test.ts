import { describe, expect, it } from 'vitest';

import { isCloudUploadMimeType } from './cloud-audio-capture';

describe('cloud-audio-capture', () => {
  it('accepts only ogg and wav upload mime types for Azure', () => {
    expect(isCloudUploadMimeType('audio/ogg;codecs=opus')).toBe(true);
    expect(isCloudUploadMimeType('audio/wav')).toBe(true);
    expect(isCloudUploadMimeType('audio/webm;codecs=opus')).toBe(false);
    expect(isCloudUploadMimeType('audio/webm')).toBe(false);
  });
});

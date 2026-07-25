import { beforeEach, describe, expect, it } from 'vitest';

import {
  detectVoiceInterruptPhrase,
  evaluateVoiceTranscript,
  formatVoiceGateFeedback,
  stripKairoWakeWordPrefix,
} from './kairo-voice-gate';
import {
  clearKairoVoiceFollowupWindow,
  openKairoVoiceFollowupWindow,
} from './kairo-voice-followup-window';

describe('kairo voice gate', () => {
  beforeEach(() => {
    clearKairoVoiceFollowupWindow();
  });
  it('accepts manual transcripts without wake word', () => {
    expect(evaluateVoiceTranscript('check health', 'manual').accept).toBe(true);
  });

  it('rejects ambient hands-free chatter without wake word', () => {
    const result = evaluateVoiceTranscript('did you see the game last night', 'hands_free');
    expect(result.accept).toBe(false);
    expect(result.reason).toBe('no_wake_word');
  });

  it('explains wake-word rejection to the operator', () => {
    expect(formatVoiceGateFeedback('no_wake_word', 'hello there', false)).toContain('VAXON');
    expect(formatVoiceGateFeedback('ambient_short', '', false)).toContain('VAXON');
    expect(formatVoiceGateFeedback('wake_word', 'hello', true)).toBeNull();
  });

  it('accepts hands-free when VAXON is addressed', () => {
    const result = evaluateVoiceTranscript('hey vaxon what is dash pro doing', 'hands_free');
    expect(result.accept).toBe(true);
    expect(result.submitContent).toContain('DashPro');
  });

  it('accepts legacy cairo wake alias in hands-free', () => {
    const result = evaluateVoiceTranscript('hey cairo what is dash pro doing', 'hands_free');
    expect(result.accept).toBe(true);
  });

  it('accepts direct operator commands in hands-free', () => {
    expect(evaluateVoiceTranscript('git status', 'hands_free').accept).toBe(true);
  });

  it('accepts follow-ups during the post-reply window without wake word', () => {
    openKairoVoiceFollowupWindow();
    const result = evaluateVoiceTranscript('and what about DashPro', 'hands_free');
    expect(result.accept).toBe(true);
    expect(result.reason).toBe('follow_up_window');
    expect(result.submitContent).toContain('DashPro');
  });

  it('still rejects ambient chatter during the follow-up window', () => {
    openKairoVoiceFollowupWindow();
    const result = evaluateVoiceTranscript('did you see the game last night', 'hands_free');
    expect(result.accept).toBe(false);
    expect(result.reason).toBe('follow_up_not_recognized');
  });

  it('detects voice interrupt phrases', () => {
    expect(detectVoiceInterruptPhrase('stop')).toBe(true);
    expect(detectVoiceInterruptPhrase('kairo stop talking')).toBe(true);
    expect(detectVoiceInterruptPhrase('nice weather')).toBe(false);
  });

  it('barge-in accepts wake word commands and interrupts first', () => {
    const result = evaluateVoiceTranscript('kairo check health', 'barge_in');
    expect(result.accept).toBe(true);
    expect(result.shouldInterrupt).toBe(true);
    expect(result.submitContent).toBe('check health');
  });

  it('strips wake word prefix', () => {
    expect(stripKairoWakeWordPrefix('VAXON, open attention')).toBe('open attention');
  });

  it.each([
    'vixen',
    'vicksen',
    'vikson',
    'vicsen',
    'wixen',
    'wax on',
    'vax on',
    'backs on',
    'back son',
  ])(
    'accepts hands-free STT mishear %s as wake word',
    (mishear) => {
      const result = evaluateVoiceTranscript(`hey ${mishear} check health`, 'hands_free');
      expect(result.accept).toBe(true);
      expect(result.submitContent).toContain('check health');
    },
  );
});

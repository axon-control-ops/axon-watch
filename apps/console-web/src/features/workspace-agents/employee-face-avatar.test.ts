import { describe, expect, it } from 'vitest';

import {
  buildEmployeeFaceAvatarUrl,
  buildFaceAvatarUrl,
  buildVaxonFaceAvatarUrl,
} from './employee-face-avatar';

describe('employee-face-avatar', () => {
  it('builds stable SVG data URLs for the same seed', () => {
    const a = buildEmployeeFaceAvatarUrl('emp_dana:lead:Dana');
    const b = buildEmployeeFaceAvatarUrl('emp_dana:lead:Dana');
    expect(a).toBe(b);
    expect(a.startsWith('data:image/svg+xml')).toBe(true);
  });

  it('varies faces across different employees', () => {
    const dana = buildEmployeeFaceAvatarUrl('emp_dana');
    const cass = buildEmployeeFaceAvatarUrl('emp_cass');
    expect(dana).not.toBe(cass);
  });

  it('builds a distinct VAXON face', () => {
    const vaxon = buildVaxonFaceAvatarUrl();
    expect(buildFaceAvatarUrl('vaxon', 'vaxon')).toBe(vaxon);
    expect(vaxon).not.toBe(buildEmployeeFaceAvatarUrl('vaxon'));
  });
});

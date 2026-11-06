import { describe, it, expect } from 'vitest';
import { formatEngineCount } from './engine-count';

/**
 * The count lands in a 56px ring and a narrow sidebar row, so it has to stay
 * short without lying: exact while a reader can still compare digits, past
 * that abbreviated rather than overflowing the circle it sits in.
 */
describe('formatEngineCount', () => {
  it('shows counts up to four digits exactly', () => {
    expect(formatEngineCount(0)).toBe('0');
    expect(formatEngineCount(84)).toBe('84');
    expect(formatEngineCount(9_914)).toBe('9,914');
    expect(formatEngineCount(9_999)).toBe('9,999');
  });

  it('abbreviates counts too large to fit the ring', () => {
    expect(formatEngineCount(10_000)).toBe('10K');
    expect(formatEngineCount(12_345)).toBe('12.3K');
    expect(formatEngineCount(1_200_000)).toBe('1.2M');
  });

  it('pins the locale so the same run renders the same string everywhere', () => {
    // `toLocaleString()` without a locale would render `9.914` on a de-DE
    // machine, and the ring would show a number that reads as a decimal.
    expect(formatEngineCount(9_914)).toBe('9,914');
  });
});

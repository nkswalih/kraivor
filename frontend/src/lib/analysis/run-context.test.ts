import { describe, it, expect } from 'vitest';
import {
  CLONE_COMPLETE_PCT,
  PARSE_COMPLETE_PCT,
  PARSE_PROGRESSING_PCT,
  measure,
} from './run-context';

/**
 * `run-context.ts` encodes when each pipeline stage publishes what. The numbers
 * come from `pipeline.py`'s stage progress weights: clone writes the file count,
 * line count and language mix at 15%, parse starts writing entity counts at 25%
 * and finishes at 60%.
 *
 * These tests pin the arithmetic, not the numbers themselves -- if a stage weight
 * changes upstream, the constants change and this file's expectations follow.
 * What must not drift is the meaning: pending is absence, ready is measurement,
 * and settled says whether the producing stage has finished.
 */

describe('stage thresholds', () => {
  it('orders the stages the way the pipeline runs them', () => {
    expect(CLONE_COMPLETE_PCT).toBeLessThan(PARSE_PROGRESSING_PCT);
    expect(PARSE_PROGRESSING_PCT).toBeLessThan(PARSE_COMPLETE_PCT);
  });

  it('puts all three inside the parse stage, which spans 15 to 60', () => {
    // Not a coincidence worth asserting, but worth knowing: none of these may
    // exceed the point at which parse finishes, or a count would be marked
    // settled before the stage producing it is done.
    expect(PARSE_COMPLETE_PCT).toBeLessThanOrEqual(60);
  });
});

describe('measure marks absence as pending', () => {
  it.each([
    ['null', null],
    ['undefined', undefined],
  ])('a %s value is pending', (_label, value) => {
    expect(measure(value, 50, PARSE_PROGRESSING_PCT)).toEqual({
      state: 'pending',
      progressPct: 50,
      availableFromPct: PARSE_PROGRESSING_PCT,
    });
  });

  it('never reports an absent value as zero', () => {
    // `?? 0` is the defect this type exists to prevent: a class count that has
    // not been taken rendering as "0 classes".
    const fact = measure<number>(null, 20, PARSE_PROGRESSING_PCT);
    expect(fact.state).not.toBe('ready');
    expect(fact).not.toHaveProperty('value');
  });

  it('reports the progress it was asked about, not a default', () => {
    expect(measure(null, 33, PARSE_PROGRESSING_PCT)).toMatchObject({ progressPct: 33 });
  });
});

describe('measure marks a measurement as ready', () => {
  it('a zero is a measurement', () => {
    // The case that must not be confused with absence: parse ran, counted
    // nothing, and zero is the answer.
    expect(measure(0, PARSE_COMPLETE_PCT, PARSE_PROGRESSING_PCT, PARSE_COMPLETE_PCT))
      .toEqual({ state: 'ready', value: 0, settled: true });
  });

  it('an empty list is a measurement', () => {
    expect(measure([] as string[], CLONE_COMPLETE_PCT, CLONE_COMPLETE_PCT)).toEqual({
      state: 'ready',
      value: [],
      settled: true,
    });
  });

  it('a null-valued measurement is still ready', () => {
    // Guard against a truthiness check creeping in. `measure` tests for
    // nullish, not falsy, so a legitimate empty string or zero survives.
    expect(measure('', 30, CLONE_COMPLETE_PCT)).toMatchObject({
      state: 'ready',
      value: '',
    });
  });
});

describe('settled tracks the stage that produces the value', () => {
  it('a clone-stage fact is settled the moment it exists', () => {
    // Clone writes these once and never revises them, so there is no interval
    // in which they are known but still moving.
    for (const pct of [CLONE_COMPLETE_PCT, 30, 99]) {
      expect(measure(1, pct, CLONE_COMPLETE_PCT)).toEqual({
        state: 'ready',
        value: 1,
        settled: true,
      });
    }
  });

  it('a parse-stage fact is unsettled while parse recounts it', () => {
    // The metadata row is rewritten on every checkpoint, so a count read at 30%
    // is real and will still change.
    for (const pct of [PARSE_PROGRESSING_PCT, 40, 55]) {
      expect(
        measure(1, pct, PARSE_PROGRESSING_PCT, PARSE_COMPLETE_PCT),
      ).toEqual({ state: 'ready', value: 1, settled: false });
    }
  });

  it('a parse-stage fact settles exactly at parse completion', () => {
    expect(
      measure(1, PARSE_COMPLETE_PCT, PARSE_PROGRESSING_PCT, PARSE_COMPLETE_PCT),
    ).toEqual({ state: 'ready', value: 1, settled: true });
  });

  it('defaults the settling point to the availability point', () => {
    // Which is what makes every clone-stage call correct without a fourth
    // argument: a fact available at the point its stage completes is final.
    expect(measure(1, 15, 15)).toEqual({ state: 'ready', value: 1, settled: true });
  });
});

describe('the settled flag does not leak into the pending case', () => {
  it('a pending fact carries no value and no settled flag', () => {
    // Structural, not cosmetic: `Fact` in the card switches on `state` and only
    // reads `settled` in the ready branch, so a pending fact with a stale
    // `settled` would be a latent bug waiting for a refactor.
    const fact = measure(null, 40, PARSE_PROGRESSING_PCT);
    expect(fact.state).toBe('pending');
    expect('settled' in fact).toBe(false);
  });

  it('a ready fact always carries a settled flag', () => {
    const fact = measure(1, 40, PARSE_PROGRESSING_PCT);
    expect(fact.state).toBe('ready');
    expect('settled' in fact).toBe(true);
  });
});
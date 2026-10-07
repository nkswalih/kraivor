import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { EngineCard } from './engine-card';
import type { EngineStatusItem } from '@/types/domain/analysis';

/**
 * The finished-run engine grid.
 *
 * This card used to carry its own account of the nine engines the service runs:
 * a five-key label table, and one hand-written function per engine returning
 * prose from score bands nobody in the service had defined. Almost everything
 * below is about what it no longer claims.
 */

function item(overrides: Partial<EngineStatusItem> = {}): EngineStatusItem {
  return {
    key: 'security',
    name: 'Security',
    description: 'Scans for injection, auth and crypto weaknesses',
    status: 'completed',
    duration: '31s',
    score: 82,
    error: null,
    ...overrides,
  };
}

describe('what the card says about an engine', () => {
  it('uses the name the service gave it, not one from a table in this file', () => {
    // The old table had five keys. `churn` was not among them, so it rendered as
    // "Churn" by capitalising a raw key -- which happened to look right, and
    // would have looked wrong the moment the service gave it a real name.
    render(<EngineCard item={item({ key: 'churn', name: 'Churn Analysis' })} />);

    expect(screen.getByText('Churn Analysis')).toBeTruthy();
  });

  it('uses the catalogue description rather than a score band it invented', () => {
    // "82 >= 75" used to mean "Minor security concerns" -- a claim about the
    // scoring model, written in a React file, which nothing in the service
    // agrees with. The catalogue's description is a fact about the engine.
    render(<EngineCard item={item({ score: 82 })} />);

    expect(
      screen.getByText('Scans for injection, auth and crypto weaknesses'),
    ).toBeTruthy();
    expect(screen.queryByText(/Minor security concerns/)).toBeNull();
  });

  it('does not describe a score it has no bands for', () => {
    // Every engine that is not one of the five got the fallback pair, so a
    // 30/100 simulation score and a 30/100 churn score both read "Needs
    // attention" -- two engines, one sentence, no way to tell them apart.
    render(<EngineCard item={item({ key: 'simulation', name: 'Simulation', score: 30 })} />);

    expect(screen.queryByText(/Needs attention|Good results|Analysis complete/)).toBeNull();
  });

  it('shows the score in the ring', () => {
    render(<EngineCard item={item({ score: 82 })} />);

    expect(screen.getByText('82')).toBeTruthy();
  });

  it('shows the engine result count when it has no score', () => {
    // Four engines report rows rather than a score dimension -- dead-code
    // entries, error findings, hotspot files, load levels -- so their rings
    // read N/A forever however much the run produced. The count is the real
    // number that belongs there.
    render(
      <EngineCard item={item({ key: 'dead_code', name: 'Dead Code', score: null, count: 9_914 })} />,
    );

    expect(screen.getByText('9,914')).toBeTruthy();
    expect(screen.queryByText('N/A')).toBeNull();
  });

  it('prefers the score over a count when the engine has both', () => {
    // The performance engine is scored; its metric count only exists to fill
    // the slot on runs the scorer had no data for.
    render(<EngineCard item={item({ score: 82, count: 5 })} />);

    expect(screen.getByText('82')).toBeTruthy();
    expect(screen.queryByText('5')).toBeNull();
  });

  it('shows N/A only when there is neither a score nor a count', () => {
    render(<EngineCard item={item({ score: null, count: null })} />);

    expect(screen.getByText('N/A')).toBeTruthy();
  });

  it('draws no count for an engine that has not finished', () => {
    // A count after a failure would be as stale a claim as a score would be.
    render(<EngineCard item={item({ status: 'failed', score: null, count: 9_914 })} />);

    expect(screen.queryByText('9,914')).toBeNull();
    expect(screen.getByText('N/A')).toBeTruthy();
  });
});

describe('a failed engine', () => {
  it('shows the reason the service recorded instead of a generic sentence', () => {
    // "Engine encountered errors during scan" was the message for all five
    // engines it knew, so a card could say an engine had failed without ever
    // saying why.
    render(
      <EngineCard
        item={item({ status: 'failed', error: 'rules: SemgrepError - exit code 2', score: null })}
      />,
    );

    expect(screen.getByText('rules: SemgrepError - exit code 2')).toBeTruthy();
    expect(screen.queryByText(/Engine encountered errors/)).toBeNull();
  });

  it('prefers the reason over the description when it has one', () => {
    // The card has one text slot. "What this engine normally checks" is not the
    // answer to "why is this card red".
    render(
      <EngineCard item={item({ status: 'failed', error: 'clone: RepositoryNotFound' })} />,
    );

    expect(screen.getByText('clone: RepositoryNotFound')).toBeTruthy();
    expect(screen.queryByText(/Scans for injection/)).toBeNull();
  });

  it('falls back to the description when the failure recorded no reason', () => {
    // Which is the common case for a job cancelled out from under the pipeline.
    // Falling back to a generic failure sentence would be inventing a reason;
    // falling back to what the engine does is true and does not pretend.
    render(<EngineCard item={item({ status: 'failed', error: null, score: null })} />);

    expect(screen.getByText('Scans for injection, auth and crypto weaknesses')).toBeTruthy();
    expect(screen.getByText('Failed')).toBeTruthy();
  });

  it('draws no ring, because a failed engine has no score to show', () => {
    // Showing the last score it reached would be a stale claim; showing a
    // placeholder number would be a fabricated one.
    render(<EngineCard item={item({ status: 'failed', score: 82 })} />);

    expect(screen.queryByText('82')).toBeNull();
  });
});

describe('the states', () => {
  it.each([
    ['completed', 'Completed'],
    ['failed', 'Failed'],
    ['running', 'Running'],
    ['skipped', 'Skipped'],
    ['pending', 'Waiting'],
    ['unavailable', 'Unavailable'],
  ] as const)('names %s as %s', (status, label) => {
    // The old card had five states and no `unavailable`, so a row the service
    // could not describe fell through to the `pending` branch and read
    // "Awaiting execution" -- a claim that it was queued.
    render(<EngineCard item={item({ status, score: status === 'completed' ? 82 : null })} />);

    expect(screen.getByText(label)).toBeTruthy();
  });

  it('draws no ring for a state that is not completed', () => {
    for (const status of ['running', 'skipped', 'pending', 'unavailable'] as const) {
      const { unmount } = render(
        <EngineCard item={item({ status, score: 82, description: 'x' })} />,
      );
      expect(screen.queryByText('82')).toBeNull();
      unmount();
    }
  });

  it('hides the status icon from assistive technology', () => {
    // The word beside it carries the state. An unlabelled graphic announced as
    // "graphic" on top of that is noise.
    const { container } = render(<EngineCard item={item()} />);

    expect(container.querySelector('svg[aria-hidden="true"]')).toBeTruthy();
  });

  it('omits the detail line entirely when there is nothing to say', () => {
    // An empty <p> would still take a line of vertical space, so nine cards in a
    // row would sit nine different heights.
    const { container } = render(
      <EngineCard item={item({ description: '', error: null, status: 'completed' })} />,
    );

    expect(container.querySelectorAll('p')).toHaveLength(0);
  });
});
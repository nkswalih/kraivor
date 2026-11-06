import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { EngineStatusCard } from './EngineStatusCard';
import type { EngineStatusItem } from '@/types/domain/analysis';

/**
 * The sidebar's engine rows.
 *
 * These read the same normalised `EngineStatusItem` the detail page's donuts
 * do, so they carry the same two numbers: the score for engines that have one,
 * and the engine's real result count for the four that report rows instead.
 * The rows used to show a number only for scored engines, which left dead
 * code, errors, hotspots and load simulation blank while the page's count
 * tiles already displayed the very same figures.
 */
function item(overrides: Partial<EngineStatusItem> = {}): EngineStatusItem {
  return {
    key: 'dead_code',
    name: 'Dead Code',
    description: 'Unreachable declarations.',
    status: 'completed',
    duration: '15s',
    score: null,
    count: null,
    error: null,
    ...overrides,
  };
}

describe('EngineStatusCard rows', () => {
  it('shows the result count for an engine that has no score', () => {
    render(<EngineStatusCard items={[item({ count: 9_914 })]} />);

    expect(screen.getByText('9,914')).toBeInTheDocument();
  });

  it('shows the score rather than the count when the engine has both', () => {
    render(<EngineStatusCard items={[item({ key: 'security', name: 'Security', score: 75, count: 5 })]} />);

    expect(screen.getByText('75')).toBeInTheDocument();
    expect(screen.queryByText('5')).toBeNull();
  });

  it('shows neither number when there is nothing to show', () => {
    // The honest state of an engine that neither scored nor produced rows the
    // statistics row has counted yet. The row still says what the engine is
    // and (below) how long it took -- it just invents no number between them.
    render(<EngineStatusCard items={[item()]} />);

    expect(screen.queryByText('N/A')).toBeNull();
    expect(screen.getByText('Dead Code')).toBeInTheDocument();
    expect(screen.getByText('15s')).toBeInTheDocument();
  });

  it('shows no count for an engine that has not finished', () => {
    // A count after a failure would be as stale a claim as a score: the
    // finished-only duration goes with it.
    render(<EngineStatusCard items={[item({ status: 'failed', count: 9_914 })]} />);

    expect(screen.queryByText('9,914')).toBeNull();
    expect(screen.queryByText('15s')).toBeNull();
    expect(screen.getByText('Dead Code')).toBeInTheDocument();
  });
});

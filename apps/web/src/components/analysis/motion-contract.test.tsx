import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/react';
import { ProgressBar } from './progress-bar';
import { ProgressRing } from './progress-ring';
import { EngineCard } from './engine-card';
import { AnalysisProgressPanel } from './progress/AnalysisProgressPanel';
import { EngineStep } from './progress/EngineStep';
import { JobFailurePanel } from './progress/JobFailurePanel';
import { JobStatus } from '@/types/domain/analysis';
import type { AnalysisJob, EngineStatusItem } from '@/types/domain/analysis';

/**
 * One invariant, checked across the whole progress surface.
 *
 * The people who switch reduced motion on have usually been hurt by motion
 * before -- vestibular disorders, migraine, ADHD. Every spinner and every
 * animating edge in a panel someone may sit and watch for ten minutes is a
 * chance to make this page unusable to them. So the rule is not "the important
 * animations respect the setting". It is that no animation exists here without a
 * way to stop it.
 *
 * The pairing is by class rather than by a `useReducedMotion()` hook, so this is
 * a static property of the rendered markup and costs nothing at runtime.
 *
 * ## Why movement and not colour
 *
 * `transition-colors` is deliberately excluded from the sweep. A hue changing
 * over 300ms has no spatial component, does not move anything in the visual
 * field, and is not what the setting is for -- so the retry button's border
 * keeps easing. `animate-*`, and transitions on `width`, `transform` and the
 * `all` shorthand, all move something and must have an opt-out. An element whose
 * only transition is a colour fade is therefore *not* required to carry one.
 *
 * ## Why this is not a browser test
 *
 * `motion-reduce:animate-none` and `animate-spin` have identical specificity, so
 * the pair only works because Tailwind emits the media-query rule after the base
 * utility in the stylesheet. That ordering was verified directly against the
 * built CSS (`@media (prefers-reduced-motion:reduce)` sits at the end of the
 * sheet, past both base rules) rather than asserted here, because testing it
 * would mean building the app from a unit test. What is asserted here is the
 * half a test can actually reach: that the pairing is present at all.
 */

/** A class that moves something in the visual field. */
const MOVES = /^(animate-|transition-(all|width|transform))/;

/** The opt-out that must accompany every one of them. */
const OPTS_OUT = /^motion-reduce:(animate-none|transition-none)$/;

function classesOf(el: Element): string[] {
  return (el.getAttribute('class') ?? '').split(/\s+/).filter(Boolean);
}

/** Every element in a rendered tree that moves something. */
function movingElements(container: HTMLElement): string[] {
  return [...container.querySelectorAll<HTMLElement>('*')]
    .filter(el => classesOf(el).some(c => MOVES.test(c)))
    .map(el => classesOf(el).find(c => MOVES.test(c))!);
}

// ----------------------------------------------------------------------
// Fixtures
// ----------------------------------------------------------------------

function job(overrides: Partial<AnalysisJob> = {}): AnalysisJob {
  return {
    job_id: 'job-1',
    repo_id: 'repo-1',
    workspace_id: 'ws-1',
    status: JobStatus.RULES,
    repo_url: 'https://github.com/acme/app',
    branch: 'main',
    progress_pct: 45,
    progress_message: 'Running rules',
    total_findings: 0,
    total_files: 480,
    total_lines: 12000,
    overall_score: null,
    blocked_by: [],
    engine_statuses: {},
    error_message: null,
    created_at: '2026-01-01T00:00:00Z',
    started_at: '2026-01-01T00:00:00Z',
    completed_at: null,
    languages_detected: null,
    language_breakdown: null,
    ...overrides,
  };
}

function item(overrides: Partial<EngineStatusItem> = {}): EngineStatusItem {
  return {
    name: 'Security',
    key: 'security',
    description: 'Injection and auth checks',
    status: 'completed',
    duration: '4s',
    score: 91,
    error: null,
    ...overrides,
  };
}

/** Every state the surface can be in that shows motion. */
const MOTION_SURFACES: Array<[string, () => HTMLElement]> = [
  [
    'ProgressBar',
    () => render(<ProgressBar pct={45} message="Running rules" />).container as HTMLElement,
  ],
  [
    'ProgressRing',
    () => render(<ProgressRing score={91} label="Security" />).container as HTMLElement,
  ],
  [
    'EngineStep (running)',
    () => render(<EngineStep item={item({ status: 'running', duration: null })} />)
        .container as HTMLElement,
  ],
  [
    'EngineCard (running)',
    () =>
      render(<EngineCard item={item({ status: 'running', score: null, duration: null })} />)
        .container as HTMLElement,
  ],
  [
    'AnalysisProgressPanel',
    () =>
      render(
        <AnalysisProgressPanel
          job={job()}
          engineStatuses={{}}
          items={[item({ status: 'running', duration: null })]}
        />,
      ).container as HTMLElement,
  ],
  [
    'JobFailurePanel (retrying)',
    () =>
      render(
        <JobFailurePanel
          job={job({ status: JobStatus.FAILED, error_message: 'rules failed: exit code 2' })}
          items={[item({ status: 'failed' })]}
          onRetry={() => undefined}
          isRetrying
        />,
      ).container as HTMLElement,
  ],
];

// ======================================================================

describe('reduced motion', () => {
  it.each(MOTION_SURFACES)('%s pairs every movement with an opt-out', (_name, mount) => {
    const container = mount();

    const offenders = [...container.querySelectorAll<HTMLElement>('*')]
      .filter(el => classesOf(el).some(c => MOVES.test(c)))
      .filter(el => !classesOf(el).some(c => OPTS_OUT.test(c)))
      .map(el => classesOf(el).filter(c => MOVES.test(c)).join(' '));

    expect(offenders).toEqual([]);
  });

  it.each(MOTION_SURFACES)('%s actually moves something, so the test above is not vacuous', (_name, mount) => {
    // A surface with nothing animated would pass the pairing check for the
    // wrong reason -- it would pass whether or not the opt-out exists. This
    // keeps the sweep honest by proving each case has something to opt out of.
    expect(movingElements(mount()).length).toBeGreaterThan(0);
  });

  it('covers the bar fill, which is what moves most often', () => {
    // The bar re-renders every two seconds while a run is in flight, easing
    // its width across half a second each time. It is the most frequent motion
    // on the page, so it is the one worth naming in a test rather than leaving
    // to the sweep.
    const { container } = render(<ProgressBar pct={45} message="Running rules" />);
    const fill = container.querySelector<HTMLElement>('.h-full');

    expect(classesOf(fill!)).toContain('transition-all');
    expect(classesOf(fill!)).toContain('motion-reduce:transition-none');
  });

  it('covers the ring arc, which sweeps a drawn edge around a circle', () => {
    const { container } = render(<ProgressRing score={91} label="Security" />);
    const arc = container.querySelector<HTMLElement>('circle[stroke="currentColor"]');

    expect(arc).toBeTruthy();
    expect(classesOf(arc!)).toContain('motion-reduce:transition-none');
  });

  it('leaves a colour-only transition alone', () => {
    // A hue fade has no spatial component. Demanding an opt-out for every
    // `transition-colors` in the app would produce dozens of `motion-reduce`
    // classes that change nothing a reader could perceive as motion, which
    // would make the real ones harder to notice.
    const { container } = render(
      <JobFailurePanel
        job={job({ status: JobStatus.FAILED, error_message: 'rules failed: exit code 2' })}
        items={[item({ status: 'failed' })]}
        onRetry={() => undefined}
      />,
    );

    const button = container.querySelector('button')!;

    expect(classesOf(button)).toContain('transition-colors');
    // And the sweep agrees: a colour-only transition is not counted as movement.
    expect(movingElements(container)).not.toContain('transition-colors');
  });

  it('loops nothing on a finished engine, because there is nothing to indicate', () => {
    // The check that the opt-out is not being applied mechanically, and that
    // the opt-out is not what stops the motion -- a card that has nothing to
    // animate has nothing to animate slowly either.
    //
    // Note this uses `EngineCard`, not `AnalysisProgressPanel`. That panel has no
    // internal running guard: the page decides whether to mount it, so handing it
    // a `COMPLETED` job is a state it is never in, and its spinner would keep
    // turning because nothing told it not to. Testing it that way would have
    // asserted a fiction.
    const { container } = render(<EngineCard item={item({ status: 'completed' })} />);

    const looping = [...container.querySelectorAll<HTMLElement>('*')]
      .flatMap(el => classesOf(el))
      .filter(c => c.startsWith('animate-'));

    expect(looping).toEqual([]);
  });
});

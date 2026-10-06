import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AIExecutiveSummaryCard } from './AIExecutiveSummaryCard';
import { PriorityRecommendationCard } from './PriorityRecommendationCard';
import type { AiSummaryCard, PriorityRecommendation } from '@/types/domain/analysis';

/**
 * Both cards used to render copy that was false in a running state.
 *
 * The summary card labelled itself "Preview" with an empty body and a footer
 * promising the summary "will appear after analysis completes" -- on a job where
 * nothing had completed. The recommendation card had no empty state at all, so
 * its caller could only be handed a fabricated recommendation or a skeleton.
 *
 * The same empty body was also wrong on a *finished* run, which is the state it
 * was actually reached in: the badge and footer were the only things on screen,
 * both promising a summary that would not arrive, with no way to ask for one.
 * That gap now names itself and offers to generate.
 */

const NO_SUMMARY: AiSummaryCard = { summary: '', isAiGenerated: false };

const GENERATED: AiSummaryCard = {
  summary: 'The codebase is well structured with minor issues.',
  isAiGenerated: true,
};

const RECOMMENDATION: PriorityRecommendation = {
  title: 'Improve Performance',
  description: 'Reduce synchronous database operations.',
  impact: 'high',
  difficulty: 'medium',
  estimatedTime: '2-4 hours',
  findingId: null,
  category: 'performance',
};

// ======================================================================
// AI Executive Summary
// ======================================================================

describe('the AI summary card while a run is in flight', () => {
  it('shows a placeholder instead of the preview badge', () => {
    render(<AIExecutiveSummaryCard data={NO_SUMMARY} isRunning />);

    // Nothing has been written yet, so there is nothing to preview.
    expect(screen.queryByText('Preview')).not.toBeInTheDocument();
  });

  it('makes no promise about a summary that has not been written', () => {
    render(<AIExecutiveSummaryCard data={NO_SUMMARY} isRunning />);

    // "will appear after analysis completes" was false here: the run is the
    // thing that has not completed.
    expect(screen.queryByText(/will appear after analysis completes/)).not.toBeInTheDocument();
  });

  it('renders no footer at all', () => {
    const { container } = render(<AIExecutiveSummaryCard data={NO_SUMMARY} isRunning />);

    expect(container.querySelectorAll('p.text-\\[10px\\]')).toHaveLength(0);
  });

  it('keeps its heading, so the card is still identifiable', () => {
    render(<AIExecutiveSummaryCard data={NO_SUMMARY} isRunning />);

    expect(screen.getByText('AI Executive Summary')).toBeInTheDocument();
  });

  it('still shows the placeholder body', () => {
    const { container } = render(<AIExecutiveSummaryCard data={NO_SUMMARY} isRunning />);

    expect(container.querySelectorAll('.animate-shimmer').length).toBeGreaterThan(0);
  });

  it('does not render a summary that arrived early', () => {
    // Not reachable from the API today, but a summary reaching the card before
    // the run ended would be claiming the run produced it.
    render(
      <AIExecutiveSummaryCard
        data={{ summary: 'draft', isAiGenerated: false }}
        isRunning
      />,
    );

    expect(screen.queryByText('draft')).not.toBeInTheDocument();
  });
});

describe('the AI summary card for a finished run', () => {
  it('says the summary is absent rather than labelling it a preview', () => {
    // "Preview" headed an empty body. There was nothing to preview, and it was
    // the first thing on the card that read as broken.
    render(<AIExecutiveSummaryCard data={NO_SUMMARY} />);

    expect(screen.queryByText('Preview')).not.toBeInTheDocument();
    expect(screen.getByText(/no ai summary for this run/i)).toBeInTheDocument();
  });

  it('makes no promise about a summary the run never wrote', () => {
    // The footer's promise was already suppressed for loading, running and a
    // failed guide request. What was left was the case it was worst in: a run
    // that had finished, read as absent, and was told the summary "will appear
    // after analysis completes" -- under an empty body, with nothing to do.
    render(<AIExecutiveSummaryCard data={NO_SUMMARY} />);

    expect(
      screen.queryByText(/will appear after analysis completes/),
    ).not.toBeInTheDocument();
  });

  it('offers the one action that could produce a summary', async () => {
    // The point of the state. A missing summary with no recorded reason is the
    // absence that can still be fixed, and `onRetry` re-runs the enrichment
    // request that would write one.
    const onRetry = vi.fn();
    render(<AIExecutiveSummaryCard data={NO_SUMMARY} onRetry={onRetry} />);

    await userEvent.click(
      screen.getByRole('button', { name: /generate ai summary/i }),
    );
    expect(onRetry).toHaveBeenCalledOnce();
  });

  it('says it is generating while the request is in flight', () => {
    render(
      <AIExecutiveSummaryCard data={NO_SUMMARY} onRetry={vi.fn()} isRetrying />,
    );

    const button = screen.getByRole('button', { name: /generating/i });
    expect(button).toBeDisabled();
  });

  it('still explains the gap to a reader with nowhere to send it', () => {
    // Same contract as the error panel: the reason is worth showing regardless,
    // only the button depends on there being somewhere to go.
    render(<AIExecutiveSummaryCard data={NO_SUMMARY} />);

    expect(screen.getByText(/finished without producing one/i)).toBeInTheDocument();
    expect(
      screen.queryByRole('button', { name: /generate ai summary/i }),
    ).not.toBeInTheDocument();
  });

  it('omits the badge for a generated summary', () => {
    render(<AIExecutiveSummaryCard data={GENERATED} />);

    expect(screen.queryByText('Preview')).not.toBeInTheDocument();
    expect(screen.queryByText(/Static preview/)).not.toBeInTheDocument();
  });

  it('renders the generated summary', () => {
    render(<AIExecutiveSummaryCard data={GENERATED} />);

    expect(screen.getByText(GENERATED.summary)).toBeInTheDocument();
  });

  it('renders the placeholder when the job is still loading', () => {
    const { container } = render(<AIExecutiveSummaryCard data={NO_SUMMARY} isLoading />);

    expect(container.querySelectorAll('.animate-shimmer').length).toBeGreaterThan(0);
    // Loading and running both suppress the footer: neither has a summary yet.
    expect(screen.queryByText(/Static preview/)).not.toBeInTheDocument();
  });

  it('waits for the guide request before claiming a summary is missing', () => {
    // The case this exists for. The page finishes loading the job, but the
    // guide request that carries the summary is still in flight, so `data` is
    // undefined and the summary reads as absent. Showing the footer then said
    // "AI summary will appear after analysis completes" for a job that had
    // completed -- while the summary was on its way.
    const { container } = render(
      <AIExecutiveSummaryCard data={NO_SUMMARY} guidePending />,
    );

    expect(container.querySelectorAll('.animate-shimmer').length).toBeGreaterThan(0);
    expect(screen.queryByText('Preview')).not.toBeInTheDocument();
    expect(screen.queryByText(/Static preview/)).not.toBeInTheDocument();
  });

  it('offers to generate one once the guide request settles without a summary', async () => {
    // The other side of the boundary: pending has ended and there is genuinely
    // no summary. That is a real gap, and a real gap gets an action instead of
    // a footer promising something that is no longer coming.
    const onRetry = vi.fn();
    render(
      <AIExecutiveSummaryCard data={NO_SUMMARY} guidePending={false} onRetry={onRetry} />,
    );

    await userEvent.click(
      screen.getByRole('button', { name: /generate ai summary/i }),
    );
    expect(onRetry).toHaveBeenCalledOnce();
    expect(screen.queryByText(/Static preview/)).not.toBeInTheDocument();
  });

  it('renders a summary that arrived with the guide', () => {
    render(
      <AIExecutiveSummaryCard data={GENERATED} guidePending={false} />,
    );

    expect(screen.getByText(GENERATED.summary)).toBeInTheDocument();
    expect(screen.queryByText('Preview')).not.toBeInTheDocument();
  });

  it('treats the three pending causes identically', () => {
    // One rendering for "a summary is expected but not here yet", whichever of
    // the three reasons applies, so the caller cannot get them inconsistent.
    for (const props of [{ isLoading: true }, { isRunning: true }, { guidePending: true }]) {
      const { container, unmount } = render(
        <AIExecutiveSummaryCard data={NO_SUMMARY} {...props} />,
      );
      expect(container.querySelectorAll('.animate-shimmer').length).toBeGreaterThan(0);
      expect(screen.queryByText('Preview')).not.toBeInTheDocument();
      unmount();
    }
  });

  it('waits for the guide even with a generated summary already in hand', () => {
    // `isAiGenerated` is settled data, but the request that carries it is still
    // in flight -- so the body stays a skeleton rather than showing a summary
    // that refetch may replace. The opposite failure would be flashing a
    // summary and then swapping it out from under the reader.
    const { container } = render(
      <AIExecutiveSummaryCard data={GENERATED} guidePending />,
    );

    expect(container.querySelectorAll('.animate-shimmer').length).toBeGreaterThan(0);
    expect(screen.queryByText(GENERATED.summary)).not.toBeInTheDocument();
  });
});

// ======================================================================
// Priority Recommendation
// ======================================================================

describe('the recommendation card with no recommendation', () => {
  it('renders nothing rather than an empty card', () => {
    // An empty card would read as "nothing was found". A skeleton would read as
    // "one is coming". Neither is true: the run has not reached a conclusion.
    const { container } = render(<PriorityRecommendationCard data={null} />);

    expect(container.firstChild).toBeNull();
  });

  it('shows its skeleton while the job is still loading', () => {
    // Order matters. Loading is checked first, because there the recommendation
    // is genuinely unknown -- once the job loads it may turn out to be a
    // completed run with a recommendation. Skeleton is the honest answer for
    // "not known yet", where `data === null` after loading means "none exists".
    const { container } = render(
      <PriorityRecommendationCard data={null} isLoading />,
    );

    expect(container.querySelectorAll('.animate-shimmer').length).toBeGreaterThan(0);
  });

  it('does not show the heading', () => {
    render(<PriorityRecommendationCard data={null} />);

    expect(
      screen.queryByText('Highest Priority Recommendation'),
    ).not.toBeInTheDocument();
  });

  it('is distinct from a completed run that produced no recommendation', () => {
    // Same null, opposite meaning: loaded-and-absent is silence, still-loading is
    // a placeholder. Collapsing them would either promise a recommendation that
    // is never coming, or flash an empty card on every page load.
    const loaded = render(<PriorityRecommendationCard data={null} />);
    expect(loaded.container.firstChild).toBeNull();

    loaded.unmount();

    const loading = render(<PriorityRecommendationCard data={null} isLoading />);
    expect(loading.container.querySelectorAll('.animate-shimmer').length)
      .toBeGreaterThan(0);
  });
});

describe('the recommendation card with a recommendation', () => {
  it('renders it unchanged', () => {
    render(<PriorityRecommendationCard data={RECOMMENDATION} />);

    expect(screen.getByText('Improve Performance')).toBeInTheDocument();
    expect(
      screen.getByText('Reduce synchronous database operations.'),
    ).toBeInTheDocument();
    expect(screen.getByText('High Impact')).toBeInTheDocument();
    expect(screen.getByText('Medium Difficulty')).toBeInTheDocument();
    expect(screen.getByText('2-4 hours')).toBeInTheDocument();
  });

  it('omits the view-finding button when there is no finding', () => {
    render(<PriorityRecommendationCard data={RECOMMENDATION} />);

    expect(screen.queryByText('View Finding')).not.toBeInTheDocument();
  });

  it('offers the view-finding button when there is one', () => {
    render(
      <PriorityRecommendationCard
        data={{ ...RECOMMENDATION, findingId: 'f-1' }}
        onViewFinding={() => {}}
      />,
    );

    expect(screen.getByText('View Finding')).toBeInTheDocument();
  });

  it('shows its loading skeleton when asked, even with data present', () => {
    const { container } = render(
      <PriorityRecommendationCard data={RECOMMENDATION} isLoading />,
    );

    expect(container.querySelectorAll('.animate-shimmer').length).toBeGreaterThan(0);
    expect(screen.queryByText('Improve Performance')).not.toBeInTheDocument();
  });
});
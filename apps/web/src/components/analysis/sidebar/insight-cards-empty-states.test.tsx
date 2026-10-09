import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AIExecutiveSummaryCard } from './AIExecutiveSummaryCard';
import { PriorityRecommendationCard } from './PriorityRecommendationCard';
import { Severity } from '@/types/domain/analysis';
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
 *
 * The recommendation card's null went the other way: it now stands for three
 * different answers -- the run in flight (no conclusion yet), a fetch that
 * failed (no conclusion knowable), and a finished run whose findings really are
 * empty (the conclusion). Only the third has copy, because it is the only one
 * the run actually said something.
 */

const NO_SUMMARY: AiSummaryCard = { summary: '', isAiGenerated: false };

const GENERATED: AiSummaryCard = {
  summary: 'The codebase is well structured with minor issues.',
  isAiGenerated: true,
};

// The shape a card takes when it quotes a finding: every content field comes
// from that finding, badge and location included. Nothing here is generic --
// the old template strings this fixture used to hold are gone from the code.
const RECOMMENDATION: PriorityRecommendation = {
  title: 'Eager-load items with a single join.',
  description: 'Order.items is queried once per row across 400 rows.',
  impact: 'high',
  difficulty: 'medium',
  estimatedTime: '2-4 hours',
  findingId: 'f-1',
  category: 'performance',
  severity: Severity.HIGH,
  filePath: 'src/api/orders.py',
  lineStart: 87,
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
  it('renders nothing while the run is still going', () => {
    // An empty card would read as "nothing was found". A skeleton would read
    // as "one is coming". Neither is true: the run has not reached a
    // conclusion, and the analysing view has always shown neither.
    const { container } = render(
      <PriorityRecommendationCard data={null} isRunning />,
    );

    expect(container.firstChild).toBeNull();
    expect(
      screen.queryByText('Highest Priority Recommendation'),
    ).not.toBeInTheDocument();
  });

  it('renders nothing when the findings fetch failed', () => {
    // A request that never came back says nothing about the run. Claiming an
    // empty one here would be a claim made from evidence never collected.
    const { container } = render(<PriorityRecommendationCard data={null} isError />);

    expect(container.firstChild).toBeNull();
    expect(
      screen.queryByText('Highest Priority Recommendation'),
    ).not.toBeInTheDocument();
  });

  it('shows its skeleton while the answer is still unknown', () => {
    // Order matters. Loading is checked first, because there the recommendation
    // is genuinely unknown -- once loading settles it may turn out to be a
    // finished run whose null *is* its answer, with copy for it below.
    const { container } = render(
      <PriorityRecommendationCard data={null} isLoading />,
    );

    expect(container.querySelectorAll('.animate-shimmer').length).toBeGreaterThan(0);
    expect(
      screen.queryByText('Highest Priority Recommendation'),
    ).not.toBeInTheDocument();
  });

  it('gives a finished run with no findings an honest answer', () => {
    // The state this card was rebuilt for. The findings row loaded, and it is
    // empty: that is information, and the card states it rather than staying
    // silent or borrowing advice nobody measured.
    render(<PriorityRecommendationCard data={null} />);

    expect(
      screen.getByText('Highest Priority Recommendation'),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/no findings recorded for this run/i),
    ).toBeInTheDocument();
    expect(screen.getByText(/nothing to prioritise/i)).toBeInTheDocument();
  });

  it('offers no action and no advice on an empty run', () => {
    // The card used to fill this space with a template -- "Improve
    // Performance", "Refactor Churn Hotspots" -- instructions measured against
    // nothing. An empty state carries a status, not a suggestion.
    render(<PriorityRecommendationCard data={null} />);

    expect(screen.queryByRole('button')).not.toBeInTheDocument();
    expect(screen.queryByText(/improve/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/refactor/i)).not.toBeInTheDocument();
  });

  it('tells a running run apart from a finished empty one', () => {
    // Same null, opposite meaning: in flight means the answer has not been
    // reached, finished means the answer *is* "none". Collapsing them would
    // either flash an empty card on every page load or promise a
    // recommendation that is never coming.
    const inFlight = render(<PriorityRecommendationCard data={null} isRunning />);
    expect(inFlight.container.firstChild).toBeNull();
    inFlight.unmount();

    const empty = render(<PriorityRecommendationCard data={null} />);
    expect(empty.container.firstChild).not.toBeNull();
    expect(
      screen.getByText(/no findings recorded for this run/i),
    ).toBeInTheDocument();
    empty.unmount();
  });
});

describe('the recommendation card with a recommendation', () => {
  it('renders it unchanged', () => {
    render(<PriorityRecommendationCard data={RECOMMENDATION} />);

    expect(
      screen.getByText('Eager-load items with a single join.'),
    ).toBeInTheDocument();
    expect(
      screen.getByText('Order.items is queried once per row across 400 rows.'),
    ).toBeInTheDocument();
    expect(screen.getByText('High Impact')).toBeInTheDocument();
    expect(screen.getByText('Medium Difficulty')).toBeInTheDocument();
    expect(screen.getByText('2-4 hours')).toBeInTheDocument();
  });

  it('badges the finding it is quoting', () => {
    render(<PriorityRecommendationCard data={RECOMMENDATION} />);

    // The badge reads the severity of the finding on screen, so the ranking
    // that chose it and the badge showing it cannot drift apart.
    expect(screen.getByText('High')).toBeInTheDocument();
  });

  it('shows no badge when the recommendation names no severity', () => {
    render(
      <PriorityRecommendationCard
        data={{ ...RECOMMENDATION, severity: null }}
      />,
    );

    expect(screen.queryByText('High')).not.toBeInTheDocument();
  });

  it('names the file and line the finding points at', () => {
    render(<PriorityRecommendationCard data={RECOMMENDATION} />);

    expect(screen.getByText('src/api/orders.py:87')).toBeInTheDocument();
  });

  it('omits the location when the finding points at no file', () => {
    render(
      <PriorityRecommendationCard
        data={{ ...RECOMMENDATION, filePath: null, lineStart: null }}
      />,
    );

    expect(screen.queryByText(/orders\.py/)).not.toBeInTheDocument();
  });

  it('omits the view-finding button when there is no finding', () => {
    render(
      <PriorityRecommendationCard
        data={{ ...RECOMMENDATION, findingId: null }}
      />,
    );

    expect(screen.queryByText('View Finding')).not.toBeInTheDocument();
  });

  it('offers the view-finding button when there is one', async () => {
    const onViewFinding = vi.fn();
    render(
      <PriorityRecommendationCard
        data={RECOMMENDATION}
        onViewFinding={onViewFinding}
      />,
    );

    await userEvent.click(screen.getByText('View Finding'));
    expect(onViewFinding).toHaveBeenCalledOnce();
  });

  it('shows its loading skeleton when asked, even with data present', () => {
    const { container } = render(
      <PriorityRecommendationCard data={RECOMMENDATION} isLoading />,
    );

    expect(container.querySelectorAll('.animate-shimmer').length).toBeGreaterThan(0);
    expect(
      screen.queryByText('Eager-load items with a single join.'),
    ).not.toBeInTheDocument();
  });
});
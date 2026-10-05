import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
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
  it('labels a non-generated summary as a preview', () => {
    render(<AIExecutiveSummaryCard data={NO_SUMMARY} />);

    expect(screen.getByText('Preview')).toBeInTheDocument();
  });

  it('keeps the footer wording for a finished run', () => {
    // Unchanged on purpose. A finished run with no summary is a real gap, and
    // the message that says which failure caused it belongs with the error
    // handling rather than here.
    render(<AIExecutiveSummaryCard data={NO_SUMMARY} />);

    expect(
      screen.getByText(/Static preview — AI summary will appear after analysis completes/),
    ).toBeInTheDocument();
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
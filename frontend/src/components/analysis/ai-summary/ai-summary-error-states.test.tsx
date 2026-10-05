import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AIExecutiveSummaryCard } from '@/components/analysis/sidebar/AIExecutiveSummaryCard';
import { AiExecutiveSummarySection } from '@/components/analysis/enterprise-guide/AiExecutiveSummarySection';
import { analysisService } from '@/lib/api/analysis-service';
import { toast } from 'sonner';
import type { AiSummaryCard, AiSummaryError } from '@/types/domain/analysis';

/**
 * Four different things used to render one sentence.
 *
 * "AI enrichment is not available. Click Regenerate to retry." was shown for a
 * run whose summary had not been generated yet, a run whose provider key was
 * missing, a run the provider rate-limited, and a run whose summary arrived too
 * short to be one. It asked for a retry in all four, including the two where a
 * retry cannot work.
 *
 * Most of what follows asserts the *specific* reason reaches a reader. A test
 * that only checked "no longer shows the old message" would pass on a component
 * that rendered nothing at all.
 */

afterEach(() => {
  vi.restoreAllMocks();
});

function error(overrides: Partial<AiSummaryError> = {}): AiSummaryError {
  return {
    code: 'rate_limited',
    message: 'The model provider is rate limiting requests.',
    suggested_action: 'wait',
    retry_after: 30,
    ...overrides,
  };
}

function card(overrides: Partial<AiSummaryCard> = {}): AiSummaryCard {
  return { summary: '', isAiGenerated: false, error: null, ...overrides };
}

// ======================================================================
// The sidebar card
// ======================================================================

describe('The sidebar card', () => {
  it('names the failure instead of promising a summary that is not coming', () => {
    render(<AIExecutiveSummaryCard data={card({ error: error() })} />);

    expect(screen.getByText('The AI service is busy')).toBeInTheDocument();
    expect(
      screen.queryByText(/will appear after analysis completes/i),
    ).not.toBeInTheDocument();
  });

  it('shows the service`s own explanation, not only our headline', () => {
    // The headline is a fixed string, so it can only say so much. The detail is
    // the service's classification, and replacing it with our wording would
    // throw away information this component cannot enumerate.
    render(
      <AIExecutiveSummaryCard
        data={card({
          error: error({ message: 'Upstream said: quota exceeded for this key.' }),
        })}
      />,
    );

    expect(screen.getByText('Upstream said: quota exceeded for this key.')).toBeInTheDocument();
  });

  it('offers a retry when the failure could plausibly clear', async () => {
    const onRetry = vi.fn();
    render(
      <AIExecutiveSummaryCard
        data={card({ error: error({ suggested_action: 'wait' }) })}
        onRetry={onRetry}
      />,
    );

    await userEvent.click(screen.getByRole('button', { name: /retry ai summary/i }));
    expect(onRetry).toHaveBeenCalledOnce();
  });

  it('withholds the retry when the credential is wrong, and says it was withheld', () => {
    // A rejected key is wrong now and will be wrong in thirty seconds. A retry
    // button here is advice that cannot work, and its absence without comment
    // reads as a broken card rather than as a decision.
    render(
      <AIExecutiveSummaryCard
        data={card({
          error: error({ code: 'auth_failed', suggested_action: 'add_key' }),
        })}
        onRetry={vi.fn()}
      />,
    );

    expect(screen.queryByRole('button', { name: /retry ai summary/i })).not.toBeInTheDocument();
    expect(screen.getByText(/retrying will not help/i)).toBeInTheDocument();
  });

  it('still shows the reason to a reader who cannot act on it', () => {
    // No `onRetry` at all -- the prop is optional. The reason is worth showing
    // regardless; only the button depends on there being somewhere to send it.
    render(
      <AIExecutiveSummaryCard
        data={card({
          error: error({
            code: 'provider_not_configured',
            suggested_action: 'add_key',
          }),
        })}
      />,
    );

    expect(screen.getByText('AI summaries are not enabled')).toBeInTheDocument();
  });

  it('reads the wait hint in units a reader can wait for', () => {
    render(<AIExecutiveSummaryCard data={card({ error: error({ retry_after: 30 }) })} />);

    expect(screen.getByText(/about 30 seconds from now/i)).toBeInTheDocument();
  });

  it('coarsens a long wait to minutes rather than showing a bare number', () => {
    render(
      <AIExecutiveSummaryCard data={card({ error: error({ retry_after: 300 }) })} />,
    );

    expect(screen.getByText(/about 5 minutes from now/i)).toBeInTheDocument();
  });

  it('omits the wait hint when the provider gave none', () => {
    // `retry_after` absent means "no hint". Zero means the same thing on the wire,
    // and rendering it would say "about 0 seconds from now" -- advice to retry
    // immediately from a failure that was not immediate.
    const noHint: AiSummaryError = { code: 'unknown', message: 'Something failed.' };
    render(<AIExecutiveSummaryCard data={card({ error: noHint })} />);

    // No `canRetry` here either, since there is no `onRetry`: the hint is only
    // rendered alongside a retry, because "wait 30 seconds" with no way to wait
    // is advice for a reader who cannot take it.
    expect(screen.queryByText(/from now/i)).not.toBeInTheDocument();
  });

  it('shows the wait hint even when there is nowhere to retry from', () => {
    // The mirror of the case above. A reader told to wait should be told how
    // long, whether or not this surface happens to offer the button.
    render(
      <AIExecutiveSummaryCard
        data={card({ error: error({ retry_after: 30 }) })}
      />,
    );

    expect(screen.getByText(/about 30 seconds from now/i)).toBeInTheDocument();
  });

  it('does not show the error while the run is still going', () => {
    // A run in flight has no summary and none is expected. Rendering a failure
    // for it would be reporting an outcome that has not happened.
    render(
      <AIExecutiveSummaryCard data={card({ error: error() })} isRunning />,
    );

    expect(screen.queryByText('The AI service is busy')).not.toBeInTheDocument();
  });

  it('does not show the error while the guide is still loading', () => {
    // Same reasoning for the third busy state. Before this, "no summary" could
    // not be told apart from "not read yet", and the footer claimed a summary was
    // on its way for both.
    render(
      <AIExecutiveSummaryCard data={card({ error: error() })} guidePending />,
    );

    expect(screen.queryByText('The AI service is busy')).not.toBeInTheDocument();
  });

  it('shows a summary that exists even if a caller pairs it with an error', () => {
    // `insights-builder` drops the error when a summary is present, so this state
    // cannot arise from the app. The guard is here because `data` is a plain
    // object and a card that rendered an error over a real summary would be
    // hiding work that succeeded.
    render(
      <AIExecutiveSummaryCard
        data={{
          summary: '## Assessment\n\nThe service is healthy.',
          isAiGenerated: true,
          error: error(),
        }}
      />,
    );

    expect(screen.getByText('Assessment')).toBeInTheDocument();
    expect(screen.queryByText('The AI service is busy')).not.toBeInTheDocument();
  });
});

// ======================================================================
// The guide section
// ======================================================================

describe('The guide section', () => {
  /**
   * `useReEnrich` is called unconditionally, so `useQueryClient` runs even for
   * the tests that never press Regenerate. The provider is not incidental
   * scaffolding for the click tests -- it is what lets the render-only ones run
   * at all.
   */
  function renderSection(props: {
    summary: string | null;
    error?: AiSummaryError | null;
  }) {
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    });
    return render(
      <QueryClientProvider client={client}>
        <AiExecutiveSummarySection
          summary={props.summary}
          error={props.error}
          jobId="job-1"
        />
      </QueryClientProvider>
    );
  }

  it('names the failure instead of saying enrichment is unavailable', () => {
    renderSection({ summary: null, error: error() });

    expect(screen.getByText('The AI service is busy')).toBeInTheDocument();
    expect(
      screen.queryByText(/enrichment is not available/i),
    ).not.toBeInTheDocument();
  });

  it('labels a summary that is present but stale', () => {
    // A failed re-enrich keeps the previous summary on purpose, and records the
    // new reason beside it. That pair means "the last one that worked" -- not
    // "no summary", and certainly not "a current summary".
    renderSection({
      summary: '## Assessment\n\nWritten before the provider started refusing us.',
      error: error({ suggested_action: 'wait' }),
    });

    expect(screen.getByText(/stale/i)).toBeInTheDocument();
    expect(screen.getByText('The AI service is busy')).toBeInTheDocument();
    // Still shown. A paying user should not lose a summary because a regenerate
    // did not work.
    expect(screen.getByText('Assessment')).toBeInTheDocument();
  });

  it('keeps the original wording when no reason has been recorded', () => {
    // No summary and no recorded reason means the stage never ran. That is the
    // one case where "not available, click Regenerate" is accurate, so it is kept
    // rather than replaced.
    renderSection({ summary: null, error: null });

    expect(screen.getByText(/enrichment is not available/i)).toBeInTheDocument();
  });

  it('reports a failed regeneration as a failure', async () => {
    const spy = vi.spyOn(analysisService.jobs, 'reEnrich').mockResolvedValue({
      status: 'degraded',
      enriched: true,
      has_summary: false,
      ai_summary_error: error(),
    });
    const success = vi.spyOn(toast, 'success').mockImplementation(() => '');
    const failure = vi.spyOn(toast, 'error').mockImplementation(() => '');

    renderSection({ summary: null, error: error() });

    await userEvent.click(screen.getByRole('button', { name: /regenerate/i }));

    await waitFor(() => expect(spy).toHaveBeenCalledWith('job-1'));
    // The bug: arrival was treated as success. A 200 carrying
    // `status: "degraded"` means the findings were re-enriched and the summary
    // was not produced, and the previous code toasted "regenerated" over it.
    await waitFor(() => expect(failure).toHaveBeenCalled());
    expect(success).not.toHaveBeenCalled();
  });

  it('reports a successful regeneration as a success', async () => {
    vi.spyOn(analysisService.jobs, 'reEnrich').mockResolvedValue({
      status: 'ok',
      enriched: true,
      has_summary: true,
      ai_summary_error: null,
    });
    const success = vi.spyOn(toast, 'success').mockImplementation(() => '');
    const failure = vi.spyOn(toast, 'error').mockImplementation(() => '');

    renderSection({ summary: '## Assessment\n\nFine.' });

    await userEvent.click(screen.getByRole('button', { name: /regenerate/i }));

    await waitFor(() => expect(success).toHaveBeenCalledWith('AI enrichment regenerated'));
    expect(failure).not.toHaveBeenCalled();
  });
});

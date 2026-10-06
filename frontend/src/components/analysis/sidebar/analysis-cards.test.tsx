import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { RepositoryOverviewCard } from './RepositoryOverviewCard';
import { AnalysisMetadataCard } from './AnalysisMetadataCard';
import type { AnalysisMetadata, RepositoryOverview } from '@/types/domain/analysis';

/**
 * The distinction these tests exist to pin: `null` means "not measured yet" and
 * must not render as a number, while a measured `0` must. Collapsing the two is
 * how "0 classes" ends up on screen for a repository nobody has counted yet.
 */

function overview(overrides: Partial<RepositoryOverview> = {}): RepositoryOverview {
  return {
    languages: [],
    totalFiles: 0,
    totalLines: 0,
    classes: null,
    functions: null,
    endpoints: null,
    frameworks: null,
    ...overrides,
  };
}

function metadata(overrides: Partial<AnalysisMetadata> = {}): AnalysisMetadata {
  return {
    totalFiles: null,
    totalLines: null,
    classes: null,
    functions: null,
    endpoints: null,
    languages: null,
    duration: null,
    startedAt: null,
    completedAt: null,
    branch: null,
    repoUrl: null,
    workspaceId: null,
    ...overrides,
  };
}

describe('RepositoryOverviewCard distinguishes unmeasured from zero', () => {
  it('renders a measured zero as 0', () => {
    render(<RepositoryOverviewCard data={overview({ totalFiles: 0, totalLines: 0 })} />);

    // Two figures, both legitimately zero.
    expect(screen.getAllByText('0')).toHaveLength(2);
  });

  it('renders an unmeasured count as a placeholder, not a 0', () => {
    render(<RepositoryOverviewCard data={overview({ totalFiles: null, totalLines: null })} />);

    expect(screen.queryByText('0')).not.toBeInTheDocument();
    expect(screen.getByLabelText('Files not measured yet')).toBeInTheDocument();
    expect(screen.getByLabelText('Lines not measured yet')).toBeInTheDocument();
  });

  it('renders one figure measured and one not', () => {
    // Clone writes both counts in the same call, so this state should not occur
    // -- but if it ever did, the card must not silently substitute for the
    // missing one.
    render(<RepositoryOverviewCard data={overview({ totalFiles: 12, totalLines: null })} />);

    expect(screen.getByText('12')).toBeInTheDocument();
    expect(screen.getByLabelText('Lines not measured yet')).toBeInTheDocument();
  });

  it('shows an unmeasured language list as a skeleton', () => {
    const { container } = render(
      <RepositoryOverviewCard data={overview({ languages: null })} />,
    );

    expect(container.querySelectorAll('.animate-shimmer').length).toBeGreaterThan(0);
  });

  it('says so plainly when languages were measured and none were found', () => {
    // The real answer, and different from "not measured yet".
    render(<RepositoryOverviewCard data={overview({ languages: [] })} />);

    expect(screen.getByText('No language data available yet.')).toBeInTheDocument();
  });

  it('renders measured languages with their real shares', () => {
    render(
      <RepositoryOverviewCard
        data={overview({
          languages: [
            { name: 'Python', percentage: 70.5, color: '#3572A5' },
            { name: 'Go', percentage: 29.5, color: '#00ADD8' },
          ],
        })}
      />,
    );

    expect(screen.getByText('Python')).toBeInTheDocument();
    expect(screen.getByText('70.5%')).toBeInTheDocument();
    expect(screen.getByText('29.5%')).toBeInTheDocument();
    expect(screen.queryByText('No language data available yet.')).not.toBeInTheDocument();
  });

  // ---------------------------------------------------------------------
  // The shares are shown as shares, not as raw two-decimal fractions
  // ---------------------------------------------------------------------
  //
  // The service now reports two decimals so a real 0.011% survives the round
  // trip instead of becoming `0.0` and rendering as "0%". Printing those two
  // decimals back out would move the defect sideways rather than fix it: a
  // column of 53.5% / 26.9% / 0.011% reads as broken. These three cases are
  // the ones that can each be wrong in their own way.

  it('never prints a real share as 0%', () => {
    render(
      <RepositoryOverviewCard
        data={overview({
          languages: [
            { name: 'Python', percentage: 99.96, color: '#3572A5' },
            { name: 'Shell', percentage: 0.04, color: '#89e051' },
          ],
        })}
      />,
    );

    // 0.04% is a share this repository has. Rounding it to one decimal would
    // produce "0.0", and printing that is the same lie as "0%" with an extra
    // digit on the end.
    expect(screen.getByText('Shell')).toBeInTheDocument();
    expect(screen.getByText('<0.1%')).toBeInTheDocument();
    expect(screen.queryByText('0%')).not.toBeInTheDocument();
    expect(screen.queryByText('0.0%')).not.toBeInTheDocument();
  });

  it('keeps the precision the service sent where one decimal is honest', () => {
    render(
      <RepositoryOverviewCard
        data={overview({
          languages: [
            { name: 'Python', percentage: 99.9, color: '#3572A5' },
            { name: 'Makefile', percentage: 0.1, color: '#427819' },
          ],
        })}
      />,
    );

    expect(screen.getByText('99.9%')).toBeInTheDocument();
    expect(screen.getByText('0.1%')).toBeInTheDocument();
    // 0.1 is not below 0.1, so it is printed rather than elided.
    expect(screen.queryByText('<0.1%')).not.toBeInTheDocument();
  });

  it('reports an exactly-zero share as 0%, because it was measured', () => {
    render(
      <RepositoryOverviewCard
        data={overview({
          languages: [
            { name: 'Python', percentage: 100, color: '#3572A5' },
            { name: 'Go', percentage: 0, color: '#00ADD8' },
          ],
        })}
      />,
    );

    // The two are different answers and the card has to keep them apart: one
    // says "measured, and none of these lines are Go", the other says nothing
    // was measured at all.
    expect(screen.getByText('100.0%')).toBeInTheDocument();
    expect(screen.getByText('0%')).toBeInTheDocument();
  });

  it('states the same shares to a screen reader', () => {
    // The visual label was rounded; the aria-label was not, so a screen reader
    // used to announce "0%" for a language the eye could see was present.
    render(
      <RepositoryOverviewCard
        data={overview({
          languages: [{ name: 'Shell', percentage: 0.05, color: '#89e051' }],
        })}
      />,
    );

    expect(screen.getByRole('img', { name: /Shell <0\.1%/ })).toBeInTheDocument();
  });

  it('carries the whole measured shape of the repository, not just files and lines', () => {
    render(
      <RepositoryOverviewCard
        data={overview({
          totalFiles: 2090,
          totalLines: 399055,
          classes: 1393,
          functions: 3890,
          endpoints: 47,
          frameworks: 3,
        })}
      />,
    );

    expect(screen.getByText('2,090')).toBeInTheDocument();
    expect(screen.getByText('399,055')).toBeInTheDocument();
    expect(screen.getByText('1,393')).toBeInTheDocument();
    expect(screen.getByText('3,890')).toBeInTheDocument();
    expect(screen.getByText('47')).toBeInTheDocument();
    expect(screen.getByText('3')).toBeInTheDocument();
  });

  it('withholds the shape counts the parse stage has not taken yet', () => {
    render(
      <RepositoryOverviewCard
        data={overview({
          totalFiles: null,
          totalLines: null,
          classes: null,
          functions: null,
        })}
      />,
    );

    expect(screen.queryByText('0')).not.toBeInTheDocument();
    expect(screen.getByLabelText('Classes not measured yet')).toBeInTheDocument();
    expect(screen.getByLabelText('Functions not measured yet')).toBeInTheDocument();
  });
});

describe('AnalysisMetadataCard distinguishes unmeasured from zero', () => {
  it('shows an em-dash for every count nothing has measured', () => {
    render(<AnalysisMetadataCard data={metadata()} />);

    // Files, LOC, Classes, Functions, Endpoints, Languages, Duration, Started,
    // Completed, Branch, Repository, Workspace are all unmeasured.
    expect(screen.getAllByText('—').length).toBe(12);
    expect(screen.queryByText('0')).not.toBeInTheDocument();
  });

  it('renders a measured zero as 0', () => {
    render(<AnalysisMetadataCard data={metadata({ classes: 0, functions: 0, endpoints: 0 })} />);

    expect(screen.getAllByText('0')).toHaveLength(3);
  });

  it('renders the measured counts a completed run produced', () => {
    render(
      <AnalysisMetadataCard
        data={metadata({
          totalFiles: 120,
          totalLines: 8400,
          classes: 30,
          functions: 210,
          endpoints: 12,
        })}
      />,
    );

    expect(screen.getByText('120')).toBeInTheDocument();
    expect(screen.getByText('8,400')).toBeInTheDocument();
    expect(screen.getByText('30')).toBeInTheDocument();
    expect(screen.getByText('210')).toBeInTheDocument();
    expect(screen.getByText('12')).toBeInTheDocument();
  });

  it('lists measured languages', () => {
    render(<AnalysisMetadataCard data={metadata({ languages: ['Python', 'Go'] })} />);

    expect(screen.getByText('Python, Go')).toBeInTheDocument();
  });

  it('shows an em-dash for a measured but empty language list', () => {
    // Different from "not measured", though both render as a dash; the reason
    // they differ is the API keeps them apart.
    render(<AnalysisMetadataCard data={metadata({ languages: [] })} />);

    expect(screen.queryByText('—,')).not.toBeInTheDocument();
  });

  it('renders the duration a completed run reported', () => {
    render(<AnalysisMetadataCard data={metadata({ duration: '1m 35s' })} />);

    expect(screen.getByText('1m 35s')).toBeInTheDocument();
  });

  it('strips the github prefix from the repository url', () => {
    render(
      <AnalysisMetadataCard data={metadata({ repoUrl: 'https://github.com/acme/widget' })} />,
    );

    expect(screen.getByText('acme/widget')).toBeInTheDocument();
  });

  it('shortens the workspace id', () => {
    render(
      <AnalysisMetadataCard data={metadata({ workspaceId: 'abcdef12-3456-7890-abcd-ef1234567890' })} />,
    );

    expect(screen.getByText('abcdef12')).toBeInTheDocument();
  });

  it('names the workspace rather than showing its id', () => {
    // A job payload carries `workspace_id`, so the raw value used to reach the
    // card: `eb6e03d3` on screen where the person reading it knows the thing as
    // "Acme". The name is a better answer and the id is the fallback, not the
    // other way round.
    render(
      <AnalysisMetadataCard
        data={metadata({ workspaceId: 'abcdef12-3456-7890-abcd-ef1234567890' })}
        workspaceName="Acme"
      />,
    );

    expect(screen.getByText('Acme')).toBeInTheDocument();
    expect(screen.queryByText('abcdef12')).not.toBeInTheDocument();
  });

  it('falls back to the short id when no name is known yet', () => {
    // A store that has not hydrated has no name, and an empty row would be a
    // worse answer than the identifier it replaces.
    render(
      <AnalysisMetadataCard
        data={metadata({ workspaceId: 'abcdef12-3456-7890-abcd-ef1234567890' })}
        workspaceName={null}
      />,
    );

    expect(screen.getByText('abcdef12')).toBeInTheDocument();
  });

  it('groups the twelve rows under their three sections', () => {
    render(<AnalysisMetadataCard data={metadata()} />);

    expect(screen.getByRole('region', { name: 'Source' })).toBeInTheDocument();
    expect(screen.getByRole('region', { name: 'Code' })).toBeInTheDocument();
    expect(screen.getByRole('region', { name: 'Run' })).toBeInTheDocument();
  });

  it('renders the whole-card skeleton when loading', () => {
    // Unchanged behaviour, pinned so the per-field placeholders do not replace
    // it: a loading job has no fields at all, which is different again.
    const { container } = render(<AnalysisMetadataCard data={metadata()} isLoading />);

    expect(container.querySelectorAll('.animate-shimmer').length).toBeGreaterThan(0);
    expect(screen.queryByText('—')).not.toBeInTheDocument();
  });
});

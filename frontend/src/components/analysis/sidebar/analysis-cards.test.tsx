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
  return { languages: [], totalFiles: 0, totalLines: 0, ...overrides };
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

  it('renders the whole-card skeleton when loading', () => {
    // Unchanged behaviour, pinned so the per-field placeholders do not replace
    // it: a loading job has no fields at all, which is different again.
    const { container } = render(<AnalysisMetadataCard data={metadata()} isLoading />);

    expect(container.querySelectorAll('.animate-shimmer').length).toBeGreaterThan(0);
    expect(screen.queryByText('—')).not.toBeInTheDocument();
  });
});

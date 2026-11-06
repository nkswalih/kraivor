'use client';

import { Component, type ReactNode } from 'react';
import { Button } from '@/components/ui/shadcn';

interface Props {
  /** Label used in the fallback copy, e.g. "AI Providers". */
  section: string;
  /**
   * Applied to the wrapper around a healthy child.
   *
   * A boundary inserts a node between the host and the view, and hosts are
   * usually flex columns whose children size themselves with `flex-1`. Without
   * this the inserted node is a plain block, `flex-1` on the view resolves
   * against nothing, and the section sizes to its content inside a clipped
   * container. Pass the host's own flex classes to continue that layout
   * through the boundary.
   */
  className?: string;
  children: ReactNode;
}

interface State {
  hasError: boolean;
  message: string;
  /** Bumped on retry so the child remounts and re-runs its effects. */
  attempt: number;
}

/**
 * Keeps one broken section from taking down the panel that hosts it.
 *
 * Both large panels -- Settings and Inbox -- mount a body whose content is a
 * lazily imported view fetching its own data, so it can throw on a payload we
 * did not expect. Without a boundary the throw propagates through the dialog
 * and into the topbar, and the whole workspace chrome blanks rather than one
 * pane. Inside it, the failure degrades to the section body alone: the nav
 * rail stays usable, so the user can switch away, or retry this one.
 *
 * Lives in `ui/` rather than under either panel because it is deliberately
 * shared -- the failure mode is a property of "a section that lazy-loads", not
 * of any particular section.
 */
export class SectionErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, message: '', attempt: 0 };

  static getDerivedStateFromError(error: Error): Partial<State> {
    return { hasError: true, message: error.message };
  }

  componentDidCatch(error: Error) {
    console.error(`Section "${this.props.section}" crashed:`, error);
  }

  private retry = () => {
    this.setState(s => ({ hasError: false, message: '', attempt: s.attempt + 1 }));
  };

  render() {
    if (!this.state.hasError) {
      /* Keyed on attempt so retry remounts the view rather than reusing the
         crashed tree. */
      return (
        <div key={this.state.attempt} className={this.props.className}>
          {this.props.children}
        </div>
      );
    }

    return (
      <div className="flex min-h-[320px] flex-1 flex-col items-center justify-center gap-4 text-center px-6">
        <div className="space-y-2">
          <h3 className="text-base font-semibold text-text-primary">
            {this.props.section} hit an error
          </h3>
          <p className="text-sm text-text-secondary max-w-[380px]">
            {this.state.message || 'Something went wrong loading this section.'}
          </p>
        </div>
        <Button variant="outline" onClick={this.retry}>
          Try again
        </Button>
      </div>
    );
  }
}

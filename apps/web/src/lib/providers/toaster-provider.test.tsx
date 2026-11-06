import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { toast } from 'sonner';
import { ToasterProvider } from './toaster-provider';

/**
 * Sonner's imperative `toast()` API needs a `<Toaster />` somewhere in the
 * tree. Without one, the calls are silently discarded -- they do not throw and
 * they do not warn, they simply render nothing.
 *
 * This app had 27 such call sites across 13 files and no `<Toaster />`:
 *
 *   app/(marketing)/profile/[slug]/edit/page.tsx
 *   app/(dashboard)/[workspace]/analysis/page.tsx
 *   app/(dashboard)/[workspace]/analysis/jobs/[jobId]/page.tsx
 *   app/(dashboard)/[workspace]/analysis/jobs/[jobId]/guide/page.tsx
 *   components/profiles/profile-header.tsx
 *   components/profiles/create-profile-dialog.tsx
 *   components/analysis/enterprise-guide/AiExecutiveSummarySection.tsx
 *   components/community/share-dialog.tsx
 *   components/features/inbox-popover.tsx (superseded by the inbox panel)
 *
 * So a failed profile update, a failed analysis delete and a failed reanalysis
 * all completed without a word to the user. The mount point was the bug; these
 * tests exist so it cannot be deleted again silently.
 *
 * Two things about sonner's DOM shape, both learned the hard way:
 *   - it renders into a portal on document.body, so assertions query
 *     `document`, not the render container;
 *   - the <ol> is only mounted once at least one toast exists, so every
 *     container assertion has to raise a toast first.
 */

const toaster = () => document.querySelector('[data-sonner-toaster]');

async function renderWithToast(props = {}) {
  render(<ToasterProvider {...props} />);
  toast('probe');
  await waitFor(() => expect(toaster()).toBeInTheDocument());
  return toaster()!;
}

describe('ToasterProvider', () => {
  it('mounts the toast container once a toast is raised', async () => {
    render(<ToasterProvider />);

    expect(toaster()).toBeNull(); // nothing to show yet

    toast.success('Profile updated successfully');

    await waitFor(() => expect(toaster()).toBeInTheDocument());
  });

  it('displays a toast raised from anywhere in the app', async () => {
    render(<ToasterProvider />);

    toast.success('Profile updated successfully');

    await waitFor(() => {
      expect(screen.getByText('Profile updated successfully')).toBeInTheDocument();
    });
  });

  it('displays error toasts, not just successes', async () => {
    render(<ToasterProvider />);

    toast.error('Failed to update profile');

    await waitFor(() => {
      expect(screen.getByText('Failed to update profile')).toBeInTheDocument();
    });
  });

  it('keeps concurrent toasts distinguishable', async () => {
    render(<ToasterProvider />);

    toast.success('Analysis deleted');
    toast.error('Failed to delete analysis');

    await waitFor(() => {
      expect(screen.getByText('Analysis deleted')).toBeInTheDocument();
      expect(screen.getByText('Failed to delete analysis')).toBeInTheDocument();
    });
  });

  it('defaults to the bottom-right corner', async () => {
    const el = await renderWithToast();

    expect(el).toHaveAttribute('data-x-position', 'right');
    expect(el).toHaveAttribute('data-y-position', 'bottom');
  });

  it('passes props through to sonner', async () => {
    const el = await renderWithToast({ position: 'top-center' });

    expect(el).toHaveAttribute('data-y-position', 'top');
  });

  it('follows the resolved theme rather than hardcoding one', async () => {
    const el = await renderWithToast();

    // The next-themes mock below reports 'dark'.
    expect(el).toHaveAttribute('data-theme', 'dark');
  });

  it('leaves richColors off so the design tokens are not overridden', async () => {
    await renderWithToast();

    // richColors replaces the surface with sonner's stock green/red via
    // [data-rich-colors=true]; the Venom Yellow palette comes from the
    // --normal-* custom properties in globals.css instead.
    expect(document.querySelector('[data-rich-colors="true"]')).toBeNull();
  });
});

describe('toast() with no Toaster mounted', () => {
  it('is a silent no-op, which is why the mount point matters', () => {
    // Deliberately no render(). Documents the exact failure mode the provider
    // fixes: the call does not throw and does not warn, it just disappears.
    expect(() => toast.error('nobody is listening')).not.toThrow();
    expect(screen.queryByText('nobody is listening')).not.toBeInTheDocument();
  });
});

vi.mock('next-themes', () => ({
  useTheme: () => ({ resolvedTheme: 'dark', theme: 'dark', setTheme: vi.fn() }),
}));
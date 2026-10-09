import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { SettingsSidebar } from './settings-sidebar';
import { SettingsRouteGate } from './settings-route-gate';
import { SETTINGS_SECTIONS } from './settings-sections';
import { useSettingsDialogStore } from '@/lib/stores/settings-dialog-store';

/**
 * Settings stopped being a page in this change, and the parts that rot when
 * that happens are not the panel -- they are the two ends of it.
 *
 * The rail used to work out its own list from `navCategories` and its active
 * item from the pathname. Both were wrong the moment the panel opened over a
 * page: the pathname belongs to the page underneath, and the local list could
 * drift from what the dialog would actually render. So these pin that the rail
 * reads the shared registry, that a click hands the section to the store
 * instead of navigating, and that the href survives for copy-link.
 *
 * The gate is the other end: it is all a pasted `/{workspace}/settings/members`
 * URL amounts to now, so it had better open the right section.
 */
describe('settings dialog store', () => {
  beforeEach(() => {
    useSettingsDialogStore.getState().close();
  });

  it('opens on Preferences when no section is named', () => {
    useSettingsDialogStore.getState().open();
    expect(useSettingsDialogStore.getState().section).toBe('preferences');
  });

  it('treats a null section as closed, so there is no boolean to keep in step', () => {
    expect(useSettingsDialogStore.getState().section).toBeNull();
    useSettingsDialogStore.getState().open('members');
    useSettingsDialogStore.getState().close();
    expect(useSettingsDialogStore.getState().section).toBeNull();
  });
});

describe('SettingsSidebar', () => {
  beforeEach(() => {
    useSettingsDialogStore.getState().close();
  });

  it('renders every section in the registry, grouped', () => {
    render(
      <SettingsSidebar workspaceSlug="acme" active="preferences" onSelect={() => {}} />
    );

    for (const section of SETTINGS_SECTIONS) {
      expect(screen.getByRole('link', { name: new RegExp(section.label) })).toBeInTheDocument();
    }
  });

  it('marks the active section, not whatever page is underneath', () => {
    render(<SettingsSidebar workspaceSlug="acme" active="members" onSelect={() => {}} />);

    expect(screen.getByRole('link', { name: /Members/ })).toHaveAttribute(
      'aria-current',
      'page'
    );
    expect(screen.getByRole('link', { name: /Preferences/ })).not.toHaveAttribute(
      'aria-current'
    );
  });

  it('hands the section to the caller instead of navigating', () => {
    const onSelect = vi.fn();
    render(<SettingsSidebar workspaceSlug="acme" active="preferences" onSelect={onSelect} />);

    fireEvent.click(screen.getByRole('link', { name: /Security & Keys/ }));
    expect(onSelect).toHaveBeenCalledWith('security');
  });

  it('keeps the real href so the item can still be copied or opened in a tab', () => {
    render(
      <SettingsSidebar workspaceSlug="acme" active="preferences" onSelect={() => {}} />
    );

    expect(screen.getByRole('link', { name: /AI Providers/ })).toHaveAttribute(
      'href',
      '/acme/settings/ai-providers'
    );
  });

  it('filters the rail as you type, and says so when nothing matches', () => {
    render(<SettingsSidebar workspaceSlug="acme" active="preferences" onSelect={() => {}} />);

    fireEvent.change(screen.getByLabelText('Search settings'), {
      target: { value: 'member' },
    });
    expect(screen.getByRole('link', { name: /Members/ })).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: /Billing/ })).not.toBeInTheDocument();

    fireEvent.change(screen.getByLabelText('Search settings'), {
      target: { value: 'zzz' },
    });
    expect(screen.getByText(/No settings match/)).toBeInTheDocument();
  });
});

describe('SettingsRouteGate', () => {
  beforeEach(() => {
    useSettingsDialogStore.getState().close();
  });

  it('opens the panel on its own section and renders nothing itself', () => {
    const { container } = render(<SettingsRouteGate section="members" />);

    expect(useSettingsDialogStore.getState().section).toBe('members');
    expect(container).toBeEmptyDOMElement();
  });
});

'use client';

import { useTheme } from 'next-themes';
import { Toaster as Sonner, type ToasterProps } from 'sonner';

/**
 * Mount point for every `toast.*` call in the app.
 *
 * Sonner's imperative `toast()` API dispatches to a `<Toaster />` rendered
 * somewhere in the tree. With no `<Toaster />` mounted the calls resolve to
 * nothing: they do not throw, do not warn, and render nothing. The app had 27
 * such call sites across 13 files, so profile edits, analysis deletion,
 * reanalysis, invite acceptance, clipboard copies and share actions all
 * completed with no confirmation and -- more damagingly -- reported no error
 * when they failed.
 *
 * `richColors` is deliberately off: it would override the Venom Yellow palette
 * with sonner's stock green/red. The surface colours come from the design
 * tokens via `--normal-*` in globals.css instead.
 */
export function ToasterProvider(props: ToasterProps) {
  const { resolvedTheme } = useTheme();

  return (
    <Sonner
      theme={resolvedTheme as ToasterProps['theme']}
      position="bottom-right"
      closeButton
      {...props}
    />
  );
}
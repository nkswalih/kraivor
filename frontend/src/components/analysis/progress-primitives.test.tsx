import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { render, screen } from '@testing-library/react';
import { ProgressBar } from './progress-bar';
import { ProgressRing } from './progress-ring';

/**
 * These two components are the only places in the analysis UI that draw their
 * own colour rather than inheriting one, so they are the two places a hardcoded
 * value can hide. The assertions read the rendered output for the literal
 * absence of hex, and the config for the keys that make the tokens reachable.
 *
 * The scale colours are deliberately Tailwind palette classes rather than hex:
 * the ring is an SVG, and `stroke="currentColor"` is the only way to let a
 * class drive it, which is worth pinning so nobody re-introduces a hex to "fix"
 * a band.
 */

const TAILWIND_CONFIG = readFileSync(
  join(process.cwd(), 'tailwind.config.ts'),
  'utf8',
);

/** Every `#rgb`, `#rrggbb` or `#rrggbbaa` literal in some source text. */
function hexLiterals(source: string): string[] {
  return source.match(/#[0-9a-fA-F]{3,8}\b/g) ?? [];
}

// ======================================================================
// ProgressBar
// ======================================================================

describe('ProgressBar', () => {
  it('fills from the brand tokens rather than a literal gradient', () => {
    const { container } = render(<ProgressBar pct={50} />);

    const fill = container.querySelector<HTMLElement>('.h-full');
    expect(fill?.style.background).toContain('var(--venom-yellow)');
    expect(fill?.style.background).toContain('var(--venom-amber)');
  });

  it('carries no hex literal', () => {
    const { container } = render(<ProgressBar pct={50} />);

    expect(hexLiterals(container.innerHTML)).toEqual([]);
  });

  it('shows the message and the rounded percentage together', () => {
    render(<ProgressBar pct={42.4} message="Parsing files" />);

    expect(screen.getByText('Parsing files')).toBeInTheDocument();
    expect(screen.getByText('42%')).toBeInTheDocument();
  });

  it('clamps above 100 so the bar cannot overflow its track', () => {
    const { container } = render(<ProgressBar pct={140} message="x" />);

    expect(screen.getByText('100%')).toBeInTheDocument();
    expect(container.querySelector<HTMLElement>('.h-full')?.style.width).toBe(
      '100%',
    );
  });

  it('clamps a negative percentage to nothing rather than inverting', () => {
    const { container } = render(<ProgressBar pct={-20} message="x" />);

    expect(screen.getByText('0%')).toBeInTheDocument();
    expect(container.querySelector<HTMLElement>('.h-full')?.style.width).toBe('0%');
  });

  it('omits the percentage when there is no message to attach it to', () => {
    // The old shape put both in one block, so a bare bar had no readout. The
    // caller that wants a number without a message can still pass an empty one,
    // but the default is a bar and nothing else.
    render(<ProgressBar pct={50} />);

    expect(screen.queryByText('50%')).not.toBeInTheDocument();
  });

  // ----------------------------------------------------------------
  // The value has to be readable without seeing it.
  //
  // Before these attributes the bar was two unlabelled divs with a CSS width on
  // one of them. The eye got a fill and a number; a screen reader got nothing --
  // no role, so not even a progress indicator. All three callers are affected,
  // which is why the fix is here rather than in each panel.
  // ----------------------------------------------------------------
  describe('as an accessible value', () => {
    it('exposes the percentage as a progressbar', () => {
      render(<ProgressBar pct={62} message="Scanning files" />);

      const bar = screen.getByRole('progressbar');

      expect(bar.getAttribute('aria-valuenow')).toBe('62');
      expect(bar.getAttribute('aria-valuemin')).toBe('0');
      expect(bar.getAttribute('aria-valuemax')).toBe('100');
    });

    it('spells the value out with its unit rather than leaving a bare integer', () => {
      // `aria-valuenow` is announced as "62". `aria-valuetext` is what says
      // "62 percent", and without it there is no way to tell 62 of 100 from 62
      // of 1000 -- the denominator is a separate attribute a reader may not pair
      // with the number.
      render(<ProgressBar pct={62} message="Scanning files" />);

      expect(screen.getByRole('progressbar').getAttribute('aria-valuetext')).toBe('62%');
    });

    it('takes its accessible name from the message by default', () => {
      // "62%" alone is a number with nothing saying 62 of what. Every caller
      // already passes a message describing the work, so defaulting to it means
      // the bar is never announced unlabelled without any caller having to know
      // the attribute exists.
      render(<ProgressBar pct={62} message="Scanning files" />);

      expect(screen.getByRole('progressbar', { name: 'Scanning files' })).toBeTruthy();
    });

    it('lets an explicit label win over the message', () => {
      render(<ProgressBar pct={62} message="Scanning files" label="Analysis progress" />);

      expect(screen.getByRole('progressbar', { name: 'Analysis progress' })).toBeTruthy();
      expect(screen.queryByRole('progressbar', { name: 'Scanning files' })).toBeNull();
    });

    it('reports the clamped value, so the announced number matches the drawn bar', () => {
      // The fill is clamped, and the exposed value has to be clamped with it.
      // Exposing the raw 140 next to a bar drawn at 100% would put two
      // different numbers in front of the reader for the same object.
      render(<ProgressBar pct={140} message="x" />);

      const bar = screen.getByRole('progressbar');

      expect(bar.getAttribute('aria-valuenow')).toBe('100');
      expect(bar.getAttribute('aria-valuetext')).toBe('100%');
    });

    it('rounds the exposed value the same way it rounds the visible one', () => {
      // The label row has always said `42%` for 42.4. Announcing `42.4` while
      // the page shows `42%` is the same value stated two ways.
      render(<ProgressBar pct={42.4} message="Parsing files" />);

      expect(screen.getByRole('progressbar').getAttribute('aria-valuenow')).toBe('42');
    });

    it('leaves the bar unlabelled rather than inventing a name when given none', () => {
      // There is no honest default to invent here -- "Progress" would be a
      // guess about what is being measured. A caller that wants a name passes
      // one; this test exists so a future default is a deliberate choice.
      render(<ProgressBar pct={50} />);

      expect(screen.getByRole('progressbar')).toBeTruthy();
      expect(screen.getByRole('progressbar').getAttribute('aria-label')).toBeNull();
    });
  });
});

// ======================================================================
// ProgressRing
// ======================================================================

describe('ProgressRing', () => {
  it('draws the track with a usable colour', () => {
    // `hsl(var(--krait-border))` was the old value. `--krait-border` is a hex,
    // and `hsl()` needs three bare numbers, so the declaration was invalid --
    // the browser dropped the stroke and the track behind the arc was never
    // visible. Any wrapper that turns a CSS custom property into a colour
    // function has to be checked against what the property actually holds.
    const { container } = render(<ProgressRing score={70} />);

    const track = container.querySelector('circle');
    expect(track?.getAttribute('stroke')).toBe('var(--krait-border)');
  });

  it('paints the arc from the current text colour', () => {
    // Which is what lets a palette class drive an SVG stroke. Two circles, so
    // the arc is the second one.
    const { container } = render(<ProgressRing score={70} />);
    const circles = container.querySelectorAll('circle');

    expect(circles).toHaveLength(2);
    expect(circles[1].getAttribute('stroke')).toBe('currentColor');
  });

  it.each([
    [95, 'text-green-500'],
    [90, 'text-green-500'],
    [89, 'text-blue-500'],
    [75, 'text-blue-500'],
    [74, 'text-yellow-500'],
    [60, 'text-yellow-500'],
    [59, 'text-orange-500'],
    [40, 'text-orange-500'],
    [39, 'text-red-500'],
    [0, 'text-red-500'],
  ])('scores %i into the %s band', (score, expected) => {
    const { container } = render(<ProgressRing score={score} />);

    expect(container.firstElementChild?.className).toContain(expected);
  });

  it('renders no band and no arc when there is no score', () => {
    // An unscored engine has nothing to colour, and giving it the worst band
    // would report a failing score that was never measured.
    const { container } = render(<ProgressRing score={null} />);

    expect(container.querySelectorAll('circle')).toHaveLength(1);
    expect(container.firstElementChild?.className).not.toContain('text-red-500');
    expect(screen.getByText('N/A')).toBeInTheDocument();
  });

  it('clamps a score above 100 to a full ring', () => {
    const { container } = render(<ProgressRing score={140} />);
    const arc = container.querySelectorAll('circle')[1];

    const circumference = Number(arc.getAttribute('stroke-dasharray'));
    const offset = Number(arc.getAttribute('stroke-dashoffset'));

    expect(offset).toBeCloseTo(0, 5);
    expect(circumference).toBeGreaterThan(0);
  });

  it('renders an empty ring for a negative score rather than inverting it', () => {
    const { container } = render(<ProgressRing score={-10} />);
    const arc = container.querySelectorAll('circle')[1];

    const circumference = Number(arc.getAttribute('stroke-dasharray'));
    const offset = Number(arc.getAttribute('stroke-dashoffset'));

    expect(offset).toBeCloseTo(circumference, 5);
  });

  it('renders the label when given one', () => {
    render(<ProgressRing score={80} label="Security" />);

    expect(screen.getByText('Security')).toBeInTheDocument();
  });

  it('omits the label element when there is no label', () => {
    const { container } = render(<ProgressRing score={80} />);

    expect(container.querySelectorAll('span')).toHaveLength(1);
  });
});

// ======================================================================
// The tokens both components depend on
// ======================================================================

describe('the tokens these components reference', () => {
  it('exposes the semantic status colours as Tailwind keys', () => {
    // Fifteen call sites write the short spelling -- `text-color-error` and
    // friends. Without these keys Tailwind cannot generate a class by that
    // name, so those error banners and score colours were silently rendering in
    // the inherited text colour. The arbitrary-value spelling
    // `text-[var(--color-error)]` that the rest of the app uses keeps working
    // either way; this makes the short form mean the same thing.
    for (const key of ['success', 'error', 'warning', 'info']) {
      expect(TAILWIND_CONFIG).toContain(`${key}:`);
      expect(TAILWIND_CONFIG).toContain(`var(--color-${key})`);
    }
  });

  it('points the status keys at the custom properties the themes define', () => {
    // Guards against a key being added that nothing defines, which would render
    // as transparent rather than as an error.
    const globals = readFileSync(
      join(process.cwd(), 'src/styles/globals.css'),
      'utf8',
    );

    for (const key of ['success', 'error', 'warning', 'info']) {
      const definitions = globals.match(
        new RegExp(`--color-${key}:`, 'g'),
      ) ?? [];
      // Once per theme.
      expect(definitions.length).toBe(2);
    }
  });

  it('keeps the venom tokens the progress gradient names', () => {
    for (const token of ['--venom-yellow', '--venom-amber']) {
      const globals = readFileSync(
        join(process.cwd(), 'src/styles/globals.css'),
        'utf8',
      );
      const definitions = globals.match(
        new RegExp(`${token}:`, 'g'),
      ) ?? [];
      expect(definitions.length).toBe(2);
      expect(TAILWIND_CONFIG).toContain(`'var(${token})'`);
    }
  });

  it('defines --krait-border as a hex, which is why it is used bare', () => {
    // The one custom property these components pass straight to a colour
    // function. Documented here because the mistake it guards against -- wrapping
    // it in `hsl()` -- produced an invisible track and would look like a styling
    // preference rather than a bug.
    const globals = readFileSync(
      join(process.cwd(), 'src/styles/globals.css'),
      'utf8',
    );

    const values = globals.match(/--krait-border:\s*([^;]+);/g) ?? [];
    expect(values.length).toBe(2);
    for (const value of values) {
      expect(value).toMatch(/#/);
    }
  });
});

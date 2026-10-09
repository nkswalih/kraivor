import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { AiProvidersView } from './ai-providers-view';
import { SectionErrorBoundary } from '@/components/ui/section-error-boundary';

/**
 * The panel rendered this view straight off `/api/ai/v1/byok/models` and read
 * `model.providers` as a `string[]`. The server sends `available_providers` as
 * a list of *objects* and the current choice as `selected_provider`, so the
 * value was `undefined` and `.map` threw -- which, unbounded, blanked the
 * whole workspace chrome rather than just this section.
 *
 * These pin both ends of the fix: the response is normalized on the way in,
 * and if a section still throws, the damage stops at the section body.
 */

const RAW_MODELS = {
  models: [
    {
      model_id: 'claude-sonnet-5',
      model_name: 'Claude Sonnet 5',
      backend_model: 'claude-sonnet-5',
      available_providers: [
        { provider: 'anthropic', name: 'Anthropic', default_base_url: 'https://api.anthropic.com' },
        { provider: 'openrouter', name: 'OpenRouter', default_base_url: 'https://openrouter.ai/api' },
      ],
      selected_provider: 'openrouter',
      has_key: true,
    },
    /* A model the server has not filled in yet -- the shape that used to throw. */
    { model_id: 'gpt-5.5' },
  ],
};

const RAW_PROVIDERS = {
  /* `provider` carries the id and `name` the display label. */
  providers: [
    {
      provider: 'anthropic',
      name: 'Anthropic',
      has_key: true,
      model_count: 4,
      models: ['claude-sonnet-5'],
      custom_url: null,
      last_validated: '2026-01-01T00:00:00Z',
    },
    { provider: 'openai', name: 'OpenAI', has_key: false, model_count: 3, models: [] },
  ],
};

function mockApi() {
  const fetchMock = vi.fn((url: string) => {
    const body = String(url).includes('/byok/models') ? RAW_MODELS : RAW_PROVIDERS;
    return Promise.resolve({
      ok: true,
      json: () => Promise.resolve(body),
    } as Response);
  });
  vi.stubGlobal('fetch', fetchMock);
  return fetchMock;
}

describe('AiProvidersView', () => {
  beforeEach(() => {
    vi.unstubAllGlobals();
    mockApi();
  });

  it('renders a model whose payload is only partly filled in', async () => {
    render(<AiProvidersView />);

    await waitFor(() => {
      expect(screen.getByText('Model Routing')).toBeInTheDocument();
    });

    expect(screen.getByText('Claude Sonnet 5')).toBeInTheDocument();
    /* MODEL_DISPLAY_NAMES titles it, but the row must exist at all. */
    expect(screen.getByText('GPT-5.5')).toBeInTheDocument();
    /* No available_providers -> say so rather than an empty <select>. */
    expect(screen.getByText('No providers')).toBeInTheDocument();
  });

  it('maps available_providers to option ids so the current choice is selected', async () => {
    const { container } = render(<AiProvidersView />);

    await waitFor(() => {
      expect(container.querySelectorAll('select option')).not.toHaveLength(0);
    });

    const optionValues = Array.from(
      container.querySelectorAll('select option')
    ).map(o => o.getAttribute('value'));

    /* The ids come from the nested objects, not from their display names. */
    expect(optionValues).toContain('anthropic');
    expect(optionValues).toContain('openrouter');
    expect(optionValues).not.toContain('Anthropic');

    /* selected_provider is what the control should be sitting on. */
    const selects = Array.from(container.querySelectorAll('select'));
    expect(selects.map(s => s.value)).toContain('openrouter');
  });

  it('shows a saved key against the provider id, not the display label', async () => {
    render(<AiProvidersView />);

    /* anthropic has_key: true, openai has_key: false. */
    await waitFor(() => {
      expect(screen.getAllByText('Active').length).toBeGreaterThan(0);
    });
    expect(screen.getAllByText('Active').length).toBe(1);
  });
});

describe('SectionErrorBoundary', () => {
  function Boom(): never {
    throw new Error('payload shape changed');
  }

  it('contains a crash to the section body instead of the panel', () => {
    const spy = vi.spyOn(console, 'error').mockImplementation(() => {});

    const { container } = render(
      <SectionErrorBoundary section="AI Providers">
        <Boom />
      </SectionErrorBoundary>
    );

    expect(container.textContent).toContain('AI Providers hit an error');
    expect(container.textContent).toContain('payload shape changed');
    spy.mockRestore();
  });

  it('re-renders the child on retry', () => {
    const spy = vi.spyOn(console, 'error').mockImplementation(() => {});
    let shouldThrow = true;

    function Flaky(): React.JSX.Element {
      if (shouldThrow) throw new Error('first render failed');
      return <p>recovered</p>;
    }

    render(
      <SectionErrorBoundary section="Members">
        <Flaky />
      </SectionErrorBoundary>
    );
    expect(screen.getByText(/hit an error/)).toBeInTheDocument();

    shouldThrow = false;
    fireEvent.click(screen.getByRole('button', { name: /Try again/ }));

    expect(screen.getByText('recovered')).toBeInTheDocument();
    spy.mockRestore();
  });
});

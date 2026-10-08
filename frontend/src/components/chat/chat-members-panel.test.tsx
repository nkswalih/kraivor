import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen, cleanup } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MembersPanel } from './chat-members-panel';

/**
 * The members rail used to be one flat list with a trailing status dot.
 * It now reads the way a presence list should: "Online — N" / "Offline — N"
 * sections with counts, the green dot attached to the avatar itself, and
 * offline members dimmed into the background instead of carrying a grey
 * placeholder dot of their own.
 */

const { MEMBERS } = vi.hoisted(() => ({
  MEMBERS: [
    {
      id: 'm1',
      user_id: 'u1',
      role: 'owner',
      status: 'active',
      joined_at: null,
      invited_by_id: null,
      created_at: '',
      updated_at: '',
      user: { id: 'u1', name: 'Lad.exe', email: 'lad@x.dev' },
    },
    {
      id: 'm2',
      user_id: 'u2',
      role: 'member',
      status: 'active',
      joined_at: null,
      invited_by_id: null,
      created_at: '',
      updated_at: '',
      user: { id: 'u2', name: 'Abhijith Krishna', email: 'abhi@x.dev' },
    },
    {
      id: 'm3',
      user_id: 'u3',
      role: 'member',
      status: 'active',
      joined_at: null,
      invited_by_id: null,
      created_at: '',
      updated_at: '',
      user: { id: 'u3', name: 'Abhinav', email: 'abhinav@x.dev' },
    },
  ],
}));

vi.mock('@/lib/api/endpoints', () => ({
  workspaceEndpoints: {
    getMembers: vi.fn().mockResolvedValue(MEMBERS),
  },
  profileEndpoints: {
    getProfilesByIds: vi.fn().mockResolvedValue({ profiles: {} }),
  },
}));

function renderPanel(onlineUserIds: Set<string>) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <MembersPanel workspaceId="ws-1" onlineUserIds={onlineUserIds} />
    </QueryClientProvider>
  );
}

function rowFor(name: string) {
  return screen.getByText(name).closest('div[title]');
}

afterEach(cleanup);

describe('MembersPanel presence sections', () => {
  it('splits members into Online and Offline sections with counts', async () => {
    renderPanel(new Set(['u1']));

    expect(await screen.findByText('Online — 1')).toBeInTheDocument();
    expect(screen.getByText('Offline — 2')).toBeInTheDocument();
    // Names land under their section, online first.
    expect(screen.getByText('Lad.exe')).toBeInTheDocument();
    expect(screen.getByText('Abhijith Krishna')).toBeInTheDocument();
    expect(screen.getByText('Abhinav')).toBeInTheDocument();
  });

  it('attaches the presence dot to the avatar, online members only', async () => {
    renderPanel(new Set(['u1']));

    await screen.findByText('Lad.exe');
    // Exactly one dot across the whole rail — the online member's.
    const dots = screen.getAllByLabelText('Online');
    expect(dots).toHaveLength(1);
    expect(rowFor('Lad.exe')).toContainElement(dots[0] as HTMLElement);
    expect(rowFor('Abhijith Krishna')).not.toContainElement(
      screen.queryByLabelText('Online') as HTMLElement
    );
  });

  it('dims offline rows and leaves online rows at full strength', async () => {
    renderPanel(new Set(['u1']));

    await screen.findByText('Abhinav');
    expect(rowFor('Lad.exe')?.className).not.toContain('opacity-40');
    expect(rowFor('Abhijith Krishna')?.className).toContain('opacity-40');
    expect(rowFor('Abhinav')?.className).toContain('opacity-40');
  });
});

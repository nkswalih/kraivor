'use client';

import { useState } from 'react';
import { X } from 'lucide-react';
import { useCommunityStore } from '@/lib/stores/community-store';
import { useCreateDiscussion } from '@/lib/hooks/use-community';
import { useAuthStore } from '@/lib/stores/auth-store';
import { useMyProfile } from '@/lib/hooks/use-profiles';

export function CreateDialog() {
  const open = useCommunityStore(s => s.createDialogOpen);
  const setOpen = useCommunityStore(s => s.setCreateDialogOpen);
  const user = useAuthStore(s => s.user);
  const { data: myProfile } = useMyProfile();
  const mutation = useCreateDiscussion();

  const [title, setTitle] = useState('');
  const [body, setBody] = useState('');
  const [tags, setTags] = useState('');

  if (!open) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim() || !body.trim()) return;

    await mutation.mutateAsync({
      title: title.trim(),
      body: body.trim(),
      tags: tags
        .split(',')
        .map(t => t.trim())
        .filter(Boolean),
      author_username: myProfile?.username ?? user?.email?.split('@')[0] ?? 'anonymous',
      author_display_name:
        myProfile?.display_name ?? user?.name ?? user?.email?.split('@')[0] ?? 'Anonymous',
      author_avatar_url: myProfile?.avatar_url ?? user?.avatar_url ?? '',
    });

    setTitle('');
    setBody('');
    setTags('');
    setOpen(false);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-card border border-border rounded-lg w-full max-w-lg mx-4 p-6 animate-fade-up">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-medium text-foreground">New Discussion</h2>
          <button
            onClick={() => setOpen(false)}
            className="text-muted-foreground hover:text-foreground"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <input
            type="text"
            placeholder="Title"
            value={title}
            onChange={e => setTitle(e.target.value)}
            className="w-full bg-background border border-border rounded-md px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-primary"
            required
            minLength={10}
          />

          <textarea
            placeholder="What's on your mind?"
            value={body}
            onChange={e => setBody(e.target.value)}
            rows={5}
            className="w-full bg-background border border-border rounded-md px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-primary resize-none"
            required
            minLength={20}
          />

          <input
            type="text"
            placeholder="Tags (comma separated)"
            value={tags}
            onChange={e => setTags(e.target.value)}
            className="w-full bg-background border border-border rounded-md px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-primary"
          />

          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={() => setOpen(false)}
              className="px-4 py-2 text-sm text-muted-foreground hover:text-foreground border border-border rounded-md"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={mutation.isPending}
              className="btn-shimmer text-primary-foreground text-sm font-medium px-4 py-2 rounded-md disabled:opacity-50"
            >
              {mutation.isPending ? 'Posting...' : 'Post Discussion'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

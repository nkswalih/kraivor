'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { X, Hash, Loader2 } from 'lucide-react';
import { chatEndpoints } from '@/lib/api/endpoints';

interface CreateChannelDialogProps {
  workspaceId: string;
  workspaceSlug: string;
  open: boolean;
  onClose: () => void;
}

export function CreateChannelDialog({
  workspaceId,
  workspaceSlug,
  open,
  onClose,
}: CreateChannelDialogProps) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [name, setName] = useState('');
  const [topic, setTopic] = useState('');
  const [error, setError] = useState('');

  const mutation = useMutation({
    mutationFn: () =>
      chatEndpoints.createRoom(workspaceId, {
        name: name.trim().toLowerCase().replace(/\s+/g, '-'),
        room_type: 'workspace',
        topic: topic.trim() || undefined,
      }),
    onSuccess: room => {
      queryClient.invalidateQueries({ queryKey: ['rooms', workspaceId] });
      setName('');
      setTopic('');
      setError('');
      onClose();
      router.push(`/${workspaceSlug}/chat/${room.id}`);
    },
    onError: (err: any) => {
      setError(err?.message || 'Failed to create channel');
    },
  });

  if (!open) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    if (!name.trim()) {
      setError('Channel name is required');
      return;
    }
    mutation.mutate();
  };

  const channelName = name.trim().toLowerCase().replace(/\s+/g, '-') || 'name';

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
      onMouseDown={e => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="w-full max-w-md bg-[#141416] border border-[#27272A] rounded-xl shadow-2xl animate-scale-in">
        <div className="flex items-center justify-between px-5 py-3.5 border-b border-[#27272A]">
          <h2 className="text-[15px] font-semibold text-[#FAFAFA] flex items-center gap-2">
            <Hash className="w-4 h-4 text-venom-yellow" /> Create Channel
          </h2>
          <button
            onClick={onClose}
            className="p-1 text-text-tertiary hover:text-[#FAFAFA] transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-5 space-y-4">
          <div>
            <label className="block text-[12px] font-medium text-text-secondary mb-1.5">
              Channel name
            </label>
            <div className="flex items-center gap-1.5 px-3 py-2 bg-[#0A0A0B] border border-[#27272A] rounded-lg focus-within:border-venom-yellow/50 transition-colors">
              <Hash className="w-4 h-4 text-text-tertiary shrink-0" />
              <input
                value={name}
                onChange={e => setName(e.target.value)}
                placeholder="e.g. project-updates"
                className="flex-1 bg-transparent border-none text-[13px] text-[#FAFAFA] placeholder:text-text-tertiary focus:outline-none"
                autoFocus
              />
            </div>
            <p className="text-[11px] text-text-tertiary mt-1.5">
              Will be created as <span className="text-venom-yellow">#{channelName}</span>
            </p>
          </div>

          <div>
            <label className="block text-[12px] font-medium text-text-secondary mb-1.5">
              Topic <span className="text-text-tertiary">(optional)</span>
            </label>
            <input
              value={topic}
              onChange={e => setTopic(e.target.value)}
              placeholder="What's this channel about?"
              className="w-full px-3 py-2 bg-[#0A0A0B] border border-[#27272A] rounded-lg text-[13px] text-[#FAFAFA] placeholder:text-text-tertiary focus:outline-none focus:border-venom-yellow/50 transition-colors"
            />
          </div>

          {error && (
            <div className="px-3 py-2 bg-red-500/10 border border-red-500/20 rounded-lg text-[12px] text-red-400">
              {error}
            </div>
          )}

          <div className="flex justify-end gap-2 pt-1">
            <button
              type="button"
              onClick={onClose}
              className="px-3 py-1.5 text-[13px] text-text-secondary hover:text-[#FAFAFA] transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={mutation.isPending}
              className="px-4 py-1.5 bg-venom-yellow text-black text-[13px] font-medium rounded-lg hover:brightness-110 transition-all disabled:opacity-50 flex items-center gap-1.5"
            >
              {mutation.isPending ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <Hash className="w-3.5 h-3.5" />
              )}
              Create
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

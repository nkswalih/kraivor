'use client';

import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { X, GitBranch, Loader2 } from 'lucide-react';
import { repositoryEndpoints } from '@/lib/api/endpoints';
import { useAuthStore } from '@/lib/stores/auth-store';

interface ConnectRepoDialogProps {
  open: boolean;
  onClose: () => void;
}

export function ConnectRepoDialog({ open, onClose }: ConnectRepoDialogProps) {
  const workspaceId = useAuthStore(s => s.workspaceId);
  const queryClient = useQueryClient();
  const [repoUrl, setRepoUrl] = useState('');
  const [error, setError] = useState('');

  const mutation = useMutation({
    mutationFn: () => repositoryEndpoints.connect(workspaceId!, { github_repo: repoUrl }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['repos', workspaceId] });
      setRepoUrl('');
      setError('');
      onClose();
    },
    onError: (err: any) => {
      setError(err?.message || 'Failed to connect repository');
    },
  });

  if (!open) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    if (!repoUrl.trim()) {
      setError('Please enter a repository URL');
      return;
    }
    mutation.mutate();
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
      onMouseDown={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div className="w-full max-w-md bg-[#141416] border border-[#27272A] rounded-xl shadow-2xl animate-scale-in">
        <div className="flex items-center justify-between px-5 py-3.5 border-b border-[#27272A]">
          <h2 className="text-[15px] font-semibold text-[#FAFAFA] flex items-center gap-2">
            <GitBranch className="w-4 h-4 text-venom-yellow" /> Connect Repository
          </h2>
          <button onClick={onClose} className="p-1 text-text-tertiary hover:text-[#FAFAFA] transition-colors">
            <X className="w-4 h-4" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-5 space-y-4">
          <div>
            <label className="block text-[12px] font-medium text-text-secondary mb-1.5">
              GitHub Repository URL
            </label>
            <input
              value={repoUrl}
              onChange={(e) => setRepoUrl(e.target.value)}
              placeholder="e.g. owner/repo or https://github.com/owner/repo"
              className="w-full px-3 py-2 bg-[#0A0A0B] border border-[#27272A] rounded-lg text-[13px] text-[#FAFAFA] placeholder:text-text-tertiary focus:outline-none focus:border-venom-yellow/50 transition-colors"
              autoFocus
            />
            <p className="text-[11px] text-text-tertiary mt-1.5">
              Enter the full GitHub repository name or URL.
            </p>
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
              {mutation.isPending ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <GitBranch className="w-3.5 h-3.5" />}
              Connect
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

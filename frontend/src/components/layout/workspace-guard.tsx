'use client';

import { useEffect, useState, type ReactNode } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/lib/stores/auth-store';
import { CreateWorkspaceDialog } from '@/components/features/create-workspace-dialog';

export function WorkspaceGuard({ children }: { children: ReactNode }) {
  const router = useRouter();
  const { isAuthenticated, isLoading, workspaceId, workspaceSlug, workspaces, initWorkspace } = useAuthStore();
  const [showCreate, setShowCreate] = useState(false);
  const [checked, setChecked] = useState(false);

  useEffect(() => {
    if (isLoading || !isAuthenticated) return;
    if (checked) return;
    setChecked(true);

    if (!workspaceId && workspaces.length === 0) {
      setShowCreate(true);
    }
  }, [isAuthenticated, isLoading, workspaceId, workspaces, checked]);

  const handleCreated = (slug: string) => {
    setShowCreate(false);
    router.push(`/${slug}`);
  };

  const handleSkip = () => {
    setShowCreate(false);
    router.push('/');
  };

  if (showCreate) {
    return (
      <div className="flex h-screen w-full bg-[#0A0A0B] items-center justify-center">
        <div className="text-center">
          <div className="w-12 h-12 rounded-xl bg-venom-yellow/10 flex items-center justify-center mx-auto mb-4">
            <svg className="w-6 h-6 text-venom-yellow" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
            </svg>
          </div>
          <h1 className="text-xl font-semibold text-[#FAFAFA] mb-2">Welcome to Kraivor</h1>
          <p className="text-[14px] text-text-secondary mb-8 max-w-sm">
            You don&apos;t have any workspaces yet. Create one to get started.
          </p>

          <div className="flex flex-col items-center gap-3">
            <button
              onClick={() => setShowCreate(true)}
              className="px-6 py-2.5 bg-venom-yellow text-black text-[14px] font-medium rounded-lg hover:brightness-110 transition-all"
            >
              Create your first workspace
            </button>
            <button
              onClick={handleSkip}
              className="text-[13px] text-text-secondary hover:text-[#FAFAFA] transition-colors"
            >
              Skip for now
            </button>
          </div>
        </div>

        <CreateWorkspaceDialog
          open={showCreate}
          onClose={() => setShowCreate(false)}
          onCreated={handleCreated}
        />
      </div>
    );
  }

  return <>{children}</>;
}

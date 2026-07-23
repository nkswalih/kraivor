'use client';

import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/lib/stores/auth-store';
import { CreateWorkspaceDialog } from '@/components/features/create-workspace-dialog';

export default function NewWorkspacePage() {
  const router = useRouter();
  const { isAuthenticated, isLoading } = useAuthStore();

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center bg-[#0A0A0B]">
        <div className="w-5 h-5 border-2 border-venom-yellow border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!isAuthenticated) {
    router.replace('/login');
    return null;
  }

  const handleCreated = (slug: string) => {
    router.push(`/${slug}`);
  };

  return (
    <div className="flex h-screen w-full bg-[#0A0A0B] items-center justify-center animate-fade-up">
      <div className="text-center max-w-sm">
        <div className="w-12 h-12 rounded-xl bg-venom-yellow/10 flex items-center justify-center mx-auto mb-4">
          <svg
            className="w-6 h-6 text-venom-yellow"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"
            />
          </svg>
        </div>
        <h1 className="text-xl font-semibold text-[#FAFAFA] mb-2">Welcome to Kraivor</h1>
        <p className="text-[14px] text-text-secondary mb-8">
          You don&apos;t have any workspaces yet. Create one to get started.
        </p>

        <CreateWorkspaceDialog
          open={true}
          onClose={() => router.push('/')}
          onCreated={handleCreated}
        />
      </div>
    </div>
  );
}

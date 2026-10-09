'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/lib/stores/auth-store';
import { ROUTES } from '@/constants';

export function NavActions() {
  const { isAuthenticated, workspaceSlug } = useAuthStore();
  const router = useRouter();

  if (isAuthenticated) {
    return (
      <button
        onClick={() => {
          const slug = workspaceSlug || useAuthStore.getState().workspaceSlug;
          if (slug) {
            router.push(`/${slug}`);
          }
        }}
        className="inline-flex items-center rounded-xl bg-[var(--venom-yellow)] px-4 py-1.5 text-sm font-medium text-black transition-all hover:brightness-110"
      >
        Dashboard
      </button>
    );
  }

  return (
    <div className="flex items-center gap-3">
      <Link
        href={ROUTES.LOGIN}
        className="text-sm text-neutral-500 transition-colors hover:text-neutral-300"
      >
        Sign in
      </Link>
      <Link
        href={ROUTES.REGISTER}
        className="inline-flex items-center rounded-xl bg-[var(--venom-yellow)] px-4 py-1.5 text-sm font-medium text-black transition-all hover:brightness-110"
      >
        Get Started
      </Link>
    </div>
  );
}

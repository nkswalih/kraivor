'use client';

import Link from 'next/link';
import { useAuthStore } from '@/lib/stores/auth-store';
import { ROUTES } from '@/constants';

export function NavActions() {
  const { isAuthenticated, workspaceSlug } = useAuthStore();

  if (isAuthenticated) {
    return (
      <Link
        href={`/${workspaceSlug || 'dashboard'}`}
        className="inline-flex items-center rounded-xl bg-[var(--venom-yellow)] px-4 py-1.5 text-sm font-medium text-black transition-all hover:brightness-110"
      >
        Dashboard
      </Link>
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

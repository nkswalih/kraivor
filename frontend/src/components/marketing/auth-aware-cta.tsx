'use client';

import Link from 'next/link';
import { useAuthStore } from '@/stores/auth-stores';
import { ROUTES, DEFAULT_DASHBOARD_ROUTE } from '@/constants';
import { ArrowRight, Plus, GridFour } from '@phosphor-icons/react';

export function AuthAwareCTA() {
  const { user, isLoading } = useAuthStore();

  if (isLoading) {
    return (
      <div className="flex items-center gap-3">
        <div className="h-8 w-16 rounded-lg bg-[var(--krait-surface-1)] animate-pulse" />
        <div className="h-8 w-24 rounded-lg bg-[var(--krait-surface-1)] animate-pulse" />
      </div>
    );
  }

  if (user) {
    return (
      <Link
        href={DEFAULT_DASHBOARD_ROUTE}
        className="inline-flex items-center gap-2 rounded-xl bg-[var(--venom-yellow)] px-4 py-2 text-sm font-semibold text-black transition-all hover:brightness-110"
      >
        <GridFour size={16} weight="fill" />
        <span>Dashboard</span>
        <ArrowRight size={14} weight="bold" />
      </Link>
    );
  }

  return (
    <div className="flex items-center gap-3">
      <Link href={ROUTES.LOGIN} className="text-sm font-medium text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors">
        Sign in
      </Link>
      <Link
        href={ROUTES.REGISTER}
        className="inline-flex items-center gap-2 rounded-xl bg-[var(--venom-yellow)] px-4 py-2 text-sm font-semibold text-black transition-all hover:brightness-110"
      >
        <Plus size={16} weight="bold" />
        <span>Get Started</span>
      </Link>
    </div>
  );
}

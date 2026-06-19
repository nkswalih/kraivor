'use client';

import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/hooks';
import { Skeleton } from '@/components/ui/shadcn';
import { ArrowLeft, User, Mail, Shield } from 'lucide-react';

export default function ProfilePage() {
  const router = useRouter();
  const { user, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="p-8 max-w-2xl mx-auto space-y-4">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-4 w-64" />
        <div className="mt-8 space-y-4">
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-16 w-full" />
        </div>
      </div>
    );
  }

  const initials = user?.name
    ? user.name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2)
    : 'U';

  return (
    <div className="p-8 max-w-2xl mx-auto">
      <button
        onClick={() => router.back()}
        className="flex items-center gap-1.5 text-[13px] text-muted-foreground hover:text-foreground mb-4 transition-colors"
      >
        <ArrowLeft className="w-4 h-4" /> Back
      </button>
      <div className="flex items-center gap-4 mb-8">
        <div className="w-16 h-16 rounded-full bg-krait-surface3 border border-krait-border flex items-center justify-center text-xl font-semibold text-text-primary">
          {initials}
        </div>
        <div>
          <h1 className="text-xl font-semibold text-text-primary">{user?.name ?? 'User'}</h1>
          <p className="text-sm text-text-tertiary">{user?.email}</p>
        </div>
      </div>

      <div className="space-y-3">
        <div className="flex items-center gap-3 p-3 rounded-lg bg-krait-surface1 border border-krait-border">
          <User className="w-4 h-4 text-text-tertiary" />
          <span className="text-sm text-text-primary">{user?.name ?? '—'}</span>
        </div>
        <div className="flex items-center gap-3 p-3 rounded-lg bg-krait-surface1 border border-krait-border">
          <Mail className="w-4 h-4 text-text-tertiary" />
          <span className="text-sm text-text-primary">{user?.email ?? '—'}</span>
        </div>
        <div className="flex items-center gap-3 p-3 rounded-lg bg-krait-surface1 border border-krait-border">
          <Shield className="w-4 h-4 text-text-tertiary" />
          <span className="text-sm text-text-primary">Member</span>
        </div>
      </div>
    </div>
  );
}

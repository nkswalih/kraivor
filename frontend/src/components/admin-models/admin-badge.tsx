'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Shield } from 'lucide-react';
import { useAuthStore } from '@/lib/stores/auth-store';
import { adminEndpoints } from '@/lib/api/endpoints/admin';

export function AdminBadge() {
  const [isSuperadmin, setIsSuperadmin] = useState(false);
  const isAuthenticated = useAuthStore(s => s.isAuthenticated);
  const accessToken = useAuthStore(s => s.accessToken);

  useEffect(() => {
    if (!isAuthenticated || !accessToken) return;
    let cancelled = false;
    adminEndpoints
      .me()
      .then(() => {
        if (!cancelled) setIsSuperadmin(true);
      })
      .catch(() => {
        if (!cancelled) setIsSuperadmin(false);
      });
    return () => {
      cancelled = true;
    };
  }, [isAuthenticated, accessToken]);

  if (!isSuperadmin) return null;

  return (
    <Link
      href="/admin/models"
      className="flex items-center gap-1.5 px-2 py-1 rounded-[6px] text-venom-yellow hover:bg-krait-surface1 transition-colors"
      title="Platform Admin"
    >
      <Shield className="w-3.5 h-3.5" />
      <span className="text-[11px] font-semibold tracking-wide uppercase hidden sm:inline">
        Admin
      </span>
    </Link>
  );
}

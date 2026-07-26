'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Loader2, Shield } from 'lucide-react';
import { useAuthStore } from '@/lib/stores/auth-store';
import { adminEndpoints } from '@/lib/api/endpoints/admin';

interface AdminInfo {
  user_id: string;
  email: string;
  is_superadmin: boolean;
}

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const isAuthenticated = useAuthStore(s => s.isAuthenticated);
  const accessToken = useAuthStore(s => s.accessToken);
  const [checking, setChecking] = useState(true);
  const [adminInfo, setAdminInfo] = useState<AdminInfo | null>(null);

  useEffect(() => {
    if (!isAuthenticated || !accessToken) {
      router.replace('/login');
      return;
    }
    adminEndpoints
      .me()
      .then((data) => {
        setAdminInfo(data as AdminInfo);
        setChecking(false);
      })
      .catch(() => router.replace('/'));
  }, [isAuthenticated, accessToken, router]);

  if (checking) {
    return (
      <div className="h-screen w-screen flex items-center justify-center bg-krait-void">
        <Loader2 className="w-6 h-6 text-venom-yellow animate-spin" />
      </div>
    );
  }

  return (
    <div className="h-screen w-screen flex flex-col bg-krait-void overflow-hidden">
      {/* Admin topbar */}
      <header className="h-12 border-b border-krait-border flex items-center px-4 bg-krait-void shrink-0 gap-4">
        <div className="flex items-center gap-2">
          <div className="w-5 h-5 bg-venom-yellow rounded-[4px] flex items-center justify-center text-black font-bold text-[10px]">
            K
          </div>
          <span className="text-[13px] font-semibold text-text-primary">Kraivor</span>
          <span className="text-krait-border mx-1">/</span>
          <span className="text-[13px] text-venom-yellow font-semibold">Platform Admin</span>
        </div>
        <div className="flex-1" />
        {/* Admin user info */}
        {adminInfo && (
          <div className="flex items-center gap-2">
            {adminInfo.is_superadmin && (
              <div className="flex items-center gap-1 px-2 py-0.5 rounded-[6px] bg-venom-yellow/10 border border-venom-yellow/20">
                <Shield className="w-3 h-3 text-venom-yellow" />
                <span className="text-[11px] font-semibold text-venom-yellow">Superadmin</span>
              </div>
            )}
            <span className="text-[12px] text-text-tertiary">{adminInfo.email}</span>
          </div>
        )}
        <a
          href="/"
          className="text-[12px] text-text-tertiary hover:text-text-secondary transition-colors"
        >
          Back to app
        </a>
      </header>

      {/* Content */}
      <div className="flex-1 overflow-y-auto">{children}</div>
    </div>
  );
}

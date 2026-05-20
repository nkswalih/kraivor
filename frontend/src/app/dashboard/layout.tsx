'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { cn } from '@/lib/utils';
import { Shield, Key, Smartphone, LogOut } from 'lucide-react';
import { useAuthStore } from '@/store/auth.store';
import { useRouter } from 'next/navigation';

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { user, logout } = useAuthStore();
  const router = useRouter();

  const navigation = [
    { name: 'Security', href: '/dashboard/settings/security', icon: Shield },
    { name: 'API Keys', href: '/dashboard/settings/api-keys', icon: Key },
    { name: 'MFA Setup', href: '/dashboard/settings/mfa', icon: Smartphone },
  ];

  const handleLogout = () => {
    logout();
    router.push('/login');
  };

  return (
    <div className="min-h-screen bg-[#0a0a0a] text-white">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
        <div className="flex justify-between items-center mb-10 border-b border-white/10 pb-6">
          <div className="flex items-center gap-4">
            <div className="w-10 h-10 bg-gradient-to-br from-primary to-accent rounded-xl shadow-[0_0_15px_rgba(250,204,21,0.2)] flex items-center justify-center font-bold text-[#0a0a0a]">
              K
            </div>
            <h1 className="text-2xl font-bold">Personal Account</h1>
          </div>
          <div className="flex items-center gap-6">
            <span className="text-sm text-gray-400 hidden sm:block">{user?.email}</span>
            <button onClick={handleLogout} className="flex items-center gap-2 text-sm text-red-400 hover:text-red-300 transition-colors bg-red-400/10 px-3 py-1.5 rounded-lg">
              <LogOut className="w-4 h-4" /> Sign Out
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
          <nav className="space-y-1">
            {navigation.map((item) => {
              const isActive = pathname === item.href;
              return (
                <Link
                  key={item.name}
                  href={item.href}
                  className={cn(
                    "flex items-center gap-3 px-4 py-2.5 text-sm font-medium rounded-xl transition-all",
                    isActive ? "bg-primary/10 text-primary border border-primary/20" : "text-gray-400 hover:text-white hover:bg-[#151515] border border-transparent"
                  )}
                >
                  <item.icon className={cn("w-5 h-5", isActive ? "text-primary" : "text-gray-500")} />
                  {item.name}
                </Link>
              );
            })}
          </nav>

          <div className="md:col-span-3">
            <div className="bg-[#111111] border border-white/5 rounded-2xl p-6 sm:p-8 shadow-2xl relative overflow-hidden">
              <div className="absolute top-0 left-0 right-0 h-[1px] bg-gradient-to-r from-transparent via-white/10 to-transparent" />
              {children}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

'use client';

import React from 'react';
import Link from 'next/link';
import { useParams, usePathname, useRouter } from 'next/navigation';

import { Sidebar, Header } from '@/components/layout';
import { cn } from '@/lib/utils';
import { useUI } from '@/lib/hooks';

import {
  Shield,
  Key,
  Smartphone,
  LogOut,
} from 'lucide-react';

import { useAuthStore } from '@/lib/stores/auth-store';
import { authApi } from '@/lib/api/auth-api';

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const params = useParams();
  const pathname = usePathname();
  const router = useRouter();

  const workspaceSlug = params.workspace as string;

  const { sidebarCollapsed } = useUI();
  const { user, clearAuth } = useAuthStore();

  const navigation = [
    {
      name: 'Security',
      href: `/${workspaceSlug}/settings/security`,
      icon: Shield,
    },
    {
      name: 'API Keys',
      href: `/${workspaceSlug}/settings/api-keys`,
      icon: Key,
    },
    {
      name: 'MFA Setup',
      href: `/${workspaceSlug}/settings/mfa`,
      icon: Smartphone,
    },
  ];

  const handleLogout = async () => {
    try {
      await authApi.logout();
    } finally {
      clearAuth();
      router.push('/login');
    }
  };

  const isSettingsPage = pathname.includes('/settings');

  return (
    <div className="min-h-screen bg-background">
      {/* Main Workspace Sidebar */}
      <Sidebar workspaceSlug={workspaceSlug} />

      <div
        className={cn(
          'transition-all duration-200',
          sidebarCollapsed ? 'pl-16' : 'pl-64'
        )}
      >
        {/* Top Header */}
        <Header workspaceName="Dashboard" />

        <main className="p-6">
          {/* Settings Layout */}
          {isSettingsPage ? (
            <div className="max-w-7xl mx-auto">
              {/* Settings Header */}
              <div className="flex justify-between items-center mb-10 border-b border-border pb-6">
                <div className="flex items-center gap-4">
                  <div className="w-10 h-10 bg-gradient-to-br from-primary to-accent rounded-xl flex items-center justify-center font-bold text-black">
                    K
                  </div>

                  <div>
                    <h1 className="text-2xl font-bold">
                      Account Settings
                    </h1>

                    <p className="text-sm text-muted-foreground">
                      Manage your account security and preferences
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-6">
                  <span className="text-sm text-muted-foreground hidden sm:block">
                    {user?.email}
                  </span>

                  <button
                    onClick={handleLogout}
                    className="flex items-center gap-2 text-sm text-red-400 hover:text-red-300 transition-colors bg-red-500/10 px-3 py-2 rounded-xl border border-red-500/10"
                  >
                    <LogOut className="w-4 h-4" />
                    Sign Out
                  </button>
                </div>
              </div>

              {/* Settings Content */}
              <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
                {/* Settings Sidebar */}
                <nav className="space-y-2">
                  {navigation.map((item) => {
                    const isActive = pathname === item.href;

                    return (
                      <Link
                        key={item.name}
                        href={item.href}
                        className={cn(
                          'flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-all border',
                          isActive
                            ? 'bg-primary/10 text-primary border-primary/20'
                            : 'border-transparent text-muted-foreground hover:text-foreground hover:bg-muted'
                        )}
                      >
                        <item.icon
                          className={cn(
                            'w-5 h-5',
                            isActive
                              ? 'text-primary'
                              : 'text-muted-foreground'
                          )}
                        />

                        {item.name}
                      </Link>
                    );
                  })}
                </nav>

                {/* Settings Page */}
                <div className="md:col-span-3">
                  <div className="bg-card border border-border rounded-2xl p-6 sm:p-8 shadow-sm relative overflow-hidden">
                    {children}
                  </div>
                </div>
              </div>
            </div>
          ) : (
            children
          )}
        </main>
      </div>
    </div>
  );
}
'use client';

import { useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useAuthStore } from '@/lib/stores/auth-store';

export default function OAuthSuccessPage() {
  const router = useRouter();
  const params = useSearchParams();
  const { setAuth, initWorkspace } = useAuthStore();

  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading');
  const [errorMessage, setErrorMessage] = useState('Authenticating...');

  useEffect(() => {
    const token = params.get('access_token');

    if (!token) {
      setStatus('error');
      setErrorMessage('No access token found. Redirecting...');
      setTimeout(() => router.push('/login'), 2500);
      return;
    }

    async function loadUser() {
      try {
        const response = await fetch('/api/auth/me/', {
          credentials: 'include',
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
        });

        if (!response.ok) throw new Error('Failed to fetch user details');

        const user = await response.json();

        setAuth(user, token as string);

        const slug = await initWorkspace();

        setStatus('success');
        setTimeout(() => {
          router.replace(slug ? `/${slug}` : '/');
        }, 800);
      } catch (error) {
        console.error('OAuth finalize error:', error);
        setStatus('error');
        setErrorMessage('Authentication failed. Please try again.');
        setTimeout(() => router.push('/login'), 3000);
      }
    }

    loadUser();
  }, [params, router, setAuth, initWorkspace]);

  return (
    <div className="mx-auto w-full max-w-[420px] animate-fade-up">
      <div className="mb-8 text-center">
        <div className="mb-3 inline-flex items-center gap-2">
          <span className="text-2xl font-bold bg-gradient-to-br from-[hsl(var(--primary-light))] to-[hsl(var(--primary))] bg-clip-text text-transparent">
            Kraivor
          </span>
        </div>
        <h1 className="text-[28px] font-bold leading-tight tracking-tight text-white">
          {status === 'error' ? 'Sign In Failed' : 'Authenticating'}
        </h1>
        <p className="mt-1.5 text-sm text-slate-400">
          {status === 'error' ? errorMessage : 'Please wait while we securely log you in'}
        </p>
      </div>

      <div
        className="relative flex min-h-[280px] flex-col items-center justify-center overflow-hidden rounded-2xl p-8 text-center transition-all duration-500"
        style={{
          background: 'rgba(255, 255, 255, 0.03)',
          backdropFilter: 'blur(24px)',
          WebkitBackdropFilter: 'blur(24px)',
          border: `1px solid ${status === 'error' ? 'rgba(239, 68, 68, 0.2)' : 'rgba(255, 255, 255, 0.08)'}`,
          boxShadow: '0 24px 64px -12px rgba(0, 0, 0, 0.6), inset 0 1px 0 rgba(255,255,255,0.06)',
        }}
      >
        <div
          className={`absolute left-1/2 top-1/2 h-40 w-40 -translate-x-1/2 -translate-y-1/2 rounded-full blur-[64px] transition-colors duration-700 ${
            status === 'error' ? 'bg-red-500/20' : status === 'success' ? 'bg-green-500/20' : 'bg-[hsl(var(--primary))]/20'
          }`}
        />

        <div className="relative z-10 flex flex-col items-center animate-fade-up-delay-1">
          {status === 'loading' && (
            <div className="relative flex items-center justify-center mb-6">
              <div className="absolute h-16 w-16 animate-pulse-ring rounded-full border-2 border-[hsl(var(--primary))] opacity-20"></div>
              <svg className="h-10 w-10 animate-spin text-[hsl(var(--primary-light))]" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
            </div>
          )}

          {status === 'success' && (
            <div className="mb-6 flex h-16 w-16 items-center justify-center rounded-full bg-green-500/10 text-green-400 border border-green-500/20 animate-fade-up">
              <svg className="h-8 w-8" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
                <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
              </svg>
            </div>
          )}

          {status === 'error' && (
            <div className="mb-6 flex h-16 w-16 items-center justify-center rounded-full bg-red-500/10 text-red-400 border border-red-500/20 animate-fade-up">
              <svg className="h-8 w-8" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </div>
          )}

          <p className="text-base font-semibold text-white">
            {status === 'loading' && 'Completing sign in...'}
            {status === 'success' && 'Login successful!'}
            {status === 'error' && 'Something went wrong.'}
          </p>
          <p className="mt-2 text-sm text-slate-400">
            {status === 'loading' && 'Fetching your workspace details.'}
            {status === 'success' && 'Redirecting to your dashboard...'}
            {status === 'error' && 'Returning to login page...'}
          </p>
        </div>
      </div>
    </div>
  );
}

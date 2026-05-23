'use client';

import { useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useAuthStore } from '@/lib/stores/auth-store';

export default function OAuthSuccessPage() {
  const router = useRouter();
  const params = useSearchParams();

  const { setAuth } = useAuthStore();

  useEffect(() => {
    const token = params.get('access_token');

    if (!token) {
      router.push('/login');
      return;
    }

    const accessToken = token;

    async function loadUser() {
      try {
        const response = await fetch('/api/auth/me/', {
          credentials: 'include',
          headers: {
            Authorization: `Bearer ${accessToken}`,
          },
        });

        if (!response.ok) {
          throw new Error('Failed auth');
        }

        const user = await response.json();

        setAuth(user, accessToken);

        router.push('/dashboard');
      } catch (error) {
        console.error(error);
        router.push('/login');
      }
    }

    loadUser();
  }, [params, router, setAuth]);

  return (
    <div className="mx-auto w-full max-w-[420px] animate-fade-up">
      {/* ── Brand ─────────────────────────────────────────── */}
      <div className="mb-8 text-center">
        <div className="mb-3 inline-flex items-center gap-2">
          <span
            className="text-2xl font-bold"
            style={{
              background: 'linear-gradient(135deg, #a78bfa, #818cf8)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              backgroundClip: 'text',
            }}
          >
            ✦ Kraivor
          </span>
        </div>
        <h1 className="text-[28px] font-bold leading-tight tracking-tight text-white">
          Authenticating
        </h1>
        <p className="mt-1.5 text-sm text-slate-400">
          Please wait while we securely log you in
        </p>
      </div>

      {/* ── Glass card / Loading State ────────────────────── */}
      <div
        className="flex min-h-[260px] flex-col items-center justify-center rounded-2xl p-8 text-center"
        style={{
          background: 'rgba(255, 255, 255, 0.03)',
          backdropFilter: 'blur(24px)',
          WebkitBackdropFilter: 'blur(24px)',
          border: '1px solid rgba(255, 255, 255, 0.08)',
          boxShadow: '0 24px 64px -12px rgba(0, 0, 0, 0.6), inset 0 1px 0 rgba(255,255,255,0.06)',
        }}
      >
        <div className="animate-fade-up-delay-1 flex flex-col items-center">
          <svg
            className="mb-6 h-10 w-10 animate-spin text-violet-400"
            viewBox="0 0 24 24"
            fill="none"
            aria-hidden="true"
          >
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
            />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
            />
          </svg>
          <p className="text-base font-medium text-white">Completing sign in...</p>
          <p className="mt-2 text-sm text-slate-400">
            Fetching your workspace details.
          </p>
        </div>
      </div>
    </div>
  );
}
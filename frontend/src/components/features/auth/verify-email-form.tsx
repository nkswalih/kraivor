'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { useAuth } from '@/lib/hooks';
import { ROUTES } from '@/constants';

export function VerifyEmailForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get('token') || '';
  const email = searchParams.get('email') || '';
  const { verifyEmail } = useAuth();
  const [status, setStatus] = useState<'loading' | 'success' | 'error' | 'expired'>('loading');
  const [message, setMessage] = useState('');
  const [isResending, setIsResending] = useState(false);
  const [resendMessage, setResendMessage] = useState('');

  useEffect(() => {
    if (!token) {
      setStatus('error');
      setMessage('No verification token provided.');
      return;
    }

    const handleVerify = async () => {
      try {
        await verifyEmail({ token });
        setStatus('success');
        setMessage('Email verified successfully! Redirecting to login...');
        setTimeout(() => router.push(ROUTES.LOGIN), 2000);
      } catch (err: any) {
        if (err?.errorCode === 'token_expired') {
          setStatus('expired');
          setMessage('Your verification link has expired.');
        } else {
          setStatus('error');
          setMessage(err?.message || 'Invalid verification token.');
        }
      }
    };

    handleVerify();
  }, [token, verifyEmail, router]);

  const handleResend = async () => {
    if (!email) return;
    setIsResending(true);
    setResendMessage('');
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/auth/resend-verification/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email }),
      });
      const data = await response.json();
      if (response.ok) {
        setResendMessage(data.message || 'Verification email resent!');
      } else {
        setResendMessage(data.error || 'Failed to resend. Please try again.');
      }
    } catch {
      setResendMessage('Failed to resend. Please try again.');
    } finally {
      setIsResending(false);
    }
  };

  return (
    <div className="mx-auto w-full max-w-[420px] animate-fade-up">
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
          {status === 'success' ? 'Email Verified' : 'Verify your email'}
        </h1>
        <p className="mt-1.5 text-sm text-slate-400">
          {email
            ? `We sent a verification link to ${email}`
            : 'Check your email for the verification link'}
        </p>
      </div>

      <div
        className="rounded-2xl p-8"
        style={{
          background: 'rgba(255, 255, 255, 0.03)',
          backdropFilter: 'blur(24px)',
          WebkitBackdropFilter: 'blur(24px)',
          border: '1px solid rgba(255, 255, 255, 0.08)',
          boxShadow: '0 24px 64px -12px rgba(0, 0, 0, 0.6), inset 0 1px 0 rgba(255,255,255,0.06)',
        }}
      >
        <div className="flex flex-col items-center space-y-6">
          {status === 'loading' && (
            <>
              <svg
                className="h-12 w-12 animate-spin text-violet-400"
                viewBox="0 0 24 24"
                fill="none"
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
              <p className="text-sm text-slate-400">Verifying your email...</p>
            </>
          )}

          {status === 'success' && (
            <>
              <div className="w-16 h-16 bg-green-500/10 rounded-full flex items-center justify-center">
                <svg
                  width="32"
                  height="32"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  className="text-green-400"
                >
                  <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                  <polyline points="9 12 11 14 15 10" />
                </svg>
              </div>
              <p className="text-sm text-green-300 text-center">{message}</p>
            </>
          )}

          {status === 'expired' && (
            <>
              <div className="w-16 h-16 bg-amber-500/10 rounded-full flex items-center justify-center">
                <svg
                  width="32"
                  height="32"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  className="text-amber-400"
                >
                  <circle cx="12" cy="12" r="10" />
                  <polyline points="12 6 12 12 16 14" />
                </svg>
              </div>
              <p className="text-sm text-amber-300 text-center">{message}</p>
              {email && (
                <button
                  onClick={handleResend}
                  disabled={isResending}
                  className="btn-shimmer relative mt-2 flex w-full items-center justify-center gap-2 rounded-xl px-4 py-3 text-sm font-semibold text-white disabled:opacity-60"
                >
                  {isResending ? 'Sending...' : 'Resend verification email →'}
                </button>
              )}
              {resendMessage && (
                <p className="text-xs text-slate-400 text-center">{resendMessage}</p>
              )}
            </>
          )}

          {status === 'error' && (
            <>
              <div className="w-16 h-16 bg-red-500/10 rounded-full flex items-center justify-center">
                <svg
                  width="32"
                  height="32"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  className="text-red-400"
                >
                  <circle cx="12" cy="12" r="10" />
                  <line x1="15" y1="9" x2="9" y2="15" />
                  <line x1="9" y1="9" x2="15" y2="15" />
                </svg>
              </div>
              <p className="text-sm text-red-300 text-center">{message}</p>
              <Link
                href={ROUTES.LOGIN}
                className="text-sm text-violet-400 hover:text-violet-300 hover:underline"
              >
                Back to login
              </Link>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

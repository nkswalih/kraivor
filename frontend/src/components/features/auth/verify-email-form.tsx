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
    if (token) {
      handleVerify();
    } else if (email) {
      setStatus('loading');
      setMessage(`We sent a verification link to ${email}`);
    } else {
      setStatus('error');
      setMessage('Missing email or verification token.');
    }
  }, [token, email]);

  const handleVerify = async () => {
    setStatus('loading');
    setMessage('Verifying your email...');
    try {
      await verifyEmail({ token });
      setStatus('success');
      setMessage('Email verified successfully! Redirecting to login...');
      setTimeout(() => router.push(ROUTES.LOGIN), 2000);
    } catch (err: unknown) {
      if ((err as any)?.errorCode === 'token_expired') {
        setStatus('expired');
        setMessage('Your verification link has expired.');
      } else {
        setStatus('error');
        setMessage((err as any)?.message || 'Invalid verification token.');
      }
    }
  };

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

  const statusConfig = {
    loading: {
      icon: (
        <svg className="h-12 w-12 animate-spin text-primary" viewBox="0 0 24 24" fill="none">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
      ),
    },
    success: {
      icon: (
        <div className="w-16 h-16 bg-primary/10 rounded-full flex items-center justify-center">
          <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-primary">
            <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
            <polyline points="9 12 11 14 15 10" />
          </svg>
        </div>
      ),
    },
    expired: {
      icon: (
        <div className="w-16 h-16 bg-destructive/10 rounded-full flex items-center justify-center">
          <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-destructive">
            <circle cx="12" cy="12" r="10" />
            <polyline points="12 6 12 12 16 14" />
          </svg>
        </div>
      ),
    },
    error: {
      icon: (
        <div className="w-16 h-16 bg-destructive/10 rounded-full flex items-center justify-center">
          <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-destructive">
            <circle cx="12" cy="12" r="10" />
            <line x1="15" y1="9" x2="9" y2="15" />
            <line x1="9" y1="9" x2="15" y2="15" />
          </svg>
        </div>
      ),
    },
  };

  return (
    <div className="mx-auto w-full max-w-[420px] animate-fade-up">
      <div className="mb-8 text-center">
        <div className="mb-3 inline-flex items-center gap-2">
          <span className="text-2xl font-bold bg-gradient-to-br from-[hsl(var(--primary-light))] to-[hsl(var(--primary))] bg-clip-text text-transparent">
            ✦ Kraivor
          </span>
        </div>
        <h1 className="text-[28px] font-bold leading-tight tracking-tight text-foreground">
          {status === 'success' ? 'Email Verified' : 'Verify your email'}
        </h1>
        <p className="mt-1.5 text-sm text-muted-foreground">
          {email && !token
            ? `We sent a verification link to ${email}`
            : email && token
            ? `Verifying ${email}`
            : 'Check your email for the verification link'}
        </p>
      </div>

      <div className="rounded-2xl p-8 bg-card border-border" style={{ boxShadow: '0 24px 64px -12px rgba(0, 0, 0, 0.6), inset 0 1px 0 rgba(255,255,255,0.06)' }}>
        <div className="flex flex-col items-center space-y-6">
          {statusConfig[status].icon}

          {status === 'loading' && !token && email && (
            <div className="text-center space-y-4">
              <p className="text-sm text-muted-foreground">{message}</p>
              <p className="text-xs text-muted-foreground">
                Didn&apos;t receive the email?{' '}
                <button
                  onClick={handleResend}
                  disabled={isResending}
                  className="text-primary hover:underline underline-offset-2"
                >
                  Resend
                </button>
              </p>
              {resendMessage && (
                <p className="text-xs text-muted-foreground">{resendMessage}</p>
              )}
            </div>
          )}

          {status === 'loading' && token && (
            <p className="text-sm text-muted-foreground">Verifying your email...</p>
          )}

          {status === 'success' && (
            <p className="text-sm text-primary text-center">{message}</p>
          )}

          {status === 'expired' && (
            <>
              <p className="text-sm text-destructive text-center">{message}</p>
              {email && (
                <button
                  onClick={handleResend}
                  disabled={isResending}
                  className="btn-shimmer relative mt-2 flex w-full items-center justify-center gap-2 rounded-xl px-4 py-3 text-sm font-semibold text-primary-foreground disabled:opacity-60"
                >
                  {isResending ? 'Sending...' : 'Resend verification email →'}
                </button>
              )}
              {resendMessage && (
                <p className="text-xs text-muted-foreground text-center">{resendMessage}</p>
              )}
            </>
          )}

          {status === 'error' && !token && !email && (
            <>
              <p className="text-sm text-destructive text-center">{message}</p>
              <Link
                href={ROUTES.LOGIN}
                className="text-sm text-primary hover:underline underline-offset-2"
              >
                Back to login
              </Link>
            </>
          )}

          {status === 'error' && (token || email) && (
            <>
              <p className="text-sm text-destructive text-center">{message}</p>
              <div className="flex items-center gap-3">
                {email && (
                  <button
                    onClick={handleResend}
                    disabled={isResending}
                    className="text-sm text-primary hover:underline underline-offset-2"
                  >
                    Resend verification email
                  </button>
                )}
                <Link
                  href={ROUTES.LOGIN}
                  className="text-sm text-muted-foreground hover:text-foreground underline underline-offset-2"
                >
                  Back to login
                </Link>
              </div>
            </>
          )}
        </div>
      </div>

      <p className="mt-6 text-center text-sm text-muted-foreground">
        Already verified?{' '}
        <Link
          href={ROUTES.LOGIN}
          className="font-medium text-primary hover:underline underline-offset-2"
        >
          Sign in
        </Link>
      </p>
    </div>
  );
}

'use client';

import { useState, useEffect, useRef, KeyboardEvent, ClipboardEvent } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/lib/stores';
import { cn } from '@/lib/utils';
import { DEFAULT_DASHBOARD_ROUTE } from '@/constants';

export default function MfaVerifyPage() {
  const router = useRouter();
  const { mfaToken, setMfaToken, setUser, setAccessToken } = useAuthStore();
  const [otp, setOtp] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);
  const inputRefs = useRef<Array<HTMLInputElement | null>>([]);

  useEffect(() => {
    if (!mfaToken) {
      setServerError('Session expired. Please sign in again.');
      setTimeout(() => router.push('/login'), 2000);
    }
  }, [mfaToken, router]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>, index: number) => {
    const val = e.target.value;
    if (!/^[0-9]*$/.test(val)) return;
    const newValue = otp.padEnd(6, ' ').split('');
    newValue[index] = val.substring(val.length - 1);
    setOtp(newValue.join('').replace(/ /g, ''));
    if (val && index < 5) inputRefs.current[index + 1]?.focus();
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>, index: number) => {
    if (e.key === 'Backspace' && !otp[index] && index > 0) {
      inputRefs.current[index - 1]?.focus();
    }
  };

  const handlePaste = (e: ClipboardEvent<HTMLInputElement>) => {
    e.preventDefault();
    const pastedData = e.clipboardData.getData('text/plain').slice(0, 6).replace(/[^0-9]/g, '');
    if (pastedData) {
      setOtp(pastedData);
      inputRefs.current[Math.min(pastedData.length, 5)]?.focus();
    }
  };

  const handleVerify = async () => {
    if (otp.length !== 6) return;
    setServerError(null);
    setIsLoading(true);

    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/auth/mfa/verify`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mfa_token: mfaToken, code: otp }),
      });

      if (!response.ok) throw new Error('Invalid verification code');

      const data = await response.json();
      setUser(data.user);
      setAccessToken(data.access_token);
      setMfaToken(null);

      router.replace(DEFAULT_DASHBOARD_ROUTE);
    } catch {
      setServerError('Invalid verification code. Please try again.');
      setOtp('');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="relative min-h-screen flex items-center justify-center overflow-hidden bg-[#0a0a0f]">
      {/* Background */}
      <div aria-hidden="true" className="animate-float-slow pointer-events-none absolute -top-40 -left-40 h-[600px] w-[600px] rounded-full opacity-25" style={{ background: 'radial-gradient(circle, #7c3aed 0%, #4f46e5 50%, transparent 70%)', filter: 'blur(80px)' }} />
      <div aria-hidden="true" className="animate-float-medium pointer-events-none absolute -bottom-32 -right-32 h-[500px] w-[500px] rounded-full opacity-20" style={{ background: 'radial-gradient(circle, #6366f1 0%, #8b5cf6 50%, transparent 70%)', filter: 'blur(90px)' }} />
      <div aria-hidden="true" className="animate-float-fast pointer-events-none absolute top-1/2 left-1/2 h-[300px] w-[300px] -translate-x-1/2 -translate-y-1/2 rounded-full opacity-10" style={{ background: 'radial-gradient(circle, #a78bfa 0%, transparent 70%)', filter: 'blur(60px)' }} />
      <div aria-hidden="true" className="pointer-events-none absolute inset-0 opacity-[0.03]" style={{ backgroundImage: 'radial-gradient(circle, #ffffff 1px, transparent 1px)', backgroundSize: '32px 32px' }} />

      <div className="relative z-10 w-full px-4 py-8">
        <div className="mx-auto w-full max-w-[420px] animate-fade-up">
          {/* Brand */}
          <div className="mb-8 text-center">
            <div className="mb-3 inline-flex items-center gap-2">
              <span className="text-2xl font-bold" style={{ background: 'linear-gradient(135deg, #a78bfa, #818cf8)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', backgroundClip: 'text' }}>
                ✦ Kraivor
              </span>
            </div>
            <h1 className="text-[28px] font-bold leading-tight tracking-tight text-white">
              Two-Factor Authentication
            </h1>
            <p className="mt-1.5 text-sm text-slate-400">
              Enter the 6-digit code from your authenticator app
            </p>
          </div>

          {/* Card */}
          <div className="rounded-2xl p-8" style={{ background: 'rgba(255, 255, 255, 0.03)', backdropFilter: 'blur(24px)', WebkitBackdropFilter: 'blur(24px)', border: '1px solid rgba(255, 255, 255, 0.08)', boxShadow: '0 24px 64px -12px rgba(0, 0, 0, 0.6), inset 0 1px 0 rgba(255,255,255,0.06)' }}>
            {serverError && (
              <div className="mb-4 rounded-lg px-4 py-3 text-sm text-red-300" style={{ background: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239,68,68,0.2)' }} role="alert">
                {serverError}
              </div>
            )}

            <div className="flex flex-col items-center space-y-6">
              <div className="w-16 h-16 bg-violet-500/10 rounded-full flex items-center justify-center mb-2">
                <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-violet-400">
                  <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                  <polyline points="9 12 11 14 15 10" />
                </svg>
              </div>

              <div className="flex gap-2 sm:gap-3 w-full justify-center">
                {Array.from({ length: 6 }).map((_, index) => (
                  <input
                    key={index}
                    ref={(el) => { inputRefs.current[index] = el; }}
                    type="text"
                    inputMode="numeric"
                    maxLength={1}
                    value={otp[index] || ''}
                    onChange={(e) => handleChange(e, index)}
                    onKeyDown={(e) => handleKeyDown(e, index)}
                    onPaste={handlePaste}
                    disabled={isLoading}
                    className={cn(
                      'w-10 h-12 sm:w-12 sm:h-14 text-center text-xl font-semibold rounded-xl transition-all duration-200',
                      'bg-white/5 border border-white/10 text-white',
                      'focus:outline-none focus:border-violet-500/50 focus:ring-1 focus:ring-violet-500/50 focus:-translate-y-1',
                      'disabled:opacity-50 disabled:cursor-not-allowed',
                    )}
                  />
                ))}
              </div>

              <button
                id="btn-mfa-verify"
                type="button"
                onClick={handleVerify}
                disabled={otp.length !== 6 || isLoading}
                className="btn-shimmer relative mt-2 flex w-full items-center justify-center gap-2 rounded-xl px-4 py-3 text-sm font-semibold text-white disabled:opacity-60 disabled:cursor-not-allowed disabled:transform-none"
              >
                {isLoading ? (
                  <>
                    <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                    </svg>
                    Verifying…
                  </>
                ) : (
                  'Verify Code →'
                )}
              </button>
            </div>

            <p className="text-sm text-slate-500 text-center mt-6">
              Lost access to your device?{' '}
              <button className="text-violet-400 hover:text-violet-300 hover:underline mt-1">
                Use a recovery code
              </button>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

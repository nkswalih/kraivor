// src/components/features/auth/login-form.tsx
'use client';

import { useState, useRef, KeyboardEvent } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { authApi } from '@/lib/api/auth-api';
import { DEFAULT_DASHBOARD_ROUTE, ROUTES } from '@/constants';

/* ─── Helpers & Icons ────────────────────────────────────────────── */

const maskEmail = (email: string) => {
  const [localPart, domain] = email.split('@');
  if (!localPart || !domain) return email;
  const maskedLocal = localPart.substring(0, 2) + '*'.repeat(5);
  return `${maskedLocal}@${domain}`;
};

const GithubIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
    <path d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z"/>
  </svg>
);

const GoogleIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" aria-hidden="true">
    <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
    <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
    <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
    <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
  </svg>
);

const EyeIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
    <circle cx="12" cy="12" r="3" />
  </svg>
);

const EyeOffIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
    <path d="M17.94 17.94A10.07 10.07 0 0112 20c-7 0-11-8-11-8a18.45 18.45 0 015.06-5.94M9.9 4.24A9.12 9.12 0 0112 4c7 0 11 8 11 8a18.5 18.5 0 01-2.16 3.19m-6.72-1.07a3 3 0 11-4.24-4.24" />
    <line x1="1" y1="1" x2="23" y2="23" />
  </svg>
);

const ArrowLeftIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M19 12H5M12 19l-7-7 7-7" />
  </svg>
);

/* ─── Component ──────────────────────────────────────────────── */

type Step = 'IDENTIFY' | 'CHOOSE_METHOD' | 'PASSWORD' | 'OTP_ENTER';

export function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const callbackUrl = searchParams.get('callbackUrl') || DEFAULT_DASHBOARD_ROUTE;
  
  // State Machine
  const [step, setStep] = useState<Step>('IDENTIFY');
  const [email, setEmail] = useState('');
  const [methods, setMethods] = useState<string[]>([]);
  const [serverError, setServerError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const resetFlow = () => {
    setStep('IDENTIFY');
    setEmail('');
    setMethods([]);
    setServerError(null);
  };

  const handleAuthSuccess = (mfaRequired = false) => {
    if (mfaRequired) {
      router.push('/mfa/verify');
    } else {
      router.replace(callbackUrl);
    }
  };

  return (
    <div className="mx-auto w-full max-w-[420px] animate-fade-up">
      {/* ── Brand & Headers ─────────────────────────────────────────── */}
      <div className="mb-8 text-center">
        <div className="mb-3 inline-flex items-center gap-2">
          <span className="text-2xl font-bold bg-gradient-to-br from-[hsl(var(--primary-light))] to-[hsl(var(--primary))] bg-clip-text text-transparent">
            ✦ Kraivor
          </span>
        </div>
        <h1 className="text-[28px] font-bold leading-tight tracking-tight text-white">
          {step === 'IDENTIFY' && 'Welcome back'}
          {step === 'CHOOSE_METHOD' && 'Choose sign in method'}
          {step === 'PASSWORD' && 'Enter password'}
          {step === 'OTP_ENTER' && 'Verify your email'}
        </h1>
        {step === 'IDENTIFY' && <p className="mt-1.5 text-sm text-slate-400">Sign in to your workspace</p>}
        {step !== 'IDENTIFY' && <p className="mt-1.5 text-sm font-medium text-slate-400">{email}</p>}
      </div>

      {/* ── Glass card ────────────────────────────────────── */}
      <div
        className="rounded-2xl p-8 relative overflow-hidden transition-all duration-300"
        style={{
          background: 'rgba(255, 255, 255, 0.03)',
          backdropFilter: 'blur(24px)',
          border: '1px solid rgba(255, 255, 255, 0.08)',
          boxShadow: '0 24px 64px -12px rgba(0, 0, 0, 0.6), inset 0 1px 0 rgba(255,255,255,0.06)',
        }}
      >
        {serverError && (
          <div className="mb-4 rounded-lg px-4 py-3 text-sm text-red-300 bg-red-500/10 border border-red-500/20" role="alert">
            {serverError}
          </div>
        )}

        {/* Step 1 */}
        {step === 'IDENTIFY' && (
          <IdentifyStep 
            onSuccess={(e: string, m: string[]) => { setEmail(e); setMethods(m); setStep('CHOOSE_METHOD'); }} 
            setGlobalError={setServerError} 
            isLoading={isLoading} 
            setIsLoading={setIsLoading} 
          />
        )}

        {/* Step 2 */}
        {step === 'CHOOSE_METHOD' && (
          <ChooseMethodStep 
            methods={methods} 
            email={email}
            onSelectPassword={() => setStep('PASSWORD')}
            onSelectOtp={async () => {
              try {
                setIsLoading(true); 
                setServerError(null);
                await authApi.sendOTP({ email });
                setStep('OTP_ENTER');
              } catch (err: any) {
                setServerError(err.message || 'Failed to send code.');
              } finally { 
                setIsLoading(false); 
              }
            }}
            isLoading={isLoading} 
            onBack={resetFlow}
          />
        )}

        {/* Step 3 */}
        {step === 'PASSWORD' && (
          <PasswordStep 
            email={email} 
            onSuccess={handleAuthSuccess} 
            setError={setServerError} 
            onBack={() => setStep('CHOOSE_METHOD')} 
            onReset={resetFlow}
          />
        )}

        {/* Step 4 */}
        {step === 'OTP_ENTER' && (
          <OtpStep 
            email={email} 
            onSuccess={() => handleAuthSuccess(false)} 
            setError={setServerError}
            onBack={() => setStep('CHOOSE_METHOD')}
          />
        )}
      </div>

      {step === 'IDENTIFY' && (
        <p className="mt-6 text-center text-sm text-slate-500 animate-fade-up-delay-2">
          Don&apos;t have an account?{' '}
          <Link href={ROUTES.REGISTER} className="font-medium text-[hsl(var(--primary-light))] transition-colors hover:text-[hsl(var(--primary))]">
            Create one free
          </Link>
        </p>
      )}
    </div>
  );
}

/* ──────────────────────────────────────────────────────────────────
    SUB-COMPONENTS 
────────────────────────────────────────────────────────────────── */

function IdentifyStep({ onSuccess, setGlobalError, isLoading, setIsLoading }: any) {
  const schema = z.object({ email: z.string().email('Invalid email address') });
  const { register, handleSubmit, setError: setFieldError, formState: { errors } } = useForm({ resolver: zodResolver(schema) });

  const onSubmit = async (data: any) => {
    setGlobalError(null); 
    setIsLoading(true);
    try {
      const res = await authApi.identify(data.email);
      
      if (res.user_exists === false) {
        setFieldError('email', { type: 'manual', message: 'Account not found. Please register.' });
        return;
      }

      if (res.user_exists && res.email_verified === false) {
        setFieldError('email', { type: 'manual', message: res.message || 'Please verify your email first.' });
        return;
      }

      if (res.methods && Array.isArray(res.methods)) {
        onSuccess(data.email, res.methods);
      } else {
        setFieldError('email', { type: 'manual', message: 'No login methods available.' });
      }

    } catch (err: any) {
      const errorData = err.response?.data || err;
      if (errorData?.user_exists === false) {
        setFieldError('email', { type: 'manual', message: 'Account not found. Please register.' });
      } else if (errorData?.email_verified === false) {
        setFieldError('email', { type: 'manual', message: errorData.message || 'Please verify your email first.' });
      } else {
        setFieldError('email', { type: 'manual', message: errorData.message || 'Account not found. Please register.' });
      }
    } finally {
      setIsLoading(false);
    }
  };

  // --- UPDATED OAUTH HANDLER ---
  const handleOAuth = async (provider: 'github' | 'google') => {
    try {
      setIsLoading(true);
      setGlobalError(null);

      if (provider === 'google') {
        // Google Backend Endpoint returns a 302 Redirect.
        // We MUST use standard browser navigation to avoid CORS errors.
        window.location.href = `/api/auth/oauth/${provider}/`;
        return;
      }

      if (provider === 'github') {
        // GitHub Backend Endpoint returns a 200 OK with JSON {"authorization_url": "..."}
        // We fetch the URL via our API client, then redirect.
        const res = await authApi.initiateOAuth(provider);
        if (res.authorization_url) {
          window.location.href = res.authorization_url;
        } else {
          setGlobalError(`Failed to initiate ${provider} login.`);
          setIsLoading(false);
        }
      }
    } catch (err: any) {
      setGlobalError(err.message || `Could not connect to ${provider}.`);
      setIsLoading(false);
    }
  };

  return (
    <div className="animate-fade-up">
      <div className="space-y-3 mb-6">
        <button 
          type="button" 
          onClick={() => handleOAuth('github')} 
          disabled={isLoading}
          className="oauth-btn flex w-full items-center justify-center gap-3 px-4 py-3 text-sm font-medium disabled:opacity-60"
        >
          <GithubIcon /> Continue with GitHub
        </button>
        <button 
          type="button" 
          onClick={() => handleOAuth('google')} 
          disabled={isLoading}
          className="oauth-btn flex w-full items-center justify-center gap-3 px-4 py-3 text-sm font-medium disabled:opacity-60"
        >
          <GoogleIcon /> Continue with Google
        </button>
      </div>

      <div className="relative my-6 flex items-center">
        <div className="flex-1 border-t border-white/[0.08]" />
        <span className="mx-4 text-xs text-slate-500">or continue with email</span>
        <div className="flex-1 border-t border-white/[0.08]" />
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <div className="space-y-1.5">
          <label className="block text-sm font-medium text-slate-300">Email address</label>
          <input 
            {...register('email')} 
            autoFocus 
            className={`auth-input w-full px-4 py-3 text-sm ${errors.email ? 'border-red-500/50 focus:border-red-500 focus:ring-red-500/20' : ''}`} 
            placeholder="you@company.com" 
          />
          {errors.email && <p className="text-xs text-red-400 mt-1">{errors.email.message as string}</p>}
        </div>
        <button 
          type="submit" 
          disabled={isLoading} 
          className="btn-shimmer relative flex w-full items-center justify-center gap-2 rounded-xl px-4 py-3 text-sm font-semibold text-white disabled:opacity-60 disabled:cursor-not-allowed"
        >
          {isLoading ? (
            <>
              <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              Checking...
            </>
          ) : (
            'Continue →'
          )}
        </button>
      </form>
    </div>
  );
}

function ChooseMethodStep({ methods, email, onSelectPassword, onSelectOtp, isLoading, onBack }: any) {
  const masked = maskEmail(email);
  return (
    <div className="animate-fade-up space-y-4">
      <p className="text-sm text-slate-300 text-center mb-6">How would you like to sign in?</p>
      
      {methods?.includes('password') && (
        <button onClick={onSelectPassword} className="w-full flex items-center p-4 border border-white/10 rounded-xl hover:bg-white/5 transition-colors text-left group">
          <div className="flex-1">
            <h3 className="text-sm font-medium text-white group-hover:text-[hsl(var(--primary-light))] transition-colors">Use your password</h3>
            <p className="text-xs text-slate-400 mt-1">Sign in with your Kraivor account password</p>
          </div>
          <ArrowLeftIcon /> 
        </button>
      )}

      {methods?.includes('otp') && (
        <button onClick={onSelectOtp} disabled={isLoading} className="w-full flex items-center p-4 border border-white/10 rounded-xl hover:bg-white/5 transition-colors text-left group">
          <div className="flex-1">
            <h3 className="text-sm font-medium text-white group-hover:text-[hsl(var(--primary-light))] transition-colors">Send a code</h3>
            <p className="text-xs text-slate-400 mt-1">We'll send a code to {masked}</p>
          </div>
          {isLoading ? <span className="text-xs text-slate-400">Sending...</span> : <ArrowLeftIcon />}
        </button>
      )}

      <div className="pt-4 border-t border-white/10 mt-6 text-center">
        <button onClick={onBack} className="text-sm text-slate-400 hover:text-white transition-colors">
          Sign in with a different account
        </button>
      </div>
    </div>
  );
}

function PasswordStep({ email, onSuccess, setError, onBack, onReset }: any) {
  const [show, setShow] = useState(false);
  const { register, handleSubmit, formState: { isSubmitting } } = useForm({
    resolver: zodResolver(z.object({ password: z.string().min(1, 'Password required') }))
  });

  const onSubmit = async (data: any) => {
    setError(null);
    try {
      const { mfaRequired } = await authApi.login({ email, password: data.password });
      onSuccess(mfaRequired);
    } catch (err: any) {
      setError(err.message || 'Invalid password. Please try again.');
    }
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="animate-fade-up space-y-5">
      <div className="space-y-1.5">
        <label className="block text-sm font-medium text-slate-300">Password</label>
        <div className="relative">
          <input {...register('password')} autoFocus type={show ? 'text' : 'password'} className="auth-input w-full px-4 py-3 pr-11 text-sm" placeholder="Enter your password" />
          <button type="button" onClick={() => setShow(!show)} className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300">
            {show ? <EyeOffIcon /> : <EyeIcon />}
          </button>
        </div>
      </div>
      
      <button type="submit" disabled={isSubmitting} className="btn-shimmer flex w-full items-center justify-center rounded-xl px-4 py-3 text-sm font-semibold text-white disabled:opacity-60 disabled:cursor-not-allowed">
        {isSubmitting ? (
          <>
            <svg className="mr-2 h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
            Signing in...
          </>
        ) : (
          'Sign in'
        )}
      </button>

      <div className="flex flex-col gap-3 pt-4 border-t border-white/10 text-center">
        <button type="button" onClick={onBack} className="text-sm text-[hsl(var(--primary-light))] hover:text-white transition-colors">
          Other way to sign in
        </button>
        <button type="button" onClick={onReset} className="text-xs text-slate-500 hover:text-slate-300 transition-colors">
          Sign in with a different Kraivor Account
        </button>
      </div>
    </form>
  );
}

function OtpStep({ email, onSuccess, setError, onBack }: any) {
  const [otp, setOtp] = useState(['', '', '', '', '', '']);
  const [isVerifying, setIsVerifying] = useState(false);
  const inputRefs = useRef<(HTMLInputElement | null)[]>([]);
  const masked = maskEmail(email);

  const handleChange = (index: number, val: string) => {
    if (!/^\d*$/.test(val)) return;
    const newOtp = [...otp];
    newOtp[index] = val;
    setOtp(newOtp);
    if (val && index < 5) inputRefs.current[index + 1]?.focus();
  };

  const handleKeyDown = (index: number, e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Backspace' && !otp[index] && index > 0) {
      inputRefs.current[index - 1]?.focus();
    }
  };

  const verify = async (code: string) => {
    setIsVerifying(true); 
    setError(null);
    try {
      await authApi.verifyOTP({ email, otp_code: code });
      onSuccess(); // Triggers Zustand setAuth implicitly inside API, then redirect
    } catch (err: any) {
      setError(err.message || 'Invalid or expired code.');
    } finally {
      setIsVerifying(false);
    }
  };

  const handlePaste = (e: React.ClipboardEvent) => {
    e.preventDefault();
    const pasted = e.clipboardData.getData('text').slice(0, 6).split('');
    if (pasted.length === 6 && pasted.every(c => /^\d$/.test(c))) {
      setOtp(pasted); 
      verify(pasted.join(''));
    }
  };

  const handleResend = async () => {
    setError(null);
    try { 
      await authApi.sendOTP({ email }); 
      setError('New code sent successfully!'); 
    } catch { 
      setError('Failed to resend. Please wait a moment.'); 
    }
  };

  return (
    <div className="animate-fade-up space-y-6">
      <p className="text-sm text-slate-300 text-center">
        If <span className="font-medium text-white">{masked}</span> matches the email address on your account, we'll send you a code.
      </p>

      <div className="flex justify-center gap-2" onPaste={handlePaste}>
        {otp.map((digit, i) => (
          <input
            key={i}
            ref={(el) => { inputRefs.current[i] = el; }}
            type="text" 
            maxLength={1} 
            value={digit}
            onChange={(e) => handleChange(i, e.target.value)}
            onKeyDown={(e) => handleKeyDown(i, e)}
            className="auth-input w-12 h-14 text-center text-xl font-bold rounded-lg focus:ring-2 focus:ring-[hsl(var(--primary))] transition-all"
            autoFocus={i === 0}
          />
        ))}
      </div>

      <button 
        onClick={() => verify(otp.join(''))} 
        disabled={isVerifying || otp.join('').length < 6}
        className="btn-shimmer flex w-full items-center justify-center rounded-xl px-4 py-3 text-sm font-semibold text-white disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {isVerifying ? (
          <>
            <svg className="mr-2 h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
            Verifying...
          </>
        ) : (
          'Verify Code'
        )}
      </button>

      <div className="flex flex-col gap-3 pt-4 border-t border-white/10 text-center">
        <button onClick={handleResend} className="text-sm text-slate-400 hover:text-white transition-colors">
          Didn't receive it? <span className="text-[hsl(var(--primary-light))] hover:underline">Resend code</span>
        </button>
        <button onClick={onBack} className="text-xs text-slate-500 hover:text-slate-300 transition-colors">
          Other way to sign in
        </button>
      </div>
    </div>
  );
}
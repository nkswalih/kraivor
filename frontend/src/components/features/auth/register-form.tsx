'use client';

import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/hooks';
import { ROUTES } from '@/constants';

/* ─── Validation ─────────────────────────────────────────────── */

const registerSchema = z
  .object({
    name: z.string().min(2, 'Name must be at least 2 characters'),
    email: z.string().email('Invalid email address'),
    password: z
      .string()
      .min(8, 'Password must be at least 8 characters')
      .regex(/[A-Z]/, 'Must contain at least one uppercase letter')
      .regex(/[0-9]/, 'Must contain at least one number'),
    confirmPassword: z.string(),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: 'Passwords do not match',
    path: ['confirmPassword'],
  });

type RegisterFormData = z.infer<typeof registerSchema>;

/* ─── SVG icons ──────────────────────────────────────────────── */

const GithubIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
    <path d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" />
  </svg>
);

const GoogleIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" aria-hidden="true">
    <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
    <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
    <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" />
    <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
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

/* ─── Password strength ──────────────────────────────────────── */
function PasswordStrength({ password }: { password: string }) {
  const checks = [
    password.length >= 8,
    /[A-Z]/.test(password),
    /[0-9]/.test(password),
    /[^A-Za-z0-9]/.test(password),
  ];
  const score = checks.filter(Boolean).length;
  const labels = ['', 'Weak', 'Fair', 'Good', 'Strong'];
  const colors = ['', '#ef4444', '#f59e0b', '#22c55e', '#10b981'];

  if (!password) return null;

  return (
    <div className="mt-2 space-y-1.5">
      <div className="flex gap-1">
        {[1, 2, 3, 4].map((i) => (
          <div
            key={i}
            className="h-1 flex-1 rounded-full transition-all duration-300"
            style={{
              background: i <= score ? colors[score] : 'rgba(255,255,255,0.1)',
            }}
          />
        ))}
      </div>
      <p className="text-xs" style={{ color: colors[score] }}>
        {labels[score]}
      </p>
    </div>
  );
}

/* ─── Component ──────────────────────────────────────────────── */

export function RegisterForm() {
  const router = useRouter();
  const { register: registerUser } = useAuth();
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<RegisterFormData>({
    resolver: zodResolver(registerSchema),
    defaultValues: { name: '', email: '', password: '', confirmPassword: '' },
  });

  const passwordValue = watch('password');

  const onSubmit = async (data: RegisterFormData) => {
    setServerError(null);
    try {
      await registerUser({ email: data.email, password: data.password, name: data.name });
      router.push(ROUTES.DASHBOARD);
    } catch {
      setServerError('Registration failed. Please try again or use a different email.');
    }
  };

  const handleOAuth = (provider: 'github' | 'google') => {
    window.location.href = `/api/auth/oauth/${provider}`;
  };

  return (
    <div className="mx-auto w-full max-w-[440px] animate-fade-up">
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
          Create your account
        </h1>
        <p className="mt-1.5 text-sm text-slate-400">
          Start analyzing your codebase in minutes
        </p>
      </div>

      {/* ── Glass card ────────────────────────────────────── */}
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
        {/* ── OAuth buttons ─────────────────────────────── */}
        <div className="animate-fade-up-delay-1 space-y-3">
          <button
            id="btn-github-register"
            type="button"
            onClick={() => handleOAuth('github')}
            className="oauth-btn flex w-full items-center justify-center gap-3 px-4 py-3 text-sm font-medium"
          >
            <GithubIcon />
            Sign up with GitHub
          </button>

          <button
            id="btn-google-register"
            type="button"
            onClick={() => handleOAuth('google')}
            className="oauth-btn flex w-full items-center justify-center gap-3 px-4 py-3 text-sm font-medium"
          >
            <GoogleIcon />
            Sign up with Google
          </button>
        </div>

        {/* ── Divider ───────────────────────────────────── */}
        <div className="relative my-6 flex items-center">
          <div className="flex-1 border-t border-white/[0.08]" />
          <span className="mx-4 text-xs text-slate-500">or register with email</span>
          <div className="flex-1 border-t border-white/[0.08]" />
        </div>

        {/* ── Form ──────────────────────────────────────── */}
        <form onSubmit={handleSubmit(onSubmit)} noValidate className="animate-fade-up-delay-2 space-y-4">
          {/* Server error */}
          {serverError && (
            <div
              className="rounded-lg px-4 py-3 text-sm text-red-300"
              style={{ background: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239,68,68,0.2)' }}
              role="alert"
            >
              {serverError}
            </div>
          )}

          {/* Full name */}
          <div className="space-y-1.5">
            <label htmlFor="name" className="block text-sm font-medium text-slate-300">
              Full name
            </label>
            <input
              id="name"
              type="text"
              autoComplete="name"
              placeholder="Jane Smith"
              className="auth-input w-full px-4 py-3 text-sm"
              {...register('name')}
            />
            {errors.name && (
              <p className="text-xs text-red-400">{errors.name.message}</p>
            )}
          </div>

          {/* Email */}
          <div className="space-y-1.5">
            <label htmlFor="email" className="block text-sm font-medium text-slate-300">
              Work email
            </label>
            <input
              id="email"
              type="email"
              autoComplete="email"
              placeholder="you@company.com"
              className="auth-input w-full px-4 py-3 text-sm"
              {...register('email')}
            />
            {errors.email && (
              <p className="text-xs text-red-400">{errors.email.message}</p>
            )}
          </div>

          {/* Password */}
          <div className="space-y-1.5">
            <label htmlFor="password" className="block text-sm font-medium text-slate-300">
              Password
            </label>
            <div className="relative">
              <input
                id="password"
                type={showPassword ? 'text' : 'password'}
                autoComplete="new-password"
                placeholder="Create a strong password"
                className="auth-input w-full px-4 py-3 pr-11 text-sm"
                {...register('password')}
              />
              <button
                type="button"
                onClick={() => setShowPassword((v) => !v)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 transition-colors hover:text-slate-300"
                aria-label={showPassword ? 'Hide password' : 'Show password'}
              >
                {showPassword ? <EyeOffIcon /> : <EyeIcon />}
              </button>
            </div>
            <PasswordStrength password={passwordValue} />
            {errors.password && (
              <p className="text-xs text-red-400">{errors.password.message}</p>
            )}
          </div>

          {/* Confirm password */}
          <div className="space-y-1.5">
            <label htmlFor="confirmPassword" className="block text-sm font-medium text-slate-300">
              Confirm password
            </label>
            <div className="relative">
              <input
                id="confirmPassword"
                type={showConfirm ? 'text' : 'password'}
                autoComplete="new-password"
                placeholder="Repeat your password"
                className="auth-input w-full px-4 py-3 pr-11 text-sm"
                {...register('confirmPassword')}
              />
              <button
                type="button"
                onClick={() => setShowConfirm((v) => !v)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 transition-colors hover:text-slate-300"
                aria-label={showConfirm ? 'Hide password' : 'Show password'}
              >
                {showConfirm ? <EyeOffIcon /> : <EyeIcon />}
              </button>
            </div>
            {errors.confirmPassword && (
              <p className="text-xs text-red-400">{errors.confirmPassword.message}</p>
            )}
          </div>

          {/* Terms */}
          <p className="text-xs text-slate-500">
            By creating an account you agree to our{' '}
            <a href="/terms" className="text-violet-400 hover:text-violet-300 underline underline-offset-2">
              Terms of Service
            </a>{' '}
            and{' '}
            <a href="/privacy" className="text-violet-400 hover:text-violet-300 underline underline-offset-2">
              Privacy Policy
            </a>
            .
          </p>

          {/* Submit */}
          <button
            id="btn-register-submit"
            type="submit"
            disabled={isSubmitting}
            className="btn-shimmer relative mt-1 flex w-full items-center justify-center gap-2 rounded-xl px-4 py-3 text-sm font-semibold text-white disabled:opacity-60 disabled:cursor-not-allowed disabled:transform-none"
          >
            {isSubmitting ? (
              <>
                <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                Creating account…
              </>
            ) : (
              'Create account →'
            )}
          </button>
        </form>
      </div>

      {/* ── Footer ────────────────────────────────────────── */}
      <p className="mt-6 text-center text-sm text-slate-500">
        Already have an account?{' '}
        <Link href={ROUTES.LOGIN} className="font-medium text-violet-400 transition-colors hover:text-violet-300">
          Sign in
        </Link>
      </p>
    </div>
  );
}
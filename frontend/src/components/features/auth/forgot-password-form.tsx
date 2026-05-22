'use client';

import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/hooks';
import { ROUTES } from '@/constants';

const forgotPasswordSchema = z.object({
  email: z.string().email('Invalid email address'),
});

type ForgotPasswordFormData = z.infer<typeof forgotPasswordSchema>;

export function ForgotPasswordForm() {
  const router = useRouter();
  const { forgotPassword } = useAuth();
  const [isSubmitted, setIsSubmitted] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);
  const [submittedEmail, setSubmittedEmail] = useState('');

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<ForgotPasswordFormData>({
    resolver: zodResolver(forgotPasswordSchema),
    defaultValues: { email: '' },
  });

  const onSubmit = async (data: ForgotPasswordFormData) => {
    setServerError(null);
    try {
      await forgotPassword({ email: data.email });
      setSubmittedEmail(data.email);
      setIsSubmitted(true);
    } catch {
      setServerError('Failed to send reset link. Please try again.');
    }
  };

  if (isSubmitted) {
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
            Check your email
          </h1>
          <p className="mt-1.5 text-sm text-slate-400">
            We sent a password reset link to {submittedEmail}
          </p>
        </div>

        <div
          className="rounded-2xl p-8 text-center space-y-6"
          style={{
            background: 'rgba(255, 255, 255, 0.03)',
            backdropFilter: 'blur(24px)',
            WebkitBackdropFilter: 'blur(24px)',
            border: '1px solid rgba(255, 255, 255, 0.08)',
            boxShadow: '0 24px 64px -12px rgba(0, 0, 0, 0.6), inset 0 1px 0 rgba(255,255,255,0.06)',
          }}
        >
          <p className="text-sm text-slate-400">
            Didn&apos;t receive the email? Check your spam folder or try again.
          </p>
          <button
            type="button"
            onClick={() => setIsSubmitted(false)}
            className="btn-shimmer-secondary w-full rounded-xl px-4 py-3 text-sm font-semibold text-white"
          >
            Try another email
          </button>
        </div>

        <p className="mt-6 text-center">
          <Link
            href={ROUTES.LOGIN}
            className="text-sm text-slate-400 transition-colors hover:text-violet-400"
          >
            ← Back to login
          </Link>
        </p>
      </div>
    );
  }

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
          Reset password
        </h1>
        <p className="mt-1.5 text-sm text-slate-400">Enter your email to receive a reset link</p>
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
        {serverError && (
          <div
            className="mb-4 rounded-lg px-4 py-3 text-sm text-red-300"
            style={{
              background: 'rgba(239, 68, 68, 0.1)',
              border: '1px solid rgba(239,68,68,0.2)',
            }}
            role="alert"
          >
            {serverError}
          </div>
        )}

        <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-4">
          <div className="space-y-1.5">
            <label htmlFor="email" className="block text-sm font-medium text-slate-300">
              Email address
            </label>
            <input
              id="email"
              type="email"
              autoComplete="email"
              placeholder="you@company.com"
              className="auth-input w-full px-4 py-3 text-sm"
              {...register('email')}
            />
            {errors.email && <p className="text-xs text-red-400">{errors.email.message}</p>}
          </div>

          <button
            id="btn-forgot-password-submit"
            type="submit"
            disabled={isSubmitting}
            className="btn-shimmer relative mt-2 flex w-full items-center justify-center gap-2 rounded-xl px-4 py-3 text-sm font-semibold text-white disabled:opacity-60 disabled:cursor-not-allowed disabled:transform-none"
          >
            {isSubmitting ? (
              <>
                <svg
                  className="h-4 w-4 animate-spin"
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
                Sending…
              </>
            ) : (
              'Send reset link →'
            )}
          </button>
        </form>
      </div>

      <p className="mt-6 text-center">
        <Link
          href={ROUTES.LOGIN}
          className="text-sm text-slate-400 transition-colors hover:text-violet-400"
        >
          ← Back to login
        </Link>
      </p>
    </div>
  );
}

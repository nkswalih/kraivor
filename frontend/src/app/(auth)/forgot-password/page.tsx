'use client';

import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { AuthLayout } from '@/components/layouts/AuthLayout';
import { AuthInput } from '@/components/auth/AuthInput';
import { AuthButton } from '@/components/auth/AuthButton';
import { apiClient } from '@/lib/api-client';
import { sileo } from 'sileo';
import { API_ENDPOINTS } from '@/constants';
import Link from 'next/link';
import { ArrowLeft } from 'lucide-react';

const forgotPasswordSchema = z.object({
  email: z.string().email('Please enter a valid email address'),
});

type ForgotPasswordForm = z.infer<typeof forgotPasswordSchema>;

export default function ForgotPasswordPage() {
  const [isLoading, setIsLoading] = useState(false);
  const [isSubmitted, setIsSubmitted] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ForgotPasswordForm>({
    resolver: zodResolver(forgotPasswordSchema),
  });

  const onSubmit = async (data: ForgotPasswordForm) => {
    setIsLoading(true);
    try {
      await apiClient.post(API_ENDPOINTS.AUTH.FORGOT_PASSWORD || '/auth/forgot-password', {
        email: data.email,
      });
      setIsSubmitted(true);
      sileo.success('Password reset link sent!');
    } catch (error: any) {
      sileo.error(error.message || 'Failed to send reset link');
    } finally {
      setIsLoading(false);
    }
  };

  if (isSubmitted) {
    return (
      <AuthLayout title="Check your email" subtitle="We sent a password reset link to your email.">
        <div className="text-center space-y-6">
          <p className="text-sm text-gray-400">
            Didn't receive the email? Check your spam folder or try again.
          </p>
          <AuthButton onClick={() => setIsSubmitted(false)} variant="secondary">
            Try another email
          </AuthButton>
          <Link href="/login" className="flex items-center justify-center gap-2 text-sm text-primary hover:underline mt-4">
            <ArrowLeft className="w-4 h-4" /> Back to login
          </Link>
        </div>
      </AuthLayout>
    );
  }

  return (
    <AuthLayout title="Reset Password" subtitle="Enter your email to receive a reset link">
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <AuthInput
          label="Email Address"
          type="email"
          placeholder="you@company.com"
          {...register('email')}
          error={errors.email?.message}
        />
        
        <AuthButton type="submit" isLoading={isLoading} className="mt-6">
          Send Reset Link
        </AuthButton>
      </form>
      
      <div className="mt-6 text-center">
        <Link href="/login" className="flex items-center justify-center gap-2 text-sm text-gray-400 hover:text-white transition-colors">
          <ArrowLeft className="w-4 h-4" /> Back to login
        </Link>
      </div>
    </AuthLayout>
  );
}


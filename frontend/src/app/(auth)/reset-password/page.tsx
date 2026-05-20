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
import { useRouter, useSearchParams } from 'next/navigation';
import { API_ENDPOINTS } from '@/constants';

const resetPasswordSchema = z.object({
  password: z.string().min(8, 'Password must be at least 8 characters'),
  confirmPassword: z.string(),
}).refine((data) => data.password === data.confirmPassword, {
  message: "Passwords don't match",
  path: ["confirmPassword"],
});

type ResetPasswordForm = z.infer<typeof resetPasswordSchema>;

export default function ResetPasswordPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams?.get('token');
  const uid = searchParams?.get('uid');
  const [isLoading, setIsLoading] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ResetPasswordForm>({
    resolver: zodResolver(resetPasswordSchema),
  });

  const onSubmit = async (data: ResetPasswordForm) => {
    if (!token) {
      sileo.error('Invalid or missing reset token.');
      return;
    }

    setIsLoading(true);
    try {
      await apiClient.post(API_ENDPOINTS.AUTH.RESET_PASSWORD || '/auth/reset-password', {
        token,
        uid, // some Django backends use uid+token
        new_password: data.password,
      });

      sileo.success('Password reset successfully!');
      router.push('/login');
    } catch (error: any) {
      sileo.error(error.message || 'Failed to reset password. Link may be expired.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <AuthLayout title="Create New Password" subtitle="Enter your new password below">
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <AuthInput
          label="New Password"
          type="password"
          placeholder="••••••••"
          {...register('password')}
          error={errors.password?.message}
        />
        <AuthInput
          label="Confirm Password"
          type="password"
          placeholder="••••••••"
          {...register('confirmPassword')}
          error={errors.confirmPassword?.message}
        />

        <AuthButton type="submit" isLoading={isLoading} className="mt-6">
          Reset Password
        </AuthButton>
      </form>
    </AuthLayout>
  );
}


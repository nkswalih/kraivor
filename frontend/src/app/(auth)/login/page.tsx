'use client';

import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { AuthLayout } from '@/components/layouts/AuthLayout';
import { AuthInput } from '@/components/auth/AuthInput';
import { AuthButton } from '@/components/auth/AuthButton';
import { apiClient } from '@/lib/api-client';
import { useAuthStore } from '@/store/auth.store';
import { sileo } from 'sileo';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { API_ENDPOINTS } from '@/constants';
import { Github, Mail } from 'lucide-react'; // Simulating Google/Apple icons with mail/github for now

const loginSchema = z.object({
  email: z.string().email('Please enter a valid email address'),
  password: z.string().min(1, 'Password is required'),
});

type LoginForm = z.infer<typeof loginSchema>;

export default function LoginPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const callbackUrl = searchParams?.get('callbackUrl') || '/dashboard';
  const { setAuth, setMfaToken } = useAuthStore();
  const [isLoading, setIsLoading] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginForm>({
    resolver: zodResolver(loginSchema),
  });

  const onSubmit = async (data: LoginForm) => {
    setIsLoading(true);
    try {
      // Step 1: Call identify or login endpoint depending on the backend
      // Assuming Kraivor backend uses /auth/login for direct token, or /auth/signin/password
      const response = await apiClient.post(API_ENDPOINTS.AUTH.PASSWORD || '/auth/login', {
        email: data.email,
        password: data.password,
      });

      const { user, access, mfa_required, mfa_token } = response.data;

      if (mfa_required && mfa_token) {
        setMfaToken(mfa_token);
        router.push('/mfa/verify');
        return;
      }

      setAuth(user, access);
      sileo.success('Welcome back!');
      router.push(callbackUrl);
    } catch (error: any) {
      sileo.error(error.message || 'Invalid credentials');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <AuthLayout title="Welcome back" subtitle="Sign in to your Kraivor account">
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <AuthInput
          label="Email Address"
          type="email"
          placeholder="you@company.com"
          {...register('email')}
          error={errors.email?.message}
        />
        <div className="space-y-1">
          <div className="flex items-center justify-between">
            <label className="text-sm font-medium text-gray-300">Password</label>
            <Link
              href="/forgot-password"
              className="text-xs text-primary hover:text-primary/80 transition-colors"
            >
              Forgot password?
            </Link>
          </div>
          <AuthInput
            type="password"
            placeholder="••••••••"
            {...register('password')}
            error={errors.password?.message}
          />
        </div>

        <AuthButton type="submit" isLoading={isLoading} className="mt-6">
          Sign In
        </AuthButton>
      </form>

      <div className="mt-8">
        <div className="relative">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t border-white/10"></div>
          </div>
          <div className="relative flex justify-center text-xs uppercase">
            <span className="bg-[#111111] px-2 text-gray-500">Or continue with</span>
          </div>
        </div>

        <div className="mt-6 grid grid-cols-2 gap-3">
          <AuthButton variant="oauth" icon={<Github className="w-4 h-4" />} onClick={() => sileo.info('OAuth coming soon')}>
            GitHub
          </AuthButton>
          <AuthButton variant="oauth" icon={<Mail className="w-4 h-4" />} onClick={() => sileo.info('OAuth coming soon')}>
            Google
          </AuthButton>
        </div>
      </div>

      <p className="mt-8 text-center text-sm text-gray-400">
        Don't have an account?{' '}
        <Link href="/register" className="text-primary hover:underline font-medium">
          Sign up
        </Link>
      </p>
    </AuthLayout>
  );
}

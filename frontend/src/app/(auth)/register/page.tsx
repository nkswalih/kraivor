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
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { API_ENDPOINTS } from '@/constants';
import { Github, Mail } from 'lucide-react';

const registerSchema = z.object({
  firstName: z.string().min(2, 'First name is required'),
  lastName: z.string().min(2, 'Last name is required'),
  email: z.string().email('Please enter a valid email address'),
  password: z.string().min(8, 'Password must be at least 8 characters'),
});

type RegisterForm = z.infer<typeof registerSchema>;

export default function RegisterPage() {
  const router = useRouter();
  const [isLoading, setIsLoading] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<RegisterForm>({
    resolver: zodResolver(registerSchema),
  });

  const onSubmit = async (data: RegisterForm) => {
    setIsLoading(true);
    try {
      await apiClient.post(API_ENDPOINTS.AUTH.REGISTER || '/auth/register', {
        first_name: data.firstName,
        last_name: data.lastName,
        email: data.email,
        password: data.password,
      });

      sileo.success('Account created! Please check your email to verify.');
      router.push('/verify-email?email=' + encodeURIComponent(data.email));
    } catch (error: any) {
      sileo.error(error.message || 'Failed to create account');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <AuthLayout title="Create an account" subtitle="Start building with Kraivor today">
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <AuthInput
            label="First Name"
            placeholder="John"
            {...register('firstName')}
            error={errors.firstName?.message}
          />
          <AuthInput
            label="Last Name"
            placeholder="Doe"
            {...register('lastName')}
            error={errors.lastName?.message}
          />
        </div>
        
        <AuthInput
          label="Email Address"
          type="email"
          placeholder="you@company.com"
          {...register('email')}
          error={errors.email?.message}
        />
        
        <AuthInput
          label="Password"
          type="password"
          placeholder="••••••••"
          {...register('password')}
          error={errors.password?.message}
        />

        <AuthButton type="submit" isLoading={isLoading} className="mt-6">
          Create Account
        </AuthButton>
      </form>

      <div className="mt-8">
        <div className="relative">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t border-white/10"></div>
          </div>
          <div className="relative flex justify-center text-xs uppercase">
            <span className="bg-[#111111] px-2 text-gray-500">Or sign up with</span>
          </div>
        </div>

        <div className="mt-6 grid grid-cols-2 gap-3">
          <AuthButton variant="oauth" icon={<Github className="w-4 h-4" />}>
            GitHub
          </AuthButton>
          <AuthButton variant="oauth" icon={<Mail className="w-4 h-4" />}>
            Google
          </AuthButton>
        </div>
      </div>

      <p className="mt-8 text-center text-sm text-gray-400">
        Already have an account?{' '}
        <Link href="/login" className="text-primary hover:underline font-medium">
          Sign in
        </Link>
      </p>
    </AuthLayout>
  );
}

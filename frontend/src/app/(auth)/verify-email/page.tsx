'use client';

import React, { useState } from 'react';
import { AuthLayout } from '@/components/layouts/AuthLayout';
import { AuthButton } from '@/components/auth/AuthButton';
import { OtpInput } from '@/components/auth/OtpInput';
import { apiClient } from '@/lib/api-client';
import { sileo } from 'sileo';
import { useRouter, useSearchParams } from 'next/navigation';
import { API_ENDPOINTS } from '@/constants';
import { MailCheck } from 'lucide-react';

export default function VerifyEmailPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const email = searchParams?.get('email') || '';
  const [otp, setOtp] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isResending, setIsResending] = useState(false);

  const handleVerify = async () => {
    if (otp.length !== 6) return;

    setIsLoading(true);
    try {
      await apiClient.post(API_ENDPOINTS.AUTH.VERIFY_EMAIL || '/auth/verify-email', {
        email,
        code: otp,
      });

      sileo.success('Email verified successfully! You can now log in.');
      router.push('/login');
    } catch (error: any) {
      sileo.error(error.message || 'Invalid verification code');
      setOtp('');
    } finally {
      setIsLoading(false);
    }
  };

  const handleResend = async () => {
    if (!email) {
      sileo.error('Email parameter missing');
      return;
    }
    setIsResending(true);
    try {
      // Kraivor backend might have a resend endpoint, standard is usually something like this:
      await apiClient.post('/auth/resend-verification', { email });
      sileo.success('Verification code resent');
    } catch (error: any) {
      sileo.error(error.message || 'Failed to resend code');
    } finally {
      setIsResending(false);
    }
  };

  return (
    <AuthLayout title="Verify your email" subtitle={`We sent a 6-digit code to ${email || 'your email'}`}>
      <div className="flex flex-col items-center space-y-6">
        <div className="w-16 h-16 bg-primary/10 rounded-full flex items-center justify-center mb-2">
          <MailCheck className="w-8 h-8 text-primary" />
        </div>
        
        <OtpInput 
          value={otp} 
          onChange={(val) => {
            setOtp(val);
          }} 
          length={6} 
          disabled={isLoading}
        />

        <AuthButton 
          onClick={handleVerify} 
          isLoading={isLoading} 
          disabled={otp.length !== 6 || !email}
          className="mt-6"
        >
          Verify Email
        </AuthButton>

        <p className="text-sm text-gray-500 text-center mt-4">
          Didn't receive the code? <br/>
          <button 
            onClick={handleResend}
            disabled={isResending || !email}
            className="text-primary hover:underline mt-1 disabled:opacity-50"
          >
            {isResending ? 'Sending...' : 'Click to resend'}
          </button>
        </p>
      </div>
    </AuthLayout>
  );
}


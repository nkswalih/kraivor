'use client';

import React, { useState, useEffect } from 'react';
import { AuthLayout } from '@/components/layouts/AuthLayout';
import { AuthButton } from '@/components/auth/AuthButton';
import { OtpInput } from '@/components/auth/OtpInput';
import { apiClient } from '@/lib/api-client';
import { useAuthStore } from '@/store/auth.store';
import { sileo } from 'sileo';
import { useRouter } from 'next/navigation';
import { API_ENDPOINTS } from '@/constants';
import { ShieldCheck } from 'lucide-react';

export default function MfaVerifyPage() {
  const router = useRouter();
  const { mfaToken, setAuth } = useAuthStore();
  const [otp, setOtp] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (!mfaToken) {
      sileo.error('Session expired. Please sign in again.');
      router.push('/login');
    }
  }, [mfaToken, router]);

  const handleVerify = async () => {
    if (otp.length !== 6) {
      sileo.error('Please enter a 6-digit code');
      return;
    }

    setIsLoading(true);
    try {
      const response = await apiClient.post(API_ENDPOINTS.AUTH.OTP_VERIFY || '/auth/otp/verify', {
        mfa_token: mfaToken,
        code: otp,
      });

      const { user, access } = response.data;
      setAuth(user, access);
      sileo.success('Verification successful!');
      router.push('/dashboard');
    } catch (error: any) {
      sileo.error(error.message || 'Invalid verification code');
      setOtp('');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <AuthLayout title="Two-Factor Authentication" subtitle="Enter the 6-digit code from your authenticator app">
      <div className="flex flex-col items-center space-y-6">
        <div className="w-16 h-16 bg-primary/10 rounded-full flex items-center justify-center mb-2">
          <ShieldCheck className="w-8 h-8 text-primary" />
        </div>
        
        <OtpInput 
          value={otp} 
          onChange={(val) => {
            setOtp(val);
            if (val.length === 6) {
              // Auto-submit could be triggered here if desired, but button is safer
            }
          }} 
          length={6} 
          disabled={isLoading}
        />

        <AuthButton 
          onClick={handleVerify} 
          isLoading={isLoading} 
          disabled={otp.length !== 6}
          className="mt-6"
        >
          Verify Code
        </AuthButton>

        <p className="text-sm text-gray-500 text-center mt-4">
          Lost access to your device? <br/>
          <button className="text-primary hover:underline mt-1">Use a recovery code</button>
        </p>
      </div>
    </AuthLayout>
  );
}


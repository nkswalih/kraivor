'use client';

import React, { useState } from 'react';
import { AuthButton } from '@/lib/auth/AuthButton';
import { OtpInput } from '@/lib/auth/OtpInput';
import { sileo } from 'sileo';
import { ShieldAlert, ShieldCheck } from 'lucide-react';
import { useAuthStore } from '@/stores/auth-stores';

export default function MfaSettingsPage() {
  const { user, updateUser } = useAuthStore();
  const isMfaEnabled = user?.mfa_enabled || false;
  
  const [isSettingUp, setIsSettingUp] = useState(false);
  const [otp, setOtp] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleEnableMfa = async () => {
    setIsLoading(true);
    // Simulate verifying code and enabling MFA
    setTimeout(() => {
      updateUser({ mfa_enabled: true });
      setIsSettingUp(false);
      setIsLoading(false);
      setOtp('');
      sileo.success({
        title: 'MFA Enabled',
        description: 'Two-factor authentication enabled successfully',
      });
    }, 1500);
  };

  const handleDisableMfa = async () => {
    setIsLoading(true);
    setTimeout(() => {
      updateUser({ mfa_enabled: false });
      setIsLoading(false);
    sileo.success({
        title: 'MFA Disabled',
        description: 'Two-factor authentication disabled',
    });
    }, 1000);
  };

  return (
    <div className="space-y-10">
      <div>
        <h2 className="text-xl font-semibold mb-1">Two-Factor Authentication</h2>
        <p className="text-sm text-gray-400">Add an extra layer of security to your Kraivor account.</p>
      </div>

      <div className="border-t border-white/10 pt-8">
        {!isMfaEnabled && !isSettingUp && (
          <div className="bg-white/[0.02] border border-white/5 rounded-xl p-6 flex flex-col sm:flex-row items-center gap-6 text-center sm:text-left">
            <div className="w-16 h-16 bg-red-500/10 rounded-full flex items-center justify-center shrink-0">
              <ShieldAlert className="w-8 h-8 text-red-500" />
            </div>
            <div className="flex-1">
              <h3 className="text-lg font-medium mb-1">MFA is not enabled</h3>
              <p className="text-sm text-gray-400">Your account is vulnerable. We highly recommend enabling two-factor authentication.</p>
            </div>
            <AuthButton onClick={() => setIsSettingUp(true)} className="w-auto px-6 whitespace-nowrap">
              Setup MFA
            </AuthButton>
          </div>
        )}

        {isMfaEnabled && (
          <div className="bg-primary/5 border border-primary/20 rounded-xl p-6 flex flex-col sm:flex-row items-center gap-6 text-center sm:text-left">
            <div className="w-16 h-16 bg-primary/20 rounded-full flex items-center justify-center shrink-0">
              <ShieldCheck className="w-8 h-8 text-primary" />
            </div>
            <div className="flex-1">
              <h3 className="text-lg font-medium mb-1 text-primary">MFA is enabled</h3>
              <p className="text-sm text-primary/70">Your account is secured with two-factor authentication.</p>
            </div>
            <AuthButton variant="secondary" onClick={handleDisableMfa} isLoading={isLoading} className="w-auto px-6 whitespace-nowrap border-red-500/30 text-red-400 hover:bg-red-500/10 hover:border-red-500/50">
              Disable
            </AuthButton>
          </div>
        )}

        {isSettingUp && (
          <div className="space-y-6">
            <h3 className="text-lg font-medium">Configure Authenticator App</h3>
            <p className="text-sm text-gray-400 max-w-xl">
              Scan the QR code with an authenticator app like 1Password, Authy, Microsoft Authenticator, or Google Authenticator.
            </p>
            
            <div className="flex flex-col sm:flex-row gap-8 items-start">
              <div className="bg-white p-4 rounded-xl shrink-0">
                <div className="w-40 h-40 bg-black/5 relative flex items-center justify-center">
                  <div className="absolute inset-2 border-[12px] border-black"></div>
                  <div className="absolute inset-10 bg-black"></div>
                  <div className="w-4 h-4 bg-white z-10"></div>
                </div>
              </div>
              
              <div className="flex-1 space-y-6 w-full">
                <div>
                  <p className="text-sm font-medium mb-2">Or enter this code manually:</p>
                  <code className="bg-[#151515] border border-white/10 px-4 py-2 rounded-lg text-primary font-mono text-sm tracking-wider block w-fit">
                    KRVR-73A9-M4BQ-8X1L
                  </code>
                </div>
                
                <div className="border-t border-white/10 pt-6">
                  <p className="text-sm font-medium mb-4">Enter the 6-digit code from your app</p>
                  <OtpInput 
                    value={otp} 
                    onChange={setOtp} 
                    length={6} 
                  />
                  <div className="flex gap-3 mt-6">
                    <AuthButton onClick={handleEnableMfa} isLoading={isLoading} disabled={otp.length !== 6}>
                      Verify & Enable
                    </AuthButton>
                    <AuthButton variant="secondary" onClick={() => { setIsSettingUp(false); setOtp(''); }} disabled={isLoading}>
                      Cancel
                    </AuthButton>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}


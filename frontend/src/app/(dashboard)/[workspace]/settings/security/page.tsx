'use client';

import React, { useState } from 'react';
import { AuthButton } from '@/lib/auth/AuthButton';
import { AuthInput } from '@/lib/auth/AuthInput';
import { sileo } from 'sileo';
import { Laptop, Smartphone, Globe } from 'lucide-react';

export default function SecuritySettingsPage() {
  const [isLoading, setIsLoading] = useState(false);

  const handlePasswordChange = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    // Simulate API call
    setTimeout(() => {
      sileo.success({
        title: 'Password Updated',
        description: 'Password updated successfully',
      });
      setIsLoading(false);
    }, 1000);
  };

  const sessions = [
    { id: 1, device: 'MacBook Pro', location: 'San Francisco, CA', time: 'Active now', current: true, icon: Laptop },
    { id: 2, device: 'iPhone 13', location: 'San Francisco, CA', time: '2 hours ago', current: false, icon: Smartphone },
    { id: 3, device: 'Chrome on Windows', location: 'New York, NY', time: 'Yesterday', current: false, icon: Globe },
  ];

  return (
    <div className="space-y-10">
      <div>
        <h2 className="text-xl font-semibold mb-1">Security</h2>
        <p className="text-sm text-gray-400">Manage your password and secure your account.</p>
      </div>

      <div className="border-t border-white/10 pt-8">
        <h3 className="text-lg font-medium mb-4">Change Password</h3>
        <form onSubmit={handlePasswordChange} className="max-w-md space-y-4">
          <AuthInput type="password" label="Current Password" placeholder="••••••••" required />
          <AuthInput type="password" label="New Password" placeholder="••••••••" required />
          <AuthInput type="password" label="Confirm New Password" placeholder="••••••••" required />
          <AuthButton type="submit" isLoading={isLoading} className="w-auto px-6">
            Update Password
          </AuthButton>
        </form>
      </div>

      <div className="border-t border-white/10 pt-8">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-lg font-medium">Active Sessions</h3>
            <p className="text-sm text-gray-400">Devices that are currently logged into your account.</p>
          </div>
          <AuthButton variant="secondary" className="w-auto px-4 text-xs h-9" onClick={() => sileo.success({
                title: 'Devices Logged Out',
                description: 'All other devices logged out',
            })}>
            Log out all other devices
          </AuthButton>
        </div>

        <div className="space-y-3 mt-6">
          {sessions.map((session) => (
            <div key={session.id} className="flex items-center justify-between p-4 rounded-xl border border-white/5 bg-white/[0.02] hover:bg-white/[0.04] transition-colors">
              <div className="flex items-center gap-4">
                <div className="p-2.5 bg-[#151515] rounded-lg border border-white/10">
                  <session.icon className="w-5 h-5 text-gray-400" />
                </div>
                <div>
                  <p className="font-medium text-sm flex items-center gap-2">
                    {session.device}
                    {session.current && <span className="text-[10px] uppercase tracking-wider bg-primary/20 text-primary px-2 py-0.5 rounded-full">Current</span>}
                  </p>
                  <p className="text-xs text-gray-500">{session.location} • {session.time}</p>
                </div>
              </div>
              {!session.current && (
                <button className="text-xs text-gray-400 hover:text-red-400 transition-colors px-3 py-1.5 border border-white/10 hover:border-red-400/30 rounded-lg">
                  Revoke
                </button>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}


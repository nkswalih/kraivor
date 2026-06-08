'use client';

import { useState } from 'react';
import { Moon, Sun, Monitor, Check } from 'lucide-react';
import { useAuthStore } from '@/lib/stores/auth-store';
import { useUIStore, type Theme } from '@/lib/stores/ui-store';
import { cn } from '@/lib/utils';

/* ════════════════════════════════════════════════════════════════════
   SETTINGS PAGE — profile, theme, password only
   ════════════════════════════════════════════════════════════════════ */

export default function SettingsPage() {
  const user = useAuthStore(s => s.user);
  const theme = useUIStore(s => s.theme);
  const setTheme = useUIStore(s => s.setTheme);

  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [passwordSaved, setPasswordSaved] = useState(false);

  const themeOptions: { value: Theme; label: string; icon: typeof Sun }[] = [
    { value: 'dark', label: 'Dark', icon: Moon },
    { value: 'light', label: 'Light', icon: Sun },
    { value: 'system', label: 'System', icon: Monitor },
  ];

  const handlePasswordChange = () => {
    // TODO: wire to authApi.changePassword when backend endpoint is available
    setPasswordSaved(true);
    setCurrentPassword('');
    setNewPassword('');
    setConfirmPassword('');
    setTimeout(() => setPasswordSaved(false), 2000);
  };

  return (
    <div className="flex flex-1 min-h-0 w-full bg-[#0A0A0B] animate-fade-up text-[13px]">
      <div className="flex-1 overflow-y-auto p-8 max-w-[600px]">
        <h1 className="text-xl font-medium text-[#FAFAFA] mb-1">Settings</h1>
        <p className="text-[#A1A1AA] mb-8">Manage your profile, theme, and security.</p>

        {/* ── Account Info ─────────────────────────────────────── */}
        <Section title="Account">
          <div className="flex items-center gap-4 pb-6 border-b border-[#27272A] mb-6">
            <div className="w-12 h-12 rounded-[6px] bg-[#27272A] border border-[#27272A] flex items-center justify-center text-sm font-medium text-[#FAFAFA]">
              {user?.name ? user.name.charAt(0).toUpperCase() : 'U'}
            </div>
            <div>
              <p className="text-[#FAFAFA] font-medium">{user?.name || '—'}</p>
              <p className="text-[12px] text-[#A1A1AA]">{user?.email || '—'}</p>
            </div>
          </div>
        </Section>

        {/* ── Theme ────────────────────────────────────────────── */}
        <Section title="Theme">
          <div className="flex gap-2 mb-6 pb-6 border-b border-[#27272A]">
            {themeOptions.map(opt => {
              const Icon = opt.icon;
              const isActive = theme === opt.value;
              return (
                <button
                  key={opt.value}
                  onClick={() => setTheme(opt.value)}
                  className={cn(
                    "flex items-center gap-2 px-3 py-2 rounded-[6px] border transition-colors text-sm font-medium",
                    isActive
                      ? "border-[#6366F1] bg-[#6366F1]/10 text-[#FAFAFA]"
                      : "border-[#27272A] text-[#A1A1AA] hover:border-[#A1A1AA]/50"
                  )}
                >
                  <Icon className="w-4 h-4" />
                  {opt.label}
                </button>
              );
            })}
          </div>
        </Section>

        {/* ── Change Password ──────────────────────────────────── */}
        <Section title="Change Password">
          <div className="space-y-3 mb-6">
            <InputField
              label="Current Password"
              type="password"
              value={currentPassword}
              onChange={setCurrentPassword}
            />
            <InputField
              label="New Password"
              type="password"
              value={newPassword}
              onChange={setNewPassword}
            />
            <InputField
              label="Confirm New Password"
              type="password"
              value={confirmPassword}
              onChange={setConfirmPassword}
            />

            <div className="flex items-center gap-3">
              <button
                onClick={handlePasswordChange}
                disabled={!currentPassword || !newPassword || newPassword !== confirmPassword}
                className="bg-[#6366F1] hover:bg-[#4F46E5] text-white font-medium py-2 px-4 rounded-[6px] transition-colors text-sm disabled:opacity-50"
              >
                Update Password
              </button>
              {passwordSaved && (
                <span className="text-green-400 text-sm inline-flex items-center gap-1">
                  <Check className="w-3.5 h-3.5" /> Password updated
                </span>
              )}
            </div>
          </div>
        </Section>
      </div>
    </div>
  );
}

/* ─── Shared Components ────────────────────────────────────────── */

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="mb-6">
      <h2 className="text-sm font-medium text-[#FAFAFA] mb-3">{title}</h2>
      {children}
    </div>
  );
}

function InputField({
  label,
  value,
  onChange,
  type = 'text',
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  type?: string;
}) {
  return (
    <div className="space-y-1">
      <label className="block text-xs text-[#A1A1AA]">{label}</label>
      <input
        type={type}
        value={value}
        onChange={e => onChange(e.target.value)}
        className="w-full max-w-[400px] bg-[#111113] border border-[#27272A] rounded-[6px] px-3 py-2 text-[#FAFAFA] focus:outline-none focus:border-[#6366F1] transition-colors text-sm"
      />
    </div>
  );
}

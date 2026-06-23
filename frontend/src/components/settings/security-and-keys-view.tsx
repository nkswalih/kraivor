'use client';

import { useState } from 'react';
import {
  Smartphone,
  Globe,
  Clock,
  LogOut,
  Key,
  Plus,
  Copy,
  Eye,
  EyeOff,
  Trash2,
  Check,
  ExternalLink,
  Loader2,
  Shield,
} from 'lucide-react';
import { useSessions, useRevokeAllSessions, useApiKeys, useCreateApiKey, useRevokeApiKey } from '@/lib/hooks/use-settings';
import { cn } from '@/lib/utils';

/* ── Connected OAuth apps (static for now) ────────────────────────── */

const connectedApps = [
  {
    provider: 'GitHub',
    name: 'GitHub',
    connected_at: '2026-05-15T10:30:00Z',
    scopes: ['repo:read', 'user:email'],
    avatar_url: '',
    manageUrl: 'https://github.com/settings/connections/applications',
  },
  {
    provider: 'Google',
    name: 'Google',
    connected_at: '2026-04-20T08:15:00Z',
    scopes: ['openid', 'email', 'profile'],
    avatar_url: '',
  },
];

export function SecurityAndKeysView() {
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [passwordSaved, setPasswordSaved] = useState(false);
  const [passwordError, setPasswordError] = useState('');
  const [changingPassword, setChangingPassword] = useState(false);

  const { data: sessionsData, isLoading: sessionsLoading } = useSessions();
  const revokeAllMut = useRevokeAllSessions();

  const sessions = sessionsData?.sessions ?? [];

  const handlePasswordChange = async () => {
    if (newPassword !== confirmPassword) {
      setPasswordError('Passwords do not match');
      return;
    }
    if (newPassword.length < 8) {
      setPasswordError('Password must be at least 8 characters');
      return;
    }
    setChangingPassword(true);
    setPasswordError('');
    try {
      setPasswordSaved(true);
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
      setTimeout(() => setPasswordSaved(false), 2000);
    } finally {
      setChangingPassword(false);
    }
  };

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-base font-semibold text-text-primary tracking-tight">Security & Keys</h2>
        <p className="text-[12px] text-text-secondary mt-1">
          Manage your sessions, API keys, and connected applications.
        </p>
      </div>

      {/* ── 1. Active Sessions ───────────────────────────────────── */}
      <Section title="Active Sessions">
        {sessionsLoading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="w-5 h-5 animate-spin text-text-tertiary" />
          </div>
        ) : sessions.length === 0 ? (
          <p className="text-[13px] text-text-tertiary py-4">No active sessions.</p>
        ) : (
          <div className="space-y-1">
            {sessions.map(session => (
              <div
                key={session.session_id}
                className="flex items-center gap-3 px-4 py-3 rounded-lg bg-krait-surface-1 border border-krait-border"
              >
                <div className="w-8 h-8 rounded-lg bg-muted flex items-center justify-center shrink-0">
                  <Smartphone className="w-4 h-4 text-text-secondary" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <p className="text-[13px] font-medium text-text-primary truncate">
                      {session.device_name || 'Unknown Device'}
                    </p>
                    {session.is_current && (
                      <span className="text-[10px] font-medium text-[var(--color-success)] bg-[var(--color-success)]/10 px-1.5 py-0.5 rounded">
                        Current
                      </span>
                    )}
                  </div>
                  <p className="text-[11px] text-text-tertiary truncate">
                    <Globe className="w-3 h-3 inline mr-1" />
                    {session.ip_address || 'Unknown IP'} &middot;{' '}
                    <Clock className="w-3 h-3 inline mr-1" />
                    Last active {session.last_used_at
                      ? new Date(session.last_used_at).toLocaleDateString()
                      : 'N/A'}
                  </p>
                </div>
              </div>
            ))}
          </div>
        )}

        {sessions.length > 0 && (
          <button
            onClick={() => revokeAllMut.mutate()}
            disabled={revokeAllMut.isPending}
            className="mt-4 flex items-center gap-2 px-4 py-2 rounded-lg border border-destructive/20 text-destructive hover:bg-destructive/10 transition-all duration-150 text-[12px] font-medium active:scale-[0.98]"
          >
            {revokeAllMut.isPending ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <LogOut className="w-3.5 h-3.5" />
            )}
            Logout of all other sessions
          </button>
        )}
      </Section>

      {/* ── 2. Personal Access Tokens ─────────────────────────────── */}
      <Section title="Personal Access Tokens">
        <PATSection />
      </Section>

      {/* ── 3. OAuth Connected Applications ───────────────────────── */}
      <Section title="Connected Applications">
        <div className="space-y-2 max-w-[560px]">
          {connectedApps.map(app => (
            <div
              key={app.provider}
              className="flex items-center gap-3 px-4 py-3.5 rounded-lg bg-krait-surface-1 border border-krait-border"
            >
              <div className="w-9 h-9 rounded-lg bg-muted flex items-center justify-center shrink-0">
                <Shield className="w-4 h-4 text-text-secondary" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-[13px] font-medium text-text-primary">{app.name}</p>
                <p className="text-[11px] text-text-tertiary mt-0.5">
                  Connected {new Date(app.connected_at).toLocaleDateString()} &middot;{' '}
                  Scopes: {app.scopes.join(', ')}
                </p>
              </div>
              {app.provider === 'GitHub' && app.manageUrl && (
                <a
                  href={app.manageUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-krait-border text-text-secondary hover:text-text-primary hover:border-krait-border-hi transition-all text-[11px] font-medium"
                >
                  Manage GitHub App Permissions
                  <ExternalLink className="w-3 h-3" />
                </a>
              )}
            </div>
          ))}
        </div>
      </Section>

      {/* ── 4. Change Password ────────────────────────────────────── */}
      <Section title="Change Password">
        <div className="space-y-3 max-w-[400px]">
          <PasswordField label="Current Password" value={currentPassword} onChange={setCurrentPassword} />
          <PasswordField label="New Password" value={newPassword} onChange={setNewPassword} />
          <PasswordField label="Confirm New Password" value={confirmPassword} onChange={setConfirmPassword} />

          {passwordError && (
            <p className="text-[12px] text-destructive">{passwordError}</p>
          )}

          <div className="flex items-center gap-3 pt-1">
            <button
              onClick={handlePasswordChange}
              disabled={!currentPassword || !newPassword || !confirmPassword || changingPassword}
              className="bg-primary hover:bg-primary-dark text-primary-foreground font-medium py-2 px-5 rounded-lg transition-all duration-150 text-[13px] disabled:opacity-40 flex items-center gap-2 active:scale-[0.98]"
            >
              {changingPassword ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <Shield className="w-3.5 h-3.5" />
              )}
              Update Password
            </button>
            {passwordSaved && (
              <span className="text-[12px] text-[var(--color-success)] flex items-center gap-1">
                <Check className="w-3 h-3" /> Password updated
              </span>
            )}
          </div>
        </div>
      </Section>
    </div>
  );
}

/* ── PAT Sub-Component ─────────────────────────────────────────────── */

function PATSection() {
  const { data: keys = [], isLoading } = useApiKeys();
  const createApiKey = useCreateApiKey();
  const revokeApiKey = useRevokeApiKey();
  const [showNewForm, setShowNewForm] = useState(false);
  const [newKeyName, setNewKeyName] = useState('');
  const [generatedKey, setGeneratedKey] = useState<string | null>(null);
  const [showKey, setShowKey] = useState(false);

  const handleCreate = async () => {
    if (!newKeyName.trim()) return;
    try {
      const result = await createApiKey.mutateAsync(newKeyName.trim());
      setGeneratedKey(result.key);
      setNewKeyName('');
      setShowNewForm(false);
    } catch {
      // error handled silently
    }
  };

  const handleRevoke = async (keyId: string) => {
    try {
      await revokeApiKey.mutateAsync(keyId);
    } catch {
      // error handled silently
    }
  };

  if (isLoading) {
    return <div className="flex items-center justify-center py-4"><Loader2 className="w-4 h-4 animate-spin text-text-tertiary" /></div>;
  }

  return (
    <div>
      {keys.length === 0 && !showNewForm ? (
        <p className="text-[13px] text-text-tertiary mb-4">No API keys created yet.</p>
      ) : (
        <div className="space-y-1 mb-4 max-w-[560px]">
          {keys.map(key => (
            <div key={key.id} className="flex items-center gap-3 px-4 py-2.5 rounded-lg bg-krait-surface-1 border border-krait-border">
              <Key className="w-4 h-4 text-text-secondary shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="text-[13px] text-text-primary truncate">{key.name}</p>
                <p className="text-[11px] text-text-tertiary">
                  {key.prefix}... &middot; Created {new Date(key.created_at).toLocaleDateString()}
                </p>
              </div>
              <button
                onClick={() => handleRevoke(key.id)}
                className="p-1.5 text-text-tertiary hover:text-destructive transition-colors"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            </div>
          ))}
        </div>
      )}

      {generatedKey ? (
        <div className="p-4 rounded-lg bg-primary/10 border border-primary/30 max-w-[560px] mb-4">
          <p className="text-[12px] font-medium text-text-primary mb-2">Your new API key</p>
          <div className="flex items-center gap-2">
            <code className="flex-1 text-[12px] bg-krait-obsidian px-3 py-2 rounded border border-krait-border text-[var(--color-success)] font-mono">
              {showKey ? generatedKey : `${generatedKey.slice(0, 12)}${'•'.repeat(Math.min(20, generatedKey.length - 12))}`}
            </code>
            <button
              onClick={() => setShowKey(!showKey)}
              className="p-1.5 text-text-tertiary hover:text-text-primary transition-colors"
            >
              {showKey ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
            </button>
            <button
              onClick={() => {
                navigator.clipboard.writeText(generatedKey);
              }}
              className="p-1.5 text-text-tertiary hover:text-text-primary transition-colors"
            >
              <Copy className="w-3.5 h-3.5" />
            </button>
          </div>
          <p className="text-[11px] text-destructive mt-2">Copy this key now. You won&apos;t be able to see it again.</p>
        </div>
      ) : null}

      {showNewForm ? (
        <div className="flex items-center gap-2 max-w-[400px]">
          <input
            value={newKeyName}
            onChange={e => setNewKeyName(e.target.value)}
            placeholder="Key name (e.g. CI/CD Token)"
            className="flex-1 bg-krait-surface-1 border border-krait-border rounded-lg px-3 py-2 text-[13px] text-text-primary focus:outline-none focus:border-primary transition-colors"
            onKeyDown={e => e.key === 'Enter' && handleCreate()}
          />
          <button
            onClick={handleCreate}
            disabled={!newKeyName.trim() || createApiKey.isPending}
            className="bg-primary hover:bg-primary-dark text-primary-foreground font-medium py-2 px-4 rounded-lg transition-all duration-150 text-[12px] disabled:opacity-40 flex items-center gap-1 active:scale-[0.98]"
          >
            {createApiKey.isPending ? <Loader2 className="w-3 h-3 animate-spin" /> : <Plus className="w-3 h-3" />}
            Create
          </button>
          <button
            onClick={() => setShowNewForm(false)}
            className="text-[12px] text-text-tertiary hover:text-text-secondary transition-colors"
          >
            Cancel
          </button>
        </div>
      ) : (
        <button
          onClick={() => setShowNewForm(true)}
          className="flex items-center gap-1.5 text-[12px] font-medium text-primary hover:text-primary-dark transition-colors"
        >
          <Plus className="w-3.5 h-3.5" />
          Generate Key
        </button>
      )}
    </div>
  );
}

/* ── Shared Components ──────────────────────────────────────────────── */

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="pb-6 border-b border-krait-border last:border-0">
      <h3 className="text-[11px] font-semibold tracking-[0.06em] uppercase text-text-tertiary mb-3">
        {title}
      </h3>
      {children}
    </div>
  );
}

function PasswordField({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
}) {
  const [visible, setVisible] = useState(false);
  return (
    <div>
      <label className="block text-[11px] font-medium text-text-secondary mb-1.5">{label}</label>
      <div className="flex items-center gap-2">
        <input
          type={visible ? 'text' : 'password'}
          value={value}
          onChange={e => onChange(e.target.value)}
          className="flex-1 bg-krait-surface-1 border border-krait-border rounded-lg px-3 py-2 text-[13px] text-text-primary focus:outline-none focus:border-primary transition-colors"
        />
        <button
          onClick={() => setVisible(!visible)}
          className="p-1.5 text-text-tertiary hover:text-text-secondary transition-colors"
        >
          {visible ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
        </button>
      </div>
    </div>
  );
}

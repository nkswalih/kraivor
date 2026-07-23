'use client';

import { useState } from 'react';
import { Check, Bell } from 'lucide-react';
import { cn } from '@/lib/utils';

export function InboxView() {
  const [notificationsEnabled, setNotificationsEnabled] = useState(true);
  const [emailNotifs, setEmailNotifs] = useState(true);
  const [pushNotifs, setPushNotifs] = useState(true);
  const [desktopNotifs, setDesktopNotifs] = useState(false);
  const [frequency, setFrequency] = useState('realtime');
  const [saved, setSaved] = useState(false);

  const handleSave = () => {
    setSaved(true);
    setTimeout(() => setSaved(false), 1500);
  };

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-base font-semibold text-text-primary tracking-tight">Inbox & Notifications</h2>
        <p className="text-[12px] text-text-secondary mt-1">
          Configure how and when you receive notifications.
        </p>
      </div>

      <Section title="Notification Channels">
        <div className="space-y-3 max-w-[480px]">
          <ToggleRow label="Email notifications" description="Receive updates via email" enabled={emailNotifs} onChange={setEmailNotifs} />
          <ToggleRow label="Push notifications" description="Push alerts to your browser" enabled={pushNotifs} onChange={setPushNotifs} />
          <ToggleRow label="Desktop notifications" description="System-level desktop alerts" enabled={desktopNotifs} onChange={setDesktopNotifs} />
        </div>
      </Section>

      <Section title="Digest Frequency">
        <select
          value={frequency}
          onChange={e => setFrequency(e.target.value)}
          className="w-full max-w-[320px] bg-krait-surface-1 border border-krait-border rounded-lg px-3 py-2 text-[13px] text-text-primary focus:outline-none focus:border-primary transition-colors"
        >
          <option value="realtime">Real-time</option>
          <option value="hourly">Hourly digest</option>
          <option value="daily">Daily digest</option>
          <option value="never">Never (pause all)</option>
        </select>
      </Section>

      <Section title="Notification Triggers">
        <div className="space-y-2 max-w-[480px]">
          <ToggleRow label="AI analysis complete" description="When a repository analysis finishes" enabled={notificationsEnabled} onChange={setNotificationsEnabled} />
          <ToggleRow label="Team member activity" description="New members, role changes, invitations" enabled={notificationsEnabled} onChange={setNotificationsEnabled} />
          <ToggleRow label="Mentions & comments" description="When someone mentions you or replies" enabled={notificationsEnabled} onChange={setNotificationsEnabled} />
        </div>
      </Section>

      <Section title="Inbox Appearance">
        <div className="flex items-center justify-between max-w-[320px]">
          <div>
            <p className="text-[13px] text-text-secondary">Unread badge on sidebar</p>
            <p className="text-[11px] text-text-tertiary">Show notification count in navigation</p>
          </div>
          <button
            onClick={() => setNotificationsEnabled(!notificationsEnabled)}
            className={cn(
              'relative w-9 h-5 rounded-full transition-colors duration-200',
              notificationsEnabled ? 'bg-primary' : 'bg-muted'
            )}
          >
            <div
              className={cn(
                'absolute top-0.5 w-4 h-4 rounded-full bg-white transition-transform duration-200',
                notificationsEnabled ? 'translate-x-[18px]' : 'translate-x-[2px]'
              )}
            />
          </button>
        </div>
      </Section>

      <div className="flex items-center gap-3 pt-2">
        <button
          onClick={handleSave}
          className="bg-primary hover:bg-primary-dark text-primary-foreground font-medium py-2 px-5 rounded-lg transition-all duration-150 text-[13px] flex items-center gap-2 active:scale-[0.98]"
        >
          <Bell className="w-3.5 h-3.5" />
          Save Notification Settings
        </button>
        {saved && (
          <span className="text-[12px] text-[var(--color-success)] flex items-center gap-1">
            <Check className="w-3 h-3" /> Saved
          </span>
        )}
      </div>
    </div>
  );
}

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

function ToggleRow({
  label,
  description,
  enabled,
  onChange,
}: {
  label: string;
  description: string;
  enabled: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <div className="flex items-center justify-between py-2">
      <div>
        <p className="text-[13px] text-text-secondary">{label}</p>
        <p className="text-[11px] text-text-tertiary">{description}</p>
      </div>
      <button
        onClick={() => onChange(!enabled)}
        className={cn(
          'relative w-9 h-5 rounded-full transition-colors duration-200 shrink-0',
          enabled ? 'bg-primary' : 'bg-muted'
        )}
      >
        <div
          className={cn(
            'absolute top-0.5 w-4 h-4 rounded-full bg-white transition-transform duration-200',
            enabled ? 'translate-x-[18px]' : 'translate-x-[2px]'
          )}
        />
      </button>
    </div>
  );
}

'use client';

import { useEffect, useState } from 'react';
import { Moon, Sun, Monitor, Check } from 'lucide-react';
import { useTheme } from 'next-themes';
import { useUIStore, type Theme } from '@/lib/stores/ui-store';
import { cn } from '@/lib/utils';

const themeOptions: { value: Theme; label: string; icon: typeof Sun }[] = [
  { value: 'dark', label: 'Dark', icon: Moon },
  { value: 'light', label: 'Light', icon: Sun },
  { value: 'system', label: 'System', icon: Monitor },
];

export function PreferencesView() {
  const { theme: currentTheme, setTheme: setNextTheme } = useTheme();
  const storeTheme = useUIStore(s => s.theme);
  const setStoreTheme = useUIStore(s => s.setTheme);
  const [saved, setSaved] = useState(false);
  const [emojiTranslation, setEmojiTranslation] = useState(true);
  const [defaultHomeView, setDefaultHomeView] = useState('dashboard');

  useEffect(() => {
    if (storeTheme) {
      setNextTheme(storeTheme);
    }
  }, []);

  const handleThemeChange = (t: Theme) => {
    setStoreTheme(t);
    setNextTheme(t);
    setSaved(true);
    setTimeout(() => setSaved(false), 1500);
  };

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-base font-semibold text-text-primary tracking-tight">Preferences</h2>
        <p className="text-[12px] text-text-secondary mt-1">Customize your Kraivor experience.</p>
      </div>

      <Section title="Appearance">
        <div className="flex items-center gap-2">
          {themeOptions.map(opt => {
            const Icon = opt.icon;
            const isActive = storeTheme === opt.value;
            return (
              <button
                key={opt.value}
                onClick={() => handleThemeChange(opt.value)}
                className={cn(
                  'flex items-center gap-2 px-3.5 py-2 rounded-lg border transition-all duration-150 text-sm font-medium',
                  isActive
                    ? 'border-primary bg-primary/10 text-text-primary'
                    : 'border-krait-border text-text-secondary hover:border-krait-border-hi hover:text-text-secondary bg-krait-surface-1'
                )}
              >
                <Icon className="w-4 h-4" />
                {opt.label}
              </button>
            );
          })}
          {saved && (
            <span className="text-[11px] text-[var(--color-success)] flex items-center gap-1 ml-2">
              <Check className="w-3 h-3" /> Saved
            </span>
          )}
        </div>
      </Section>

      <Section title="Default Home View">
        <select
          value={defaultHomeView}
          onChange={e => setDefaultHomeView(e.target.value)}
          className="w-full max-w-[320px] bg-krait-surface-1 border border-krait-border rounded-lg px-3 py-2 text-[13px] text-text-primary focus:outline-none focus:border-primary transition-colors"
        >
          <option value="dashboard">Dashboard</option>
          <option value="projects">Projects</option>
          <option value="repositories">Repositories</option>
          <option value="ai">AI Workspace</option>
          <option value="chat">Chat</option>
        </select>
      </Section>

      <Section title="Emoji Translation">
        <div className="flex items-center justify-between max-w-[320px]">
          <p className="text-[13px] text-text-secondary">Convert emoji shortcodes like <code className="text-[11px] bg-muted px-1.5 py-0.5 rounded text-text-secondary">:rocket:</code></p>
          <button
            onClick={() => setEmojiTranslation(!emojiTranslation)}
            className={cn(
              'relative w-9 h-5 rounded-full transition-colors duration-200',
              emojiTranslation ? 'bg-primary' : 'bg-muted'
            )}
          >
            <div
              className={cn(
                'absolute top-0.5 w-4 h-4 rounded-full bg-white transition-transform duration-200',
                emojiTranslation ? 'translate-x-[18px]' : 'translate-x-[2px]'
              )}
            />
          </button>
        </div>
      </Section>
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

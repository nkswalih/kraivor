'use client';

import { useState, useRef, useEffect } from 'react';
import { Camera, Loader2, Check, AlertCircle } from 'lucide-react';
import { useAuthStore } from '@/lib/stores/auth-store';
import { useMyProfile, useUpdateProfile, useUploadProfileImage } from '@/lib/hooks/use-settings';
import { cn } from '@/lib/utils';

export function ProfileView() {
  const user = useAuthStore(s => s.user);
  const { data: profile, isLoading: profileLoading } = useMyProfile();
  const updateProfile = useUpdateProfile();
  const uploadImage = useUploadProfileImage();
  const avatarInputRef = useRef<HTMLInputElement>(null);
  const bannerInputRef = useRef<HTMLInputElement>(null);

  const [displayName, setDisplayName] = useState('');
  const [username, setUsername] = useState('');
  const [bio, setBio] = useState('');
  const [location, setLocation] = useState('');
  const [websiteUrl, setWebsiteUrl] = useState('');
  const [githubUsername, setGithubUsername] = useState('');
  const [twitterUsername, setTwitterUsername] = useState('');
  const [linkedinUrl, setLinkedinUrl] = useState('');
  const [isPublic, setIsPublic] = useState(true);
  const [avatarUrl, setAvatarUrl] = useState('');
  const [bannerUrl, setBannerUrl] = useState('');
  const [saved, setSaved] = useState(false);
  const [uploading, setUploading] = useState<'avatar' | 'banner' | null>(null);

  useEffect(() => {
    if (profile) {
      setDisplayName(profile.display_name || user?.name || '');
      setUsername(profile.username || '');
      setBio(profile.bio || '');
      setLocation(profile.location || '');
      setWebsiteUrl(profile.website_url || '');
      setGithubUsername(profile.github_username || '');
      setTwitterUsername(profile.twitter_username || '');
      setLinkedinUrl(profile.linkedin_url || '');
      setIsPublic(profile.is_public ?? true);
      setAvatarUrl(profile.avatar_url || profile.user_avatar_url || '');
      setBannerUrl(profile.banner_url || '');
    }
  }, [profile, user]);

  const handleImageUpload = async (field: 'avatar' | 'banner', file: File) => {
    setUploading(field);
    try {
      const result = await uploadImage.mutateAsync({ field, file });
      if (field === 'avatar') setAvatarUrl(result.url);
      else setBannerUrl(result.url);
    } catch {
      // handled by mutation error state
    } finally {
      setUploading(null);
    }
  };

  const handleFileSelect = (field: 'avatar' | 'banner') => (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleImageUpload(field, file);
  };

  const handleSave = async () => {
    try {
      await updateProfile.mutateAsync({
        username: profile?.username || username,
        display_name: displayName,
        bio,
        location,
        website_url: websiteUrl,
        github_username: githubUsername,
        twitter_username: twitterUsername,
        linkedin_url: linkedinUrl,
        is_public: isPublic,
        avatar_url: avatarUrl,
        banner_url: bannerUrl,
      });
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch {
      // handled by mutation
    }
  };

  const hasChanges = profile && (
    displayName !== (profile.display_name || user?.name || '') ||
    username !== (profile.username || '') ||
    bio !== (profile.bio || '') ||
    location !== (profile.location || '') ||
    websiteUrl !== (profile.website_url || '') ||
    githubUsername !== (profile.github_username || '') ||
    twitterUsername !== (profile.twitter_username || '') ||
    linkedinUrl !== (profile.linkedin_url || '') ||
    isPublic !== (profile.is_public ?? true)
  );

  if (profileLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="w-5 h-5 animate-spin text-[#6b6b70]" />
      </div>
    );
  }

  const displayNameVal = displayName || user?.name || '';
  const avatarInitial = displayNameVal.charAt(0).toUpperCase() || 'U';

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-base font-semibold text-text-primary tracking-tight">Profile</h2>
        <p className="text-[12px] text-text-secondary mt-1">Manage your public profile information.</p>
      </div>

      {/* Avatar + Banner Upload */}
      <Section title="Profile Photo & Banner">
        <div className="space-y-4">
          {/* Banner Preview */}
          <div
            className="relative w-full h-32 rounded-lg bg-krait-surface-1 border border-krait-border overflow-hidden group cursor-pointer"
            onClick={() => bannerInputRef.current?.click()}
          >
            {bannerUrl ? (
              <img src={bannerUrl} alt="" className="w-full h-full object-cover" />
            ) : (
              <div className="w-full h-full flex items-center justify-center text-text-tertiary text-[11px]">Banner</div>
            )}
            <div className="absolute inset-0 bg-black/0 group-hover:bg-black/40 transition-colors flex items-center justify-center">
              <Camera className="w-5 h-5 text-white opacity-0 group-hover:opacity-100 transition-opacity" />
            </div>
            {uploading === 'banner' && (
              <div className="absolute inset-0 bg-black/60 flex items-center justify-center">
                <Loader2 className="w-5 h-5 animate-spin text-white" />
              </div>
            )}
            <input ref={bannerInputRef} type="file" accept="image/png,image/jpeg,image/webp" className="hidden" onChange={handleFileSelect('banner')} />
          </div>

          <div className="flex items-end gap-4 -mt-10 pl-4">
            <div className="relative group cursor-pointer" onClick={() => avatarInputRef.current?.click()}>
              {avatarUrl ? (
                <img src={avatarUrl} alt="" className="w-20 h-20 rounded-lg border-2 border-krait-obsidian object-cover" />
              ) : (
                <div className="w-20 h-20 rounded-lg border-2 border-krait-obsidian bg-muted flex items-center justify-center text-2xl font-bold text-text-primary">
                  {avatarInitial}
                </div>
              )}
              <div className="absolute inset-0 bg-black/0 group-hover:bg-black/40 rounded-lg transition-colors flex items-center justify-center">
                <Camera className="w-5 h-5 text-white opacity-0 group-hover:opacity-100 transition-opacity" />
              </div>
              {uploading === 'avatar' && (
                <div className="absolute inset-0 bg-black/60 rounded-lg flex items-center justify-center">
                  <Loader2 className="w-5 h-5 animate-spin text-white" />
                </div>
              )}
              <input ref={avatarInputRef} type="file" accept="image/png,image/jpeg,image/webp" className="hidden" onChange={handleFileSelect('avatar')} />
            </div>
          </div>
        </div>
      </Section>

      <Section title="Display Information">
        <div className="grid grid-cols-2 gap-4 max-w-[560px]">
          <Field label="Display Name" value={displayName} onChange={setDisplayName} />
          <Field label="Username" value={username} onChange={setUsername} />
        </div>
        <div className="mt-4 max-w-[560px]">
          <label className="block text-[11px] font-medium text-text-secondary mb-1.5">Bio</label>
          <textarea
            value={bio}
            onChange={e => setBio(e.target.value)}
            rows={3}
            className="w-full bg-krait-surface-1 border border-krait-border rounded-lg px-3 py-2 text-[13px] text-text-primary focus:outline-none focus:border-primary transition-colors resize-none"
          />
        </div>
      </Section>

      <Section title="Links & Social">
        <div className="space-y-3 max-w-[560px]">
          <Field label="Website" value={websiteUrl} onChange={setWebsiteUrl} placeholder="https://" />
          <Field label="Location" value={location} onChange={setLocation} placeholder="City, Country" />
          <Field label="GitHub" value={githubUsername} onChange={setGithubUsername} placeholder="username" />
          <Field label="Twitter" value={twitterUsername} onChange={setTwitterUsername} placeholder="@username" />
          <Field label="LinkedIn" value={linkedinUrl} onChange={setLinkedinUrl} placeholder="https://linkedin.com/in/..." />
        </div>
      </Section>

      <Section title="Privacy">
        <div className="flex items-center justify-between max-w-[320px]">
          <div>
            <p className="text-[13px] text-text-secondary">Public profile</p>
            <p className="text-[11px] text-text-tertiary">Allow others to view your profile</p>
          </div>
          <button
            onClick={() => setIsPublic(!isPublic)}
            className={cn(
              'relative w-9 h-5 rounded-full transition-colors duration-200',
              isPublic ? 'bg-primary' : 'bg-muted'
            )}
          >
            <div
              className={cn(
                'absolute top-0.5 w-4 h-4 rounded-full bg-white transition-transform duration-200',
                isPublic ? 'translate-x-[18px]' : 'translate-x-[2px]'
              )}
            />
          </button>
        </div>
      </Section>

      <div className="flex items-center gap-3 pt-2">
        <button
          onClick={handleSave}
          disabled={updateProfile.isPending || !hasChanges || !username.trim() || !displayName.trim()}
          className="bg-primary hover:bg-primary-dark text-primary-foreground font-medium py-2 px-5 rounded-lg transition-all duration-150 text-[13px] disabled:opacity-40 flex items-center gap-2 active:scale-[0.98]"
        >
          {updateProfile.isPending ? (
            <Loader2 className="w-3.5 h-3.5 animate-spin" />
          ) : (
            <Check className="w-3.5 h-3.5" />
          )}
          {updateProfile.isPending ? 'Saving...' : 'Save Changes'}
        </button>
        {saved && (
          <span className="text-[12px] text-[var(--color-success)] flex items-center gap-1">
            <Check className="w-3 h-3" /> Saved
          </span>
        )}
        {updateProfile.isError && (
          <span className="text-[12px] text-destructive flex items-center gap-1">
            <AlertCircle className="w-3 h-3" /> Failed to save
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

function Field({
  label,
  value,
  onChange,
  placeholder,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
}) {
  return (
    <div>
      <label className="block text-[11px] font-medium text-text-secondary mb-1.5">{label}</label>
      <input
        value={value}
        onChange={e => onChange(e.target.value)}
        placeholder={placeholder}
        className="w-full bg-krait-surface-1 border border-krait-border rounded-lg px-3 py-2 text-[13px] text-text-primary focus:outline-none focus:border-primary transition-colors placeholder:text-text-tertiary"
      />
    </div>
  );
}

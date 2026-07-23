'use client';

import { useState, useRef, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { toast } from 'sonner';
import { useUpdateProfile, useUploadProfileImage } from '@/lib/hooks/use-profiles';
import { useAuthStore } from '@/lib/stores/auth-store';
import { Button } from '@/components/ui/shadcn';
import { Input } from '@/components/ui/shadcn';
import { Label } from '@/components/ui/shadcn';
import { Camera, Loader2, X } from 'lucide-react';

export function CreateProfileDialog() {
  const router = useRouter();
  const user = useAuthStore(s => s.user);
  const defaultUsername =
    user?.name?.toLowerCase().replace(/\s+/g, '_') || user?.email?.split('@')[0] || 'user';
  const updateMutation = useUpdateProfile();
  const uploadMutation = useUploadProfileImage();

  const [open, setOpen] = useState(true);
  const [formUsername, setFormUsername] = useState(defaultUsername);
  const [displayName, setDisplayName] = useState(user?.name || '');
  const [bio, setBio] = useState('');

  const [avatarFile, setAvatarFile] = useState<File | null>(null);
  const [avatarPreview, setAvatarPreview] = useState<string | null>(null);
  const [bannerFile, setBannerFile] = useState<File | null>(null);
  const [bannerPreview, setBannerPreview] = useState<string | null>(null);

  const avatarInputRef = useRef<HTMLInputElement>(null);
  const bannerInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!open) {
      document.body.style.overflow = '';
    } else {
      document.body.style.overflow = 'hidden';
    }
    return () => {
      document.body.style.overflow = '';
    };
  }, [open]);

  const handleAvatarSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setAvatarFile(file);
    setAvatarPreview(URL.createObjectURL(file));
  };

  const handleBannerSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setBannerFile(file);
    setBannerPreview(URL.createObjectURL(file));
  };

  const isSubmitting = updateMutation.isPending || uploadMutation.isPending;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!displayName.trim()) {
      toast.error('Display name is required');
      return;
    }

    try {
      let avatarUrl = '';
      let bannerUrl = '';

      if (avatarFile) {
        const result = await uploadMutation.mutateAsync({ field: 'avatar', file: avatarFile });
        avatarUrl = result.url;
      }

      if (bannerFile) {
        const result = await uploadMutation.mutateAsync({ field: 'banner', file: bannerFile });
        bannerUrl = result.url;
      }

      const result = await updateMutation.mutateAsync({
        id: formUsername,
        username: formUsername,
        display_name: displayName.trim(),
        bio: bio.trim() || undefined,
        avatar_url: avatarUrl || undefined,
        banner_url: bannerUrl || undefined,
      });

      toast.success('Profile created! Welcome to Kraivor.');
      setOpen(false);
      router.push(`/profile/${result.username}`);
      router.refresh();
    } catch {
      toast.error('Failed to create profile');
    }
  };

  const handleSkip = () => {
    setOpen(false);
    router.refresh();
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/60">
      <div className="bg-card border border-border rounded-xl shadow-2xl w-full max-w-lg mx-4 max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between px-6 pt-6 pb-2">
          <h2 className="text-lg font-semibold text-foreground">Set up your profile</h2>
          <button
            onClick={handleSkip}
            className="text-muted-foreground hover:text-foreground transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        <p className="px-6 pb-4 text-[13px] text-muted-foreground">
          Personalize your profile so the community can get to know you.
        </p>

        <form onSubmit={handleSubmit} className="px-6 pb-6 space-y-5">
          {/* Banner */}
          <div>
            <Label className="text-[13px] text-muted-foreground mb-2 block">Banner</Label>
            <div
              className="relative h-24 bg-gradient-to-r from-primary/20 via-primary/10 to-background rounded-lg overflow-hidden cursor-pointer group"
              onClick={() => bannerInputRef.current?.click()}
            >
              {bannerPreview && (
                <img src={bannerPreview} alt="" loading="lazy" className="w-full h-full object-cover" />
              )}
              <div className="absolute inset-0 bg-black/0 group-hover:bg-black/30 transition-colors flex items-center justify-center">
                <Camera className="w-5 h-5 text-white opacity-0 group-hover:opacity-100 transition-opacity" />
              </div>
            </div>
            <input
              ref={bannerInputRef}
              type="file"
              accept="image/png,image/jpeg,image/webp"
              className="hidden"
              onChange={handleBannerSelect}
            />
          </div>

          {/* Avatar */}
          <div className="flex items-center gap-4">
            <div
              className="relative w-20 h-20 rounded-full overflow-hidden cursor-pointer group shrink-0"
              onClick={() => avatarInputRef.current?.click()}
            >
              {avatarPreview ? (
                <img src={avatarPreview} alt="" loading="lazy" className="w-full h-full object-cover" />
              ) : (
                <div className="w-full h-full bg-muted flex items-center justify-center text-xl font-medium text-muted-foreground">
                  {(displayName || 'U')[0].toUpperCase()}
                </div>
              )}
              <div className="absolute inset-0 bg-black/0 group-hover:bg-black/30 transition-colors rounded-full flex items-center justify-center">
                <Camera className="w-5 h-5 text-white opacity-0 group-hover:opacity-100 transition-opacity" />
              </div>
            </div>
            <input
              ref={avatarInputRef}
              type="file"
              accept="image/png,image/jpeg,image/webp"
              className="hidden"
              onChange={handleAvatarSelect}
            />
            <div>
              <p className="text-sm font-medium text-foreground">{displayName || 'Your Name'}</p>
              <p className="text-[12px] text-muted-foreground">@{formUsername}</p>
            </div>
          </div>

          {/* Display Name */}
          <div>
            <Label htmlFor="cd-displayName" className="text-[13px] text-muted-foreground">
              Display name *
            </Label>
            <Input
              id="cd-displayName"
              value={displayName}
              onChange={e => setDisplayName(e.target.value)}
              placeholder="Your name"
              className="mt-1"
              required
            />
          </div>

          {/* Username */}
          <div>
            <Label htmlFor="cd-username" className="text-[13px] text-muted-foreground">
              Username
            </Label>
            <Input
              id="cd-username"
              value={formUsername}
              onChange={e =>
                setFormUsername(e.target.value.toLowerCase().replace(/[^a-z0-9_]/g, ''))
              }
              placeholder="your_username"
              className="mt-1"
            />
          </div>

          {/* Bio */}
          <div>
            <Label htmlFor="cd-bio" className="text-[13px] text-muted-foreground">
              Bio
            </Label>
            <textarea
              id="cd-bio"
              value={bio}
              onChange={e => setBio(e.target.value)}
              placeholder="Tell us about yourself"
              className="mt-1 flex min-h-[72px] w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring resize-none"
              maxLength={1000}
            />
          </div>

          {/* Actions */}
          <div className="flex items-center gap-3 pt-2">
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
              {isSubmitting ? 'Saving...' : 'Create profile'}
            </Button>
            <Button type="button" variant="ghost" onClick={handleSkip}>
              Skip for now
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}

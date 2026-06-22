'use client';

import { useEffect, useState, useRef } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { toast } from 'sonner';
import {
  useMyProfile,
  useUpdateProfile,
  useUploadProfileImage,
  useCheckUsername,
} from '@/lib/hooks/use-profiles';
import { useAuth } from '@/lib/hooks';
import { Button } from '@/components/ui/shadcn';
import { Input } from '@/components/ui/shadcn';
import { Label } from '@/components/ui/shadcn';
import { Skeleton } from '@/components/ui/shadcn';
import { Camera, ArrowLeft, Loader2, Check, X } from 'lucide-react';

export default function EditProfilePage() {
  const params = useParams();
  const router = useRouter();
  const { user } = useAuth();
  const { data: profile, isLoading, isError } = useMyProfile();
  const updateMutation = useUpdateProfile();
  const uploadMutation = useUploadProfileImage();

  const [displayName, setDisplayName] = useState('');
  const [bio, setBio] = useState('');
  const [websiteUrl, setWebsiteUrl] = useState('');
  const [location, setLocation] = useState('');
  const [githubUsername, setGithubUsername] = useState('');
  const [twitterUsername, setTwitterUsername] = useState('');
  const [linkedinUrl, setLinkedinUrl] = useState('');
  const [isPublic, setIsPublic] = useState(true);

  const [avatarFile, setAvatarFile] = useState<File | null>(null);
  const [avatarPreview, setAvatarPreview] = useState<string | null>(null);
  const [bannerFile, setBannerFile] = useState<File | null>(null);
  const [bannerPreview, setBannerPreview] = useState<string | null>(null);

  const avatarInputRef = useRef<HTMLInputElement>(null);
  const bannerInputRef = useRef<HTMLInputElement>(null);

  const [editUsername, setEditUsername] = useState('');
  const usernameChanged = profile ? editUsername !== profile.username : false;
  const { data: usernameCheck } = useCheckUsername(usernameChanged ? editUsername : '');
  const usernameAvailable = usernameCheck?.available ?? true;

  useEffect(() => {
    if (profile) {
      setEditUsername(profile.username || '');
      setDisplayName(profile.display_name || '');
      setBio(profile.bio || '');
      setWebsiteUrl(profile.website_url || '');
      setLocation(profile.location || '');
      setGithubUsername(profile.github_username || '');
      setTwitterUsername(profile.twitter_username || '');
      setLinkedinUrl(profile.linkedin_url || '');
      setIsPublic(profile.is_public);
    }
  }, [profile]);

  useEffect(() => {
    if (!isLoading && !isError && profile && !profile.is_owner) {
      toast.error("You don't have permission to edit this profile.");
      router.replace(`/profile/${editUsername}`);
    }
  }, [isLoading, isError, profile, editUsername, router]);

  if (isLoading) {
    return (
      <div className="max-w-2xl mx-auto p-6 w-full space-y-4">
        <Skeleton className="h-8 w-32" />
        <Skeleton className="h-32 w-full rounded-lg" />
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-10 w-full" />
      </div>
    );
  }

  if (isError || !profile) {
    return (
      <div className="max-w-2xl mx-auto p-6 w-full text-center text-muted-foreground">
        Profile not found.
      </div>
    );
  }

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

    try {
      let avatarUrl = profile.avatar_url;
      let bannerUrl = profile.banner_url;

      if (avatarFile) {
        const result = await uploadMutation.mutateAsync({ field: 'avatar', file: avatarFile });
        avatarUrl = result.url;
      }

      if (bannerFile) {
        const result = await uploadMutation.mutateAsync({ field: 'banner', file: bannerFile });
        bannerUrl = result.url;
      }

      const result = await updateMutation.mutateAsync({
        username: editUsername,
        display_name: displayName || undefined,
        bio: bio || undefined,
        avatar_url: avatarUrl || undefined,
        banner_url: bannerUrl || undefined,
        website_url: websiteUrl || undefined,
        location: location || undefined,
        github_username: githubUsername || undefined,
        twitter_username: twitterUsername || undefined,
        linkedin_url: linkedinUrl || undefined,
        is_public: isPublic,
      });

      toast.success('Profile updated successfully');
      router.push(`/profile/${result.username}`);
    } catch {
      toast.error('Failed to update profile');
    }
  };

  return (
    <div className="max-w-2xl mx-auto p-6 w-full">
      <button
        onClick={() => router.push(`/profile/${editUsername}`)}
        className="flex items-center gap-1.5 text-[13px] text-muted-foreground hover:text-foreground mb-4 transition-colors"
      >
        <ArrowLeft className="w-4 h-4" />
        Back to profile
      </button>

      <h1 className="text-xl font-semibold text-foreground mb-6">Edit Profile</h1>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Banner */}
        <div>
          <Label className="text-[13px] text-muted-foreground mb-2 block">Banner</Label>
          <div
            className="relative h-32 bg-gradient-to-r from-primary/20 via-primary/10 to-background rounded-lg overflow-hidden cursor-pointer group"
            onClick={() => bannerInputRef.current?.click()}
          >
            {(bannerPreview || profile.banner_url) && (
              <img
                src={bannerPreview || profile.banner_url}
                alt=""
                className="w-full h-full object-cover"
              />
            )}
            <div className="absolute inset-0 bg-black/0 group-hover:bg-black/30 transition-colors flex items-center justify-center">
              <Camera className="w-6 h-6 text-white opacity-0 group-hover:opacity-100 transition-opacity" />
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
        <div>
          <Label className="text-[13px] text-muted-foreground mb-2 block">Avatar</Label>
          <div
            className="relative w-24 h-24 rounded-full overflow-hidden cursor-pointer group"
            onClick={() => avatarInputRef.current?.click()}
          >
            {avatarPreview || profile.avatar_url ? (
              <img
                src={avatarPreview || profile.avatar_url}
                alt=""
                className="w-full h-full object-cover"
              />
            ) : (
              <div className="w-full h-full bg-muted flex items-center justify-center text-2xl font-medium text-muted-foreground">
                {(profile.display_name || 'U')[0].toUpperCase()}
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
        </div>

        {/* Display Name */}
        <div>
          <Label htmlFor="displayName" className="text-[13px] text-muted-foreground">
            Display name
          </Label>
          <Input
            id="displayName"
            value={displayName}
            onChange={e => setDisplayName(e.target.value)}
            placeholder="Your display name"
            className="mt-1"
          />
        </div>

        {/* Username */}
        <div>
          <Label htmlFor="editUsername" className="text-[13px] text-muted-foreground">
            Username
          </Label>
          <div className="relative mt-1">
            <Input
              id="editUsername"
              value={editUsername}
              onChange={e => setEditUsername(e.target.value)}
              placeholder="your_username"
              className={
                usernameChanged && editUsername.length >= 3
                  ? usernameAvailable
                    ? 'pr-10 border-green-500'
                    : 'pr-10 border-red-500'
                  : ''
              }
            />
            {usernameChanged && editUsername.length >= 3 && (
              <span className="absolute right-3 top-1/2 -translate-y-1/2">
                {usernameAvailable ? (
                  <Check className="w-4 h-4 text-green-500" />
                ) : (
                  <X className="w-4 h-4 text-red-500" />
                )}
              </span>
            )}
          </div>
          {usernameChanged && editUsername.length >= 3 && !usernameAvailable && (
            <p className="text-[12px] text-red-500 mt-1">This username is not available.</p>
          )}
        </div>

        {/* Bio */}
        <div>
          <Label htmlFor="bio" className="text-[13px] text-muted-foreground">
            Bio
          </Label>
          <textarea
            id="bio"
            value={bio}
            onChange={e => setBio(e.target.value)}
            placeholder="Tell us about yourself"
            className="mt-1 flex min-h-[80px] w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring resize-none"
            maxLength={1000}
          />
        </div>

        {/* Website */}
        <div>
          <Label htmlFor="websiteUrl" className="text-[13px] text-muted-foreground">
            Website
          </Label>
          <Input
            id="websiteUrl"
            value={websiteUrl}
            onChange={e => setWebsiteUrl(e.target.value)}
            placeholder="https://example.com"
            className="mt-1"
          />
        </div>

        {/* Location */}
        <div>
          <Label htmlFor="location" className="text-[13px] text-muted-foreground">
            Location
          </Label>
          <Input
            id="location"
            value={location}
            onChange={e => setLocation(e.target.value)}
            placeholder="San Francisco, CA"
            className="mt-1"
          />
        </div>

        {/* GitHub */}
        <div>
          <Label htmlFor="githubUsername" className="text-[13px] text-muted-foreground">
            GitHub username
          </Label>
          <Input
            id="githubUsername"
            value={githubUsername}
            onChange={e => setGithubUsername(e.target.value)}
            placeholder="username"
            className="mt-1"
          />
        </div>

        {/* Twitter */}
        <div>
          <Label htmlFor="twitterUsername" className="text-[13px] text-muted-foreground">
            Twitter username
          </Label>
          <Input
            id="twitterUsername"
            value={twitterUsername}
            onChange={e => setTwitterUsername(e.target.value)}
            placeholder="username"
            className="mt-1"
          />
        </div>

        {/* LinkedIn */}
        <div>
          <Label htmlFor="linkedinUrl" className="text-[13px] text-muted-foreground">
            LinkedIn URL
          </Label>
          <Input
            id="linkedinUrl"
            value={linkedinUrl}
            onChange={e => setLinkedinUrl(e.target.value)}
            placeholder="https://linkedin.com/in/username"
            className="mt-1"
          />
        </div>

        {/* Public toggle */}
        <div className="flex items-center justify-between">
          <div>
            <Label className="text-[13px] text-foreground">Public profile</Label>
            <p className="text-[12px] text-muted-foreground">
              Make your profile visible to everyone
            </p>
          </div>
          <button
            type="button"
            role="switch"
            aria-checked={isPublic}
            onClick={() => setIsPublic(!isPublic)}
            className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors shrink-0 ${
              isPublic ? 'bg-primary' : 'bg-input'
            }`}
          >
            <span
              className={`inline-block h-3.5 w-3.5 rounded-full bg-white shadow-sm transform transition-transform ${
                isPublic ? 'translate-x-[18px]' : 'translate-x-[3px]'
              }`}
            />
          </button>
        </div>

        {/* Submit */}
        <div className="flex items-center gap-3 pt-2">
          <Button type="submit" disabled={isSubmitting}>
            {isSubmitting && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
            {isSubmitting ? 'Saving...' : 'Save'}
          </Button>
          <Button
            type="button"
            variant="ghost"
            onClick={() => router.push(`/profile/${editUsername}`)}
          >
            Cancel
          </Button>
        </div>
      </form>
    </div>
  );
}

'use client';

import { useEffect } from 'react';
import { useRouter, useParams } from 'next/navigation';

export default function SettingsIndexPage() {
  const router = useRouter();
  const params = useParams<{ workspace: string }>();
  const slug = params?.workspace ?? '';

  useEffect(() => {
    router.replace(`/${slug}/settings/preferences`);
  }, [slug, router]);

  return null;
}

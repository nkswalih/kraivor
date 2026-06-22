'use client';

import { useParams } from 'next/navigation';
import { DiscussionDetail } from '@/components/community/detail';

export default function DiscussionPage() {
  const params = useParams();
  const discussionId = params?.id as string;

  if (!discussionId) {
    return <div className="p-6 text-center text-muted-foreground">Discussion not found.</div>;
  }

  return <DiscussionDetail discussionId={discussionId} />;
}

'use client';

import { useParams } from 'next/navigation';
import { AiChatView } from '@/components/features/ai-chat-view';

export default function AIWorkspacePage() {
  const params = useParams<{ workspace: string }>();
  const workspaceSlug = params?.workspace ?? '';

  return <AiChatView key="welcome" workspaceSlug={workspaceSlug} />;
}

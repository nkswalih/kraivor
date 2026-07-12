'use client';

import { useParams } from 'next/navigation';
import { AiChatView } from '@/components/features/ai-chat-view';

export default function ConversationPage() {
  const params = useParams<{ workspace: string; conversationId: string }>();
  const workspaceSlug = params?.workspace ?? '';
  const conversationId = params?.conversationId ?? '';

  return <AiChatView key={conversationId} workspaceSlug={workspaceSlug} initialConversationId={conversationId} />;
}

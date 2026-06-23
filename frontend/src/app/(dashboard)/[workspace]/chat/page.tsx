'use client';

import { useParams } from 'next/navigation';
import { useAuthStore } from '@/lib/stores/auth-store';
import { ChannelSidebar } from '@/components/features/channel-sidebar';
import { MessageSquare } from 'lucide-react';

export default function ChatPage() {
  const params = useParams<{ workspace: string }>();
  const workspaceSlug = params?.workspace ?? '';
  const workspaceId = useAuthStore(s => s.workspaceId);

  if (!workspaceId) {
    return (
      <div className="flex h-full items-center justify-center bg-background">
        <div className="w-5 h-5 border-2 border-venom-yellow border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="flex flex-1 min-h-0 w-full bg-background">
      <ChannelSidebar workspaceId={workspaceId} workspaceSlug={workspaceSlug} />
      <div className="flex-1 flex flex-col items-center justify-center text-center p-8 bg-krait-void">
        <MessageSquare className="w-10 h-10 text-text-tertiary mb-3" />
        <h3 className="text-base font-medium text-text-primary mb-1">Choose a conversation</h3>
        <p className="text-[13px] text-text-tertiary max-w-xs">
          Select a channel or direct message from the sidebar to start chatting.
        </p>
      </div>
    </div>
  );
}

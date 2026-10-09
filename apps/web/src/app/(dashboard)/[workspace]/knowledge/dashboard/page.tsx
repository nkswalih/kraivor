'use client';

import { useParams } from 'next/navigation';
import { useAuthStore } from '@/lib/stores/auth-store';
import { KnowledgeDashboardPage } from '@/components/knowledge-dashboard/knowledge-dashboard-page';

export default function DashboardPage() {
  const params = useParams<{ workspace: string }>();
  const workspaceId = useAuthStore(s => s.workspaceId);

  if (!workspaceId) return null;

  return <KnowledgeDashboardPage workspaceId={workspaceId} workspaceSlug={params.workspace} />;
}

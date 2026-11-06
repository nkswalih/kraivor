'use client';

import { useParams } from 'next/navigation';
import { useAuthStore } from '@/lib/stores/auth-store';
import { AdminMonitoringPage } from '@/components/admin-monitoring/admin-monitoring-page';

export default function AdminMonitoring() {
  const params = useParams<{ workspace: string }>();
  const workspaceId = useAuthStore(s => s.workspaceId);

  if (!workspaceId) return null;

  return <AdminMonitoringPage workspaceId={workspaceId} />;
}

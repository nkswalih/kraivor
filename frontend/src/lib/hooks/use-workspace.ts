import { useWorkspaceStore } from '@/lib/stores';

export function useWorkspace() {
  const { workspaces, currentWorkspace, isLoading, error, fetchWorkspaces, setCurrentWorkspace, createWorkspace, updateWorkspace, deleteWorkspace } = useWorkspaceStore();

  return {
    workspaces,
    currentWorkspace,
    isLoading,
    error,
    fetchWorkspaces,
    setCurrentWorkspace,
    createWorkspace,
    updateWorkspace,
    deleteWorkspace,
  };
}
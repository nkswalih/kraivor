import { useShallow } from 'zustand/shallow';
import { useWorkspaceStore } from '@/lib/stores';

export function useWorkspace() {
  const fetchWorkspaces = useWorkspaceStore(s => s.fetchWorkspaces);
  const setCurrentWorkspace = useWorkspaceStore(s => s.setCurrentWorkspace);
  const createWorkspace = useWorkspaceStore(s => s.createWorkspace);
  const updateWorkspace = useWorkspaceStore(s => s.updateWorkspace);
  const deleteWorkspace = useWorkspaceStore(s => s.deleteWorkspace);
  const isLoading = useWorkspaceStore(s => s.isLoading);
  const error = useWorkspaceStore(s => s.error);
  const { workspaces, currentWorkspace } = useWorkspaceStore(
    useShallow(s => ({ workspaces: s.workspaces, currentWorkspace: s.currentWorkspace }))
  );

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

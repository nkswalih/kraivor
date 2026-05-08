import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { authApi, workspaceApi, analysisApi, notesApi, projectsApi } from '@/lib/api';

export function useCurrentUser() {
  return useQuery({
    queryKey: ['currentUser'],
    queryFn: authApi.getCurrentUser,
    retry: false,
    staleTime: Infinity,
  });
}

export function useWorkspaces() {
  return useQuery({
    queryKey: ['workspaces'],
    queryFn: workspaceApi.list,
    enabled: false,
  });
}

export function useLogin() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: authApi.login,
    onSuccess: (data) => {
      queryClient.setQueryData(['currentUser'], data.user);
    },
  });
}

export function useRegister() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: authApi.register,
    onSuccess: (data) => {
      queryClient.setQueryData(['currentUser'], data.user);
    },
  });
}

export function useLogout() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: authApi.logout,
    onSuccess: () => {
      queryClient.clear();
    },
  });
}

export function useRepositories() {
  return useQuery({
    queryKey: ['repositories'],
    queryFn: analysisApi.listRepositories,
  });
}

export function useNotes(params?: { projectId?: string }) {
  return useQuery({
    queryKey: ['notes', params],
    queryFn: () => notesApi.list(params),
  });
}

export function useProjects() {
  return useQuery({
    queryKey: ['projects'],
    queryFn: projectsApi.listProjects,
  });
}

export function useTasks(projectId?: string) {
  return useQuery({
    queryKey: ['tasks', projectId],
    queryFn: () => projectsApi.listTasks(projectId),
  });
}
import { create } from 'zustand';
import type { TaskStatus, ProjectStatus } from '@/types/domain/projects';

type ViewMode = 'grid' | 'list';
type ProjectTab = 'overview' | 'board' | 'list' | 'timeline' | 'insights';

interface ProjectsStore {
  viewMode: ViewMode;
  projectStatusFilter: ProjectStatus | undefined;
  taskStatusFilter: TaskStatus | undefined;
  taskPriorityFilter: string | undefined;
  selectedProjectId: string | undefined;
  drawerOpen: boolean;
  drawerTaskId: string | undefined;
  createTaskOpen: boolean;
  createTaskDefaultProjectId: string | undefined;
  createProjectOpen: boolean;
  editProjectOpen: boolean;
  editProjectId: string | undefined;
  activeTab: ProjectTab;

  setViewMode: (mode: ViewMode) => void;
  setProjectStatusFilter: (status: ProjectStatus | undefined) => void;
  setTaskStatusFilter: (status: TaskStatus | undefined) => void;
  setTaskPriorityFilter: (priority: string | undefined) => void;
  setSelectedProjectId: (id: string | undefined) => void;
  openTaskDrawer: (taskId: string) => void;
  closeTaskDrawer: () => void;
  openCreateTask: (projectId?: string) => void;
  closeCreateTask: () => void;
  openCreateProject: () => void;
  closeCreateProject: () => void;
  openEditProject: (projectId: string) => void;
  closeEditProject: () => void;
  setActiveTab: (tab: ProjectTab) => void;
}

export const useProjectsStore = create<ProjectsStore>(set => ({
  viewMode: 'grid',
  projectStatusFilter: undefined,
  taskStatusFilter: undefined,
  taskPriorityFilter: undefined,
  selectedProjectId: undefined,
  drawerOpen: false,
  drawerTaskId: undefined,
  createTaskOpen: false,
  createTaskDefaultProjectId: undefined,
  createProjectOpen: false,
  editProjectOpen: false,
  editProjectId: undefined,
  activeTab: 'overview',

  setViewMode: mode => set({ viewMode: mode }),
  setProjectStatusFilter: status => set({ projectStatusFilter: status }),
  setTaskStatusFilter: status => set({ taskStatusFilter: status }),
  setTaskPriorityFilter: priority => set({ taskPriorityFilter: priority }),
  setSelectedProjectId: id => set({ selectedProjectId: id }),
  openTaskDrawer: taskId => set({ drawerOpen: true, drawerTaskId: taskId }),
  closeTaskDrawer: () => set({ drawerOpen: false, drawerTaskId: undefined }),
  openCreateTask: projectId => set({ createTaskOpen: true, createTaskDefaultProjectId: projectId }),
  closeCreateTask: () => set({ createTaskOpen: false, createTaskDefaultProjectId: undefined }),
  openCreateProject: () => set({ createProjectOpen: true }),
  closeCreateProject: () => set({ createProjectOpen: false }),
  openEditProject: projectId => set({ editProjectOpen: true, editProjectId: projectId }),
  closeEditProject: () => set({ editProjectOpen: false, editProjectId: undefined }),
  setActiveTab: tab => set({ activeTab: tab }),
}));

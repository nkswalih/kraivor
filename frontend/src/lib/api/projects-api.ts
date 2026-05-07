import apiClient from './client';
import { API_ENDPOINTS } from '@/constants';
import type { Project, Task, ProjectCreatePayload, TaskCreatePayload } from '@/types/domain/projects';
import { handleApiError } from './error-handler';

export const projectsApi = {
  async listProjects() {
    try {
      const response = await apiClient.get<Project[]>(API_ENDPOINTS.PROJECTS.LIST);
      return response;
    } catch (error) {
      throw handleApiError(error);
    }
  },

  async getProject(id: string) {
    try {
      const response = await apiClient.get<Project>(API_ENDPOINTS.PROJECTS.GET(id));
      return response;
    } catch (error) {
      throw handleApiError(error);
    }
  },

  async createProject(payload: ProjectCreatePayload) {
    try {
      const response = await apiClient.post<Project>(API_ENDPOINTS.PROJECTS.CREATE, payload);
      return response;
    } catch (error) {
      throw handleApiError(error);
    }
  },

  async updateProject(id: string, payload: Partial<ProjectCreatePayload>) {
    try {
      const response = await apiClient.patch<Project>(API_ENDPOINTS.PROJECTS.UPDATE(id), payload);
      return response;
    } catch (error) {
      throw handleApiError(error);
    }
  },

  async deleteProject(id: string) {
    try {
      await apiClient.delete(API_ENDPOINTS.PROJECTS.DELETE(id));
    } catch (error) {
      throw handleApiError(error);
    }
  },

  async listTasks(projectId?: string) {
    try {
      const response = await apiClient.get<Task[]>(API_ENDPOINTS.TASKS.LIST, { params: { projectId } });
      return response;
    } catch (error) {
      throw handleApiError(error);
    }
  },

  async getTask(id: string) {
    try {
      const response = await apiClient.get<Task>(API_ENDPOINTS.TASKS.GET(id));
      return response;
    } catch (error) {
      throw handleApiError(error);
    }
  },

  async createTask(payload: TaskCreatePayload) {
    try {
      const response = await apiClient.post<Task>(API_ENDPOINTS.TASKS.CREATE, payload);
      return response;
    } catch (error) {
      throw handleApiError(error);
    }
  },

  async updateTask(id: string, payload: Partial<Task>) {
    try {
      const response = await apiClient.patch<Task>(API_ENDPOINTS.TASKS.UPDATE(id), payload);
      return response;
    } catch (error) {
      throw handleApiError(error);
    }
  },

  async deleteTask(id: string) {
    try {
      await apiClient.delete(API_ENDPOINTS.TASKS.DELETE(id));
    } catch (error) {
      throw handleApiError(error);
    }
  },
};
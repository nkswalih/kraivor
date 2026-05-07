import apiClient from './client';
import { API_ENDPOINTS } from '@/constants';
import type { Workspace, CreateWorkspacePayload, UpdateWorkspacePayload } from '@/types/workspace';
import { handleApiError } from './error-handler';

export const workspaceApi = {
  async list() {
    try {
      const response = await apiClient.get<Workspace[]>(API_ENDPOINTS.WORKSPACES.LIST);
      return response;
    } catch (error) {
      throw handleApiError(error);
    }
  },

  async get(id: string) {
    try {
      const response = await apiClient.get<Workspace>(API_ENDPOINTS.WORKSPACES.GET(id));
      return response;
    } catch (error) {
      throw handleApiError(error);
    }
  },

  async create(payload: CreateWorkspacePayload) {
    try {
      const response = await apiClient.post<Workspace>(API_ENDPOINTS.WORKSPACES.CREATE, payload);
      return response;
    } catch (error) {
      throw handleApiError(error);
    }
  },

  async update(id: string, payload: UpdateWorkspacePayload) {
    try {
      const response = await apiClient.patch<Workspace>(API_ENDPOINTS.WORKSPACES.UPDATE(id), payload);
      return response;
    } catch (error) {
      throw handleApiError(error);
    }
  },

  async delete(id: string) {
    try {
      await apiClient.delete(API_ENDPOINTS.WORKSPACES.DELETE(id));
    } catch (error) {
      throw handleApiError(error);
    }
  },

  async getMembers(id: string) {
    try {
      const response = await apiClient.get(API_ENDPOINTS.WORKSPACES.MEMBERS(id));
      return response;
    } catch (error) {
      throw handleApiError(error);
    }
  },
};
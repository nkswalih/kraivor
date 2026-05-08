import apiClient from './client';
import { API_ENDPOINTS } from '@/constants';
import type { Repository, AnalysisResult, RepositoryProvider } from '@/types/domain/analysis';
import { handleApiError } from './error-handler';

export const analysisApi = {
  async listRepositories() {
    try {
      const response = await apiClient.get<Repository[]>(API_ENDPOINTS.REPOSITORIES.LIST);
      return response;
    } catch (error) {
      throw handleApiError(error);
    }
  },

  async getRepository(id: string) {
    try {
      const response = await apiClient.get<Repository>(API_ENDPOINTS.REPOSITORIES.GET(id));
      return response;
    } catch (error) {
      throw handleApiError(error);
    }
  },

  async connectRepository(provider: RepositoryProvider, repoUrl: string) {
    try {
      const response = await apiClient.post<Repository>(API_ENDPOINTS.REPOSITORIES.CONNECT, { provider, repoUrl });
      return response;
    } catch (error) {
      throw handleApiError(error);
    }
  },

  async disconnectRepository(id: string) {
    try {
      await apiClient.delete(API_ENDPOINTS.REPOSITORIES.DISCONNECT(id));
    } catch (error) {
      throw handleApiError(error);
    }
  },

  async analyzeRepository(id: string) {
    try {
      const response = await apiClient.post<AnalysisResult>(API_ENDPOINTS.REPOSITORIES.ANALYZE(id));
      return response;
    } catch (error) {
      throw handleApiError(error);
    }
  },

  async getAnalysisResult(repositoryId: string) {
    try {
      const response = await apiClient.get<AnalysisResult>(`/analysis/repository/${repositoryId}`);
      return response;
    } catch (error) {
      throw handleApiError(error);
    }
  },
};
import apiClient from './client';
import { API_ENDPOINTS } from '@/constants';
import type { Note, NoteCreatePayload, NoteUpdatePayload, NoteSearchParams } from '@/types/domain/notes';
import { handleApiError } from './error-handler';

export const notesApi = {
  async list(params?: NoteSearchParams) {
    try {
      const response = await apiClient.get<Note[]>(API_ENDPOINTS.NOTES.LIST, { params });
      return response;
    } catch (error) {
      throw handleApiError(error);
    }
  },

  async get(id: string) {
    try {
      const response = await apiClient.get<Note>(API_ENDPOINTS.NOTES.GET(id));
      return response;
    } catch (error) {
      throw handleApiError(error);
    }
  },

  async create(payload: NoteCreatePayload) {
    try {
      const response = await apiClient.post<Note>(API_ENDPOINTS.NOTES.CREATE, payload);
      return response;
    } catch (error) {
      throw handleApiError(error);
    }
  },

  async update(id: string, payload: NoteUpdatePayload) {
    try {
      const response = await apiClient.patch<Note>(API_ENDPOINTS.NOTES.UPDATE(id), payload);
      return response;
    } catch (error) {
      throw handleApiError(error);
    }
  },

  async delete(id: string) {
    try {
      await apiClient.delete(API_ENDPOINTS.NOTES.DELETE(id));
    } catch (error) {
      throw handleApiError(error);
    }
  },
};
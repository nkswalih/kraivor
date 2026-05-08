import apiClient from './client';
import { API_ENDPOINTS } from '@/constants';
import type { ChatSession, SendMessagePayload, ChatMessage } from '@/types/domain/ai';
import { handleApiError } from './error-handler';

export const aiApi = {
  async listSessions() {
    try {
      const response = await apiClient.get<ChatSession[]>(API_ENDPOINTS.AI.SESSIONS);
      return response;
    } catch (error) {
      throw handleApiError(error);
    }
  },

  async getSession(id: string) {
    try {
      const response = await apiClient.get<ChatSession>(`${API_ENDPOINTS.AI.SESSIONS}/${id}`);
      return response;
    } catch (error) {
      throw handleApiError(error);
    }
  },

  async sendMessage(payload: SendMessagePayload): Promise<ChatMessage> {
    try {
      const response = await apiClient.post<ChatMessage>(API_ENDPOINTS.AI.CHAT, payload);
      return response;
    } catch (error) {
      throw handleApiError(error);
    }
  },

  async *streamMessage(payload: SendMessagePayload) {
    const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}${API_ENDPOINTS.AI.STREAM}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      throw new Error('Stream failed');
    }

    const reader = response.body?.getReader();
    if (!reader) return;

    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6);
          if (data === '[DONE]') return;
          try {
            const parsed = JSON.parse(data);
            yield parsed;
          } catch {
            yield data;
          }
        }
      }
    }
  },

  async deleteSession(id: string) {
    try {
      await apiClient.delete(`${API_ENDPOINTS.AI.SESSIONS}/${id}`);
    } catch (error) {
      throw handleApiError(error);
    }
  },
};
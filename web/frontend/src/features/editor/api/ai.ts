import { apiClient } from '../../../shared/config/apiClient';
import type { Design } from '../../design/types';
import type { Pattern } from '../../design/types';

export const aiAPI = {
  suggest: async (prompt: string, pageWidth: number, pageHeight: number): Promise<any> => {
    const response = await apiClient.post(
      '/ai/suggest',
      { prompt, page_width: pageWidth, page_height: pageHeight },
      { timeout: 300000 }
    );
    return response.data;
  },
  improve: async (design: Design): Promise<string[]> => {
    const response = await apiClient.post('/ai/improve', { design });
    return response.data.suggestions;
  },
  learnFromPDF: async (file: File): Promise<any> => {
    const formData = new FormData();
    formData.append('file', file);
    const response = await apiClient.post('/ai/learn', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },
  getPatterns: async (query?: string): Promise<Pattern[]> => {
    const response = await apiClient.get('/ai/patterns', { params: { query } });
    return response.data.patterns;
  },
  getStats: async (): Promise<any> => {
    const response = await apiClient.get('/ai/stats');
    return response.data;
  },
};

export default aiAPI;


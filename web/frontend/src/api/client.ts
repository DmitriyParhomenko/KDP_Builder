/**
 * API client for backend communication
 */

import axios from 'axios';
import type { Design, DesignCreate, Pattern } from '../types/design';

const API_BASE = '/api';

const api = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Designs API
export const designsAPI = {
  create: async (data: DesignCreate): Promise<Design> => {
    const response = await api.post('/designs/', data);
    return response.data.design;
  },

  list: async (): Promise<Design[]> => {
    const response = await api.get('/designs/');
    return response.data.designs;
  },

  get: async (id: string): Promise<Design> => {
    const response = await api.get(`/designs/${id}`);
    return response.data.design;
  },

  update: async (id: string, data: Partial<Design>): Promise<Design> => {
    const response = await api.put(`/designs/${id}`, data);
    return response.data.design;
  },

  delete: async (id: string): Promise<void> => {
    await api.delete(`/designs/${id}`);
  },
};

// AI API
export const aiAPI = {
  suggest: async (prompt: string, pageWidth: number, pageHeight: number): Promise<any> => {
    const response = await api.post('/ai/suggest', {
      prompt,
      page_width: pageWidth,
      page_height: pageHeight,
    });
    return response.data;
  },

  improve: async (design: Design): Promise<string[]> => {
    const response = await api.post('/ai/improve', { design });
    return response.data.suggestions;
  },

  learnFromPDF: async (file: File): Promise<any> => {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await api.post('/ai/learn', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  getPatterns: async (query?: string): Promise<Pattern[]> => {
    const response = await api.get('/ai/patterns', {
      params: { query },
    });
    return response.data.patterns;
  },

  getStats: async (): Promise<any> => {
    const response = await api.get('/ai/stats');
    return response.data;
  },
};

// Export API
export const exportAPI = {
  toPDF: async (design: Design, includeBleed: boolean = true): Promise<string> => {
    const response = await api.post('/export/pdf', {
      design,
      include_bleed: includeBleed,
      bleed_pt: 9.0,
    });
    return response.data.download_url;
  },
};

export default api;

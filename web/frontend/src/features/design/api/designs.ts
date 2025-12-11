import { apiClient } from '../../../shared/config/apiClient';
import type { Design, DesignCreate } from '../types';

export const designsAPI = {
  create: async (data: DesignCreate): Promise<Design> => {
    const response = await apiClient.post('/designs/', data);
    return response.data.design;
  },
  list: async (): Promise<Design[]> => {
    const response = await apiClient.get('/designs/');
    return response.data.designs;
  },
  get: async (id: string): Promise<Design> => {
    const response = await apiClient.get(`/designs/${id}`);
    return response.data.design;
  },
  update: async (id: string, data: Partial<Design>): Promise<Design> => {
    const response = await apiClient.put(`/designs/${id}`, data);
    return response.data.design;
  },
  delete: async (id: string): Promise<void> => {
    await apiClient.delete(`/designs/${id}`);
  },
};

export default designsAPI;


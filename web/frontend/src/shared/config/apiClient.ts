import axios from 'axios';

/**
 * Shared Axios client
 */
export const apiClient = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
  timeout: 120000,
});

export default apiClient;

import { apiClient } from '../../../shared/config/apiClient';
import type { Design } from '../../design/types';

export const exportAPI = {
  toPDF: async (design: Design, includeBleed: boolean = true): Promise<string> => {
    const response = await apiClient.post('/export/pdf', {
      design,
      include_bleed: includeBleed,
      bleed_pt: 9.0,
    });
    return response.data.download_url;
  },
};

export default exportAPI;


import { describe, test, expect, beforeEach, vi } from 'vitest';

// Mock axios module with factory
vi.mock('axios', () => {
  const mockInstance = {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  };
  
  return {
    default: {
      create: vi.fn(() => mockInstance),
    },
  };
});

// Import client after mock is set up
import { designsAPI, aiAPI, exportAPI } from './client';
import axios from 'axios';

// Get reference to the mock instance
const mockAxiosInstance = (axios.create as any)();

describe('Designs API', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('create', () => {
    test('creates new design with correct payload', async () => {
      const mockResponse = {
        data: {
          design: {
            id: 'design-1',
            name: 'Test Design',
            page_width: 432,
            page_height: 648,
            pages: [
              {
                page_number: 1,
                elements: [],
                background_color: '#ffffff',
              },
            ],
            created_at: '2024-01-01T00:00:00Z',
            updated_at: '2024-01-01T00:00:00Z',
            metadata: {},
          },
        },
      };

      mockAxiosInstance.post.mockResolvedValueOnce(mockResponse);

      const result = await designsAPI.create({
        name: 'Test Design',
        page_width: 432,
        page_height: 648,
        num_pages: 1,
      });

      expect(mockAxiosInstance.post).toHaveBeenCalledWith('/designs/', {
        name: 'Test Design',
        page_width: 432,
        page_height: 648,
        num_pages: 1,
      });

      expect(result).toEqual(mockResponse.data.design);
    });

    test('throws error on API failure', async () => {
      mockAxiosInstance.post.mockRejectedValueOnce(new Error('Network error'));

      await expect(
        designsAPI.create({
          name: 'Test Design',
          page_width: 432,
          page_height: 648,
          num_pages: 1,
        })
      ).rejects.toThrow('Network error');
    });
  });

  describe('list', () => {
    test('fetches list of designs', async () => {
      const mockResponse = {
        data: {
          designs: [
            {
              id: 'design-1',
              name: 'Design 1',
              page_width: 432,
              page_height: 648,
              created_at: '2024-01-01T00:00:00Z',
            },
            {
              id: 'design-2',
              name: 'Design 2',
              page_width: 432,
              page_height: 648,
              created_at: '2024-01-02T00:00:00Z',
            },
          ],
        },
      };

      mockAxiosInstance.get.mockResolvedValueOnce(mockResponse);

      const result = await designsAPI.list();

      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/designs/');
      expect(result).toEqual(mockResponse.data.designs);
    });
  });

  describe('get', () => {
    test('fetches single design by id', async () => {
      const mockResponse = {
        data: {
          design: {
            id: 'design-1',
            name: 'Test Design',
            page_width: 432,
            page_height: 648,
            pages: [],
            created_at: '2024-01-01T00:00:00Z',
            updated_at: '2024-01-01T00:00:00Z',
            metadata: {},
          },
        },
      };

      mockAxiosInstance.get.mockResolvedValueOnce(mockResponse);

      const result = await designsAPI.get('design-1');

      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/designs/design-1');
      expect(result).toEqual(mockResponse.data.design);
    });
  });

  describe('update', () => {
    test('updates design with partial data', async () => {
      const mockResponse = {
        data: {
          design: {
            id: 'design-1',
            name: 'Updated Design',
            page_width: 432,
            page_height: 648,
            pages: [],
            created_at: '2024-01-01T00:00:00Z',
            updated_at: '2024-01-02T00:00:00Z',
            metadata: {},
          },
        },
      };

      mockAxiosInstance.put.mockResolvedValueOnce(mockResponse);

      const result = await designsAPI.update('design-1', {
        name: 'Updated Design',
      });

      expect(mockAxiosInstance.put).toHaveBeenCalledWith('/designs/design-1', {
        name: 'Updated Design',
      });
      expect(result).toEqual(mockResponse.data.design);
    });
  });

  describe('delete', () => {
    test('deletes design by id', async () => {
      mockAxiosInstance.delete.mockResolvedValueOnce({ data: { success: true } });

      await designsAPI.delete('design-1');

      expect(mockAxiosInstance.delete).toHaveBeenCalledWith('/designs/design-1');
    });
  });
});

describe('AI API', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('suggest', () => {
    test('generates AI layout suggestions', async () => {
      const mockResponse = {
        data: {
          elements: [
            { type: 'text', x: 100, y: 100, width: 200, height: 30 },
          ],
        },
      };

      mockAxiosInstance.post.mockResolvedValueOnce(mockResponse);

      const result = await aiAPI.suggest('Create a daily planner', 432, 648);

      expect(mockAxiosInstance.post).toHaveBeenCalledWith(
        '/ai/suggest',
        {
          prompt: 'Create a daily planner',
          page_width: 432,
          page_height: 648,
        },
        {
          timeout: 300000,
        }
      );
      expect(result).toEqual(mockResponse.data);
    });
  });

  describe('learnFromPDF', () => {
    test('uploads PDF for pattern learning', async () => {
      const mockFile = new File(['test'], 'test.pdf', { type: 'application/pdf' });
      const mockResponse = {
        data: {
          pattern_id: 'pattern-1',
          blocks: [],
          message: 'Pattern learned successfully',
        },
      };

      mockAxiosInstance.post.mockResolvedValueOnce(mockResponse);

      const result = await aiAPI.learnFromPDF(mockFile);

      expect(mockAxiosInstance.post).toHaveBeenCalledWith(
        '/ai/learn',
        expect.any(FormData),
        {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        }
      );
      expect(result).toEqual(mockResponse.data);
    });
  });

  describe('getPatterns', () => {
    test('fetches patterns without query', async () => {
      const mockResponse = {
        data: {
          patterns: [
            {
              id: 'pattern-1',
              description: 'Daily planner layout',
              metadata: { type: 'planner' },
            },
          ],
        },
      };

      mockAxiosInstance.get.mockResolvedValueOnce(mockResponse);

      const result = await aiAPI.getPatterns();

      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/ai/patterns', {
        params: { query: undefined },
      });
      expect(result).toEqual(mockResponse.data.patterns);
    });

    test('fetches patterns with query', async () => {
      const mockResponse = {
        data: {
          patterns: [
            {
              id: 'pattern-1',
              description: 'Daily planner layout',
              metadata: { type: 'planner' },
            },
          ],
        },
      };

      mockAxiosInstance.get.mockResolvedValueOnce(mockResponse);

      const result = await aiAPI.getPatterns('daily');

      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/ai/patterns', {
        params: { query: 'daily' },
      });
      expect(result).toEqual(mockResponse.data.patterns);
    });
  });

  describe('getStats', () => {
    test('fetches AI statistics', async () => {
      const mockResponse = {
        data: {
          total_patterns: 10,
          total_blocks: 150,
        },
      };

      mockAxiosInstance.get.mockResolvedValueOnce(mockResponse);

      const result = await aiAPI.getStats();

      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/ai/stats');
      expect(result).toEqual(mockResponse.data);
    });
  });
});

describe('Export API', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('toPDF', () => {
    test('exports design to PDF with bleed', async () => {
      const mockDesign = {
        id: 'design-1',
        name: 'Test Design',
        page_width: 432,
        page_height: 648,
        pages: [],
        metadata: {},
      };

      const mockResponse = {
        data: {
          download_url: '/downloads/design-1.pdf',
        },
      };

      mockAxiosInstance.post.mockResolvedValueOnce(mockResponse);

      const result = await exportAPI.toPDF(mockDesign, true);

      expect(mockAxiosInstance.post).toHaveBeenCalledWith('/export/pdf', {
        design: mockDesign,
        include_bleed: true,
        bleed_pt: 9.0,
      });
      expect(result).toBe('/downloads/design-1.pdf');
    });

    test('exports design to PDF without bleed', async () => {
      const mockDesign = {
        id: 'design-1',
        name: 'Test Design',
        page_width: 432,
        page_height: 648,
        pages: [],
        metadata: {},
      };

      const mockResponse = {
        data: {
          download_url: '/downloads/design-1.pdf',
        },
      };

      mockAxiosInstance.post.mockResolvedValueOnce(mockResponse);

      const result = await exportAPI.toPDF(mockDesign, false);

      expect(mockAxiosInstance.post).toHaveBeenCalledWith('/export/pdf', {
        design: mockDesign,
        include_bleed: false,
        bleed_pt: 9.0,
      });
      expect(result).toBe('/downloads/design-1.pdf');
    });
  });
});

import { describe, test, expect, beforeEach } from 'vitest';
import { useDesignStore } from './designStore';
import type { Design, DesignElement } from '../types/design';

describe('Design Store', () => {
  // Helper to create a test design
  const createTestDesign = (): Design => ({
    id: 'test-design-1',
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
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    metadata: {},
  });

  // Helper to create a test element
  const createTestElement = (id: string, type: 'text' | 'rectangle' | 'circle' | 'line' = 'rectangle'): DesignElement => ({
    id,
    type,
    x: 100,
    y: 100,
    width: 50,
    height: 50,
    rotation: 0,
    z_index: 0,
    properties: {},
  });

  beforeEach(() => {
    // Reset store before each test
    useDesignStore.setState({
      design: null,
      currentPage: 0,
      selectedElements: [],
      activeTool: 'select',
      history: [],
      historyIndex: -1,
    });
  });

  describe('setDesign', () => {
    test('sets design and resets current page', () => {
      const design = createTestDesign();
      useDesignStore.getState().setDesign(design);

      const state = useDesignStore.getState();
      expect(state.design).toEqual(design);
      expect(state.currentPage).toBe(0);
    });

    test('saves design to history', () => {
      const design = createTestDesign();
      useDesignStore.getState().setDesign(design);

      const state = useDesignStore.getState();
      expect(state.history.length).toBeGreaterThan(0);
      expect(state.historyIndex).toBe(0);
    });
  });

  describe('addElement', () => {
    test('adds element to current page', () => {
      const design = createTestDesign();
      useDesignStore.getState().setDesign(design);

      const element = createTestElement('rect-1');
      useDesignStore.getState().addElement(element);

      const state = useDesignStore.getState();
      expect(state.design?.pages[0].elements).toHaveLength(1);
      expect(state.design?.pages[0].elements[0]).toEqual(element);
    });

    test('does nothing if no design exists', () => {
      const element = createTestElement('rect-1');
      useDesignStore.getState().addElement(element);

      const state = useDesignStore.getState();
      expect(state.design).toBeNull();
    });

    test('saves to history after adding element', () => {
      const design = createTestDesign();
      useDesignStore.getState().setDesign(design);
      const initialHistoryLength = useDesignStore.getState().history.length;

      const element = createTestElement('rect-1');
      useDesignStore.getState().addElement(element);

      const state = useDesignStore.getState();
      expect(state.history.length).toBe(initialHistoryLength + 1);
    });
  });

  describe('updateElement', () => {
    test('updates element properties', () => {
      const design = createTestDesign();
      useDesignStore.getState().setDesign(design);

      const element = createTestElement('rect-1');
      useDesignStore.getState().addElement(element);

      useDesignStore.getState().updateElement('rect-1', {
        x: 200,
        y: 300,
        width: 100,
      });

      const state = useDesignStore.getState();
      const updatedElement = state.design?.pages[0].elements[0];
      expect(updatedElement?.x).toBe(200);
      expect(updatedElement?.y).toBe(300);
      expect(updatedElement?.width).toBe(100);
      expect(updatedElement?.height).toBe(50); // Unchanged
    });

    test('merges properties without overwriting', () => {
      const design = createTestDesign();
      useDesignStore.getState().setDesign(design);

      const element = createTestElement('text-1', 'text');
      element.properties = { text: 'Hello', fontSize: 16, color: '#000' };
      useDesignStore.getState().addElement(element);

      useDesignStore.getState().updateElement('text-1', {
        properties: { fontSize: 24 },
      });

      const state = useDesignStore.getState();
      const updatedElement = state.design?.pages[0].elements[0];
      expect(updatedElement?.properties.text).toBe('Hello'); // Preserved
      expect(updatedElement?.properties.fontSize).toBe(24); // Updated
      expect(updatedElement?.properties.color).toBe('#000'); // Preserved
    });

    test('does nothing if element not found', () => {
      const design = createTestDesign();
      useDesignStore.getState().setDesign(design);

      const element = createTestElement('rect-1');
      useDesignStore.getState().addElement(element);

      useDesignStore.getState().updateElement('non-existent', { x: 999 });

      const state = useDesignStore.getState();
      expect(state.design?.pages[0].elements[0].x).toBe(100); // Unchanged
    });
  });

  describe('deleteElement', () => {
    test('deletes element by id', () => {
      const design = createTestDesign();
      useDesignStore.getState().setDesign(design);

      const element = createTestElement('rect-1');
      useDesignStore.getState().addElement(element);

      useDesignStore.getState().deleteElement('rect-1');

      const state = useDesignStore.getState();
      expect(state.design?.pages[0].elements).toHaveLength(0);
    });

    test('clears selection after delete', () => {
      const design = createTestDesign();
      useDesignStore.getState().setDesign(design);

      const element = createTestElement('rect-1');
      useDesignStore.getState().addElement(element);
      useDesignStore.getState().selectElement('rect-1');

      useDesignStore.getState().deleteElement('rect-1');

      const state = useDesignStore.getState();
      expect(state.selectedElements).toHaveLength(0);
    });
  });

  describe('reorderElement', () => {
    test('moves element to new z-index', () => {
      const design = createTestDesign();
      useDesignStore.getState().setDesign(design);

      // Add 3 elements
      useDesignStore.getState().addElement(createTestElement('rect-1'));
      useDesignStore.getState().addElement(createTestElement('rect-2'));
      useDesignStore.getState().addElement(createTestElement('rect-3'));

      // Set z-indexes
      useDesignStore.getState().updateElement('rect-1', { z_index: 0 });
      useDesignStore.getState().updateElement('rect-2', { z_index: 1 });
      useDesignStore.getState().updateElement('rect-3', { z_index: 2 });

      // Move rect-1 to top (z-index 2)
      useDesignStore.getState().reorderElement('rect-1', 2);

      const state = useDesignStore.getState();
      const elements = state.design?.pages[0].elements || [];
      
      const rect1 = elements.find(e => e.id === 'rect-1');
      const rect2 = elements.find(e => e.id === 'rect-2');
      const rect3 = elements.find(e => e.id === 'rect-3');

      expect(rect1?.z_index).toBe(2);
      expect(rect2?.z_index).toBe(0);
      expect(rect3?.z_index).toBe(1);
    });
  });

  describe('selectElement', () => {
    test('selects single element', () => {
      useDesignStore.getState().selectElement('rect-1');

      const state = useDesignStore.getState();
      expect(state.selectedElements).toEqual(['rect-1']);
    });

    test('replaces selection when multi=false', () => {
      useDesignStore.getState().selectElement('rect-1');
      useDesignStore.getState().selectElement('rect-2', false);

      const state = useDesignStore.getState();
      expect(state.selectedElements).toEqual(['rect-2']);
    });

    test('adds to selection when multi=true', () => {
      useDesignStore.getState().selectElement('rect-1');
      useDesignStore.getState().selectElement('rect-2', true);

      const state = useDesignStore.getState();
      expect(state.selectedElements).toEqual(['rect-1', 'rect-2']);
    });

    test('toggles selection when multi=true and already selected', () => {
      useDesignStore.getState().selectElement('rect-1');
      useDesignStore.getState().selectElement('rect-2', true);
      useDesignStore.getState().selectElement('rect-1', true); // Toggle off

      const state = useDesignStore.getState();
      expect(state.selectedElements).toEqual(['rect-2']);
    });
  });

  describe('clearSelection', () => {
    test('clears all selected elements', () => {
      useDesignStore.getState().selectElement('rect-1');
      useDesignStore.getState().selectElement('rect-2', true);

      useDesignStore.getState().clearSelection();

      const state = useDesignStore.getState();
      expect(state.selectedElements).toHaveLength(0);
    });
  });

  describe('setActiveTool', () => {
    test('changes active tool', () => {
      useDesignStore.getState().setActiveTool('text');

      const state = useDesignStore.getState();
      expect(state.activeTool).toBe('text');
    });
  });

  describe('undo/redo', () => {
    test('undo reverts to previous state', () => {
      const design = createTestDesign();
      useDesignStore.getState().setDesign(design);

      const element = createTestElement('rect-1');
      useDesignStore.getState().addElement(element);

      expect(useDesignStore.getState().design?.pages[0].elements).toHaveLength(1);

      useDesignStore.getState().undo();

      expect(useDesignStore.getState().design?.pages[0].elements).toHaveLength(0);
    });

    test('redo restores undone state', () => {
      const design = createTestDesign();
      useDesignStore.getState().setDesign(design);

      const element = createTestElement('rect-1');
      useDesignStore.getState().addElement(element);

      useDesignStore.getState().undo();
      expect(useDesignStore.getState().design?.pages[0].elements).toHaveLength(0);

      useDesignStore.getState().redo();
      expect(useDesignStore.getState().design?.pages[0].elements).toHaveLength(1);
    });

    test('undo does nothing at start of history', () => {
      const design = createTestDesign();
      useDesignStore.getState().setDesign(design);

      useDesignStore.getState().undo();
      useDesignStore.getState().undo(); // Try to go before start

      expect(useDesignStore.getState().design).toBeTruthy();
    });

    test('redo does nothing at end of history', () => {
      const design = createTestDesign();
      useDesignStore.getState().setDesign(design);

      const element = createTestElement('rect-1');
      useDesignStore.getState().addElement(element);

      useDesignStore.getState().redo(); // Already at end

      expect(useDesignStore.getState().design?.pages[0].elements).toHaveLength(1);
    });

    test('history is limited to 50 states', () => {
      const design = createTestDesign();
      useDesignStore.getState().setDesign(design);

      // Add 60 elements to exceed history limit
      for (let i = 0; i < 60; i++) {
        useDesignStore.getState().addElement(createTestElement(`rect-${i}`));
      }

      const state = useDesignStore.getState();
      expect(state.history.length).toBeLessThanOrEqual(50);
    });
  });

  describe('setCurrentPage', () => {
    test('changes current page', () => {
      useDesignStore.getState().setCurrentPage(1);

      const state = useDesignStore.getState();
      expect(state.currentPage).toBe(1);
    });
  });
});

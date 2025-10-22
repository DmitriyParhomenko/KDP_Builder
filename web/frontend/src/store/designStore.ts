/**
 * Zustand store for design state management
 */

import { create } from 'zustand';
import type { Design, DesignElement, Tool } from '../types/design';

interface DesignState {
  // Current design
  design: Design | null;
  currentPage: number;
  
  // Selected elements
  selectedElements: string[];
  
  // Active tool
  activeTool: Tool;
  
  // History for undo/redo
  history: Design[];
  historyIndex: number;
  
  // Actions
  setDesign: (design: Design) => void;
  setCurrentPage: (page: number) => void;
  addElement: (element: DesignElement) => void;
  updateElement: (id: string, updates: Partial<DesignElement>) => void;
  deleteElement: (id: string) => void;
  selectElement: (id: string, multi?: boolean) => void;
  clearSelection: () => void;
  setActiveTool: (tool: Tool) => void;
  undo: () => void;
  redo: () => void;
  saveToHistory: () => void;
}

export const useDesignStore = create<DesignState>((set, get) => ({
  design: null,
  currentPage: 0,
  selectedElements: [],
  activeTool: 'select',
  history: [],
  historyIndex: -1,

  setDesign: (design) => {
    set({ design, currentPage: 0 });
    get().saveToHistory();
  },

  setCurrentPage: (page) => set({ currentPage: page }),

  addElement: (element) => {
    const { design, currentPage } = get();
    if (!design) return;

    const newDesign = { ...design };
    newDesign.pages[currentPage].elements.push(element);
    
    set({ design: newDesign });
    get().saveToHistory();
  },

  updateElement: (id, updates) => {
    const { design, currentPage } = get();
    if (!design) return;

    const newDesign = { ...design };
    const elements = newDesign.pages[currentPage].elements;
    const index = elements.findIndex(e => e.id === id);
    
    if (index !== -1) {
      const currentElement = elements[index];
      // Merge properties separately to avoid overwriting
      const mergedProperties = updates.properties 
        ? { ...currentElement.properties, ...updates.properties }
        : currentElement.properties;
      
      elements[index] = { 
        ...currentElement, 
        ...updates,
        properties: mergedProperties
      };
      set({ design: newDesign });
      get().saveToHistory();
    }
  },

  deleteElement: (id) => {
    const { design, currentPage } = get();
    if (!design) return;

    const newDesign = { ...design };
    newDesign.pages[currentPage].elements = 
      newDesign.pages[currentPage].elements.filter(e => e.id !== id);
    
    set({ design: newDesign, selectedElements: [] });
    get().saveToHistory();
  },

  selectElement: (id, multi = false) => {
    const { selectedElements } = get();
    
    if (multi) {
      set({
        selectedElements: selectedElements.includes(id)
          ? selectedElements.filter(eid => eid !== id)
          : [...selectedElements, id]
      });
    } else {
      set({ selectedElements: [id] });
    }
  },

  clearSelection: () => set({ selectedElements: [] }),

  setActiveTool: (tool) => set({ activeTool: tool }),

  saveToHistory: () => {
    const { design, history, historyIndex } = get();
    if (!design) return;

    const newHistory = history.slice(0, historyIndex + 1);
    newHistory.push(JSON.parse(JSON.stringify(design)));
    
    // Keep only last 50 states
    if (newHistory.length > 50) {
      newHistory.shift();
    }

    set({
      history: newHistory,
      historyIndex: newHistory.length - 1
    });
  },

  undo: () => {
    const { history, historyIndex } = get();
    if (historyIndex > 0) {
      set({
        design: JSON.parse(JSON.stringify(history[historyIndex - 1])),
        historyIndex: historyIndex - 1
      });
    }
  },

  redo: () => {
    const { history, historyIndex } = get();
    if (historyIndex < history.length - 1) {
      set({
        design: JSON.parse(JSON.stringify(history[historyIndex + 1])),
        historyIndex: historyIndex + 1
      });
    }
  },
}));

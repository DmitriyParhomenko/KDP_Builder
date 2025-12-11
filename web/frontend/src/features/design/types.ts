/**
 * TypeScript types for KDP Visual Editor
 */

export type ElementType = 'text' | 'rectangle' | 'circle' | 'line' | 'image' | 'checkbox';

export interface DesignElement {
  id: string;
  type: ElementType;
  x: number;
  y: number;
  width: number;
  height: number;
  rotation: number;
  z_index: number;
  properties: Record<string, any>;
}

export interface DesignPage {
  page_number: number;
  elements: DesignElement[];
  background_color: string;
}

export interface Design {
  id?: string;
  name: string;
  page_width: number;
  page_height: number;
  pages: DesignPage[];
  created_at?: string;
  updated_at?: string;
  metadata: Record<string, any>;
}

export interface DesignCreate {
  name: string;
  page_width: number;
  page_height: number;
  num_pages: number;
}

export interface Pattern {
  id: string;
  description: string;
  metadata: Record<string, any>;
  distance?: number;
}

export type Tool = 'select' | 'text' | 'rectangle' | 'circle' | 'line' | 'pan';

import { useEffect, useRef } from 'react';
import { fabric } from 'fabric';
import type { Design, DesignElement } from '../../design/types';
import { applyZOrder, createFabricObject } from '../lib/fabricHelpers';

type UseElementsSyncArgs = {
  fabricRef: React.RefObject<any>;
  design: Design | null;
  currentPage: number;
  updateElement: (id: string, updates: Partial<DesignElement>) => void;
  selectElement: (id: string, multi?: boolean) => void;
  offsetX: number;
  offsetY: number;
};

export const useElementsSync = ({
  fabricRef,
  design,
  currentPage,
  updateElement,
  selectElement,
  offsetX,
  offsetY,
}: UseElementsSyncArgs) => {
  const isSyncingRef = useRef(false);
  const recentlyModifiedRef = useRef<Set<string>>(new Set());

  // load elements on design/page change
  useEffect(() => {
    const canvas = fabricRef.current;
    if (!canvas || !design) return;

    // Remove existing non-background objects
    const removable = canvas
      .getObjects()
      .filter((o: any) => !['background-page', 'background-grid', 'background-margins'].includes((o as any).data?.type));
    removable.forEach((o: any) => canvas.remove(o));

    // Ensure page background exists
    const hasPage = canvas.getObjects().some((o: any) => o.data?.type === 'background-page');
    if (!hasPage) {
      const pageRect = new fabric.Rect({
        left: 0,
        top: 0,
        width: design.page_width,
        height: design.page_height,
        fill: '#ffffff',
        selectable: false,
        evented: false,
        hasControls: false,
        hasBorders: false,
        hoverCursor: 'default',
        excludeFromExport: true,
        data: { type: 'background-page' },
      });
      canvas.add(pageRect);
      canvas.sendToBack(pageRect);
    }

    const page = design.pages[currentPage];
    if (!page) return;

    const sortedElements = [...page.elements].sort((a, b) => a.z_index - b.z_index);
    sortedElements.forEach((el) => {
      const obj = createFabricObject(el, offsetX, offsetY);
      if (obj) {
        obj.set({ data: { id: el.id }, angle: el.rotation || 0 });
        canvas.add(obj);
      }
    });

    applyZOrder(canvas, page.elements);
    canvas.renderAll();
  }, [fabricRef, design, currentPage, offsetX, offsetY]);

  // write back on modify
  useEffect(() => {
    const canvas = fabricRef.current;
    if (!canvas || !design) return;

    const pageOffsetLeft = 0;
    const pageOffsetTop = 0;

    const onModified = (e: any) => {
      if (!e.target || isSyncingRef.current || !design) return;
      const target = e.target as any;
      if (!target.data?.id) return;

      isSyncingRef.current = true;

      const calculatedWidth = (target.width || 0) * (target.scaleX || 1);
      const calculatedHeight = (target.height || 0) * (target.scaleY || 1);
      const relativeX = Math.round((target.left || 0) - pageOffsetLeft);
      const relativeY = Math.round((target.top || 0) - pageOffsetTop);

      const updates: any = {
        x: relativeX,
        y: relativeY,
        width: isNaN(calculatedWidth) ? 1 : Math.max(1, Math.round(calculatedWidth)),
        height: isNaN(calculatedHeight) ? 1 : Math.max(1, Math.round(calculatedHeight)),
        rotation: Math.round(target.angle || 0),
      };

      if (target.type === 'i-text' || target.type === 'text') {
        const textObj = target as any;
        const originalFontSize = textObj.fontSize || 16;
        const scaleX = textObj.scaleX || 1;
        const scaleY = textObj.scaleY || 1;
        const avgScale = (scaleX + scaleY) / 2;
        const newFontSize = Math.round(originalFontSize * avgScale);
        updates.properties = {
          text: textObj.text || '',
          fontSize: newFontSize,
          fontFamily: textObj.fontFamily || 'Arial',
          color: textObj.fill || '#000000',
        };
        textObj.set({ fontSize: newFontSize, scaleX: 1, scaleY: 1 });
        canvas.renderAll();
      }

      recentlyModifiedRef.current.add(target.data.id);
      updateElement(target.data.id, updates);

      setTimeout(() => {
        isSyncingRef.current = false;
        recentlyModifiedRef.current.delete(target.data!.id!);
      }, 300);
    };

    canvas.on('object:modified', onModified);

    canvas.on('text:editing:exited', (e: any) => {
      if (e.target && e.target.data?.id) {
        const textObj = e.target as any;
        updateElement(e.target.data.id, {
          properties: { text: textObj.text || '' },
        });
      }
    });

    return () => {
      canvas.off('object:modified', onModified);
    };
  }, [fabricRef, design, updateElement]);

  // sync store -> canvas updates for properties
  useEffect(() => {
    const canvas = fabricRef.current;
    if (!canvas || !design || isSyncingRef.current) return;

    const page = design.pages[currentPage];
    if (!page) return;

    page.elements.forEach((element) => {
      if (recentlyModifiedRef.current.has(element.id)) return;
      const canvasObj = canvas.getObjects().find((obj: any) => obj.data?.id === element.id);
      if (!canvasObj) return;
      canvasObj.set({
        left: element.x,
        top: element.y,
        angle: element.rotation || 0,
      });

      if (element.type === 'text' && (canvasObj.type === 'i-text' || canvasObj.type === 'text')) {
        const textObj = canvasObj as any;
        textObj.set({
          text: element.properties.text || '',
          fontSize: element.properties.fontSize || 12,
          fontFamily: element.properties.fontFamily || 'Helvetica',
          fill: element.properties.color || '#000000',
        });
      } else if (element.type === 'rectangle' && canvasObj.type === 'rect') {
        const rectObj = canvasObj as any;
        rectObj.set({
          width: element.width,
          height: element.height,
          fill: element.properties.fill || 'transparent',
          stroke: element.properties.stroke || '#000000',
          strokeWidth: element.properties.strokeWidth || 1,
        });
      } else if (element.type === 'circle' && canvasObj.type === 'circle') {
        const circleObj = canvasObj as any;
        circleObj.set({
          radius: Math.min(element.width, element.height) / 2,
          fill: element.properties.fill || 'transparent',
          stroke: element.properties.stroke || '#000000',
          strokeWidth: element.properties.strokeWidth || 1,
        });
      } else if (element.type === 'line' && canvasObj.type === 'line') {
        const lineObj = canvasObj as any;
        lineObj.set({
          stroke: element.properties.stroke || '#000000',
          strokeWidth: element.properties.strokeWidth || 1,
        });
      }

      canvasObj.setCoords();
    });

    applyZOrder(canvas, page.elements);
    canvas.renderAll();
  }, [fabricRef, design, currentPage]);

  // selection syncing
  useEffect(() => {
    const canvas = fabricRef.current;
    if (!canvas) return;

    const onSelectionCreated = (e: any) => {
      if (e.selected && e.selected.length > 1) {
        const selectedIds = e.selected
          .map((obj: any) => obj.data?.id)
          .filter(Boolean) as string[];
        if (selectedIds.length > 0) {
          selectElement(selectedIds[0], false);
          for (let i = 1; i < selectedIds.length; i++) selectElement(selectedIds[i], true);
        }
        if (e.target) {
          e.target.setControlsVisibility({ mt: false, mb: false, ml: false, mr: false });
        }
      } else if (e.selected && e.selected[0]) {
        const obj = e.selected[0];
        if (obj.data?.id) selectElement(obj.data.id);
      }
    };

    canvas.on('selection:created', onSelectionCreated);
    canvas.on('selection:updated', onSelectionCreated);

    return () => {
      canvas.off('selection:created', onSelectionCreated);
      canvas.off('selection:updated', onSelectionCreated);
    };
  }, [fabricRef, selectElement]);
};

export default useElementsSync;


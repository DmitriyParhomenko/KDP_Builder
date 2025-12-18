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

      // Handle group selection (multiple objects moved together)
      if (target.type === 'activeSelection') {
        const group = target;
        const objects = group.getObjects();
        
        isSyncingRef.current = true;

        // Ungroup to get absolute positions, then update each object
        const itemsData: Array<{id: string, obj: any, updates: any}> = [];
        
        objects.forEach((obj: any) => {
          if (!obj.data?.id) return;

          // Get the absolute center position using Fabric's coordinate system
          const matrix = group.calcTransformMatrix();
          const objCenter = obj.getCenterPoint();
          const transformedCenter = fabric.util.transformPoint(objCenter, matrix);

          // Calculate dimensions accounting for object's own scale and group scale
          const objWidth = (obj.width || 0) * (obj.scaleX || 1);
          const objHeight = (obj.height || 0) * (obj.scaleY || 1);
          const calculatedWidth = objWidth * (group.scaleX || 1);
          const calculatedHeight = objHeight * (group.scaleY || 1);
          
          // Calculate the final angle (object's angle + group's angle)
          const finalAngle = (obj.angle || 0) + (group.angle || 0);

          // Store center coordinates for reliable PDF export
          const updates: any = {
            x: Math.round(transformedCenter.x - pageOffsetLeft),
            y: Math.round(transformedCenter.y - pageOffsetTop),
            width: isNaN(calculatedWidth) ? 1 : Math.max(1, Math.round(calculatedWidth)),
            height: isNaN(calculatedHeight) ? 1 : Math.max(1, Math.round(calculatedHeight)),
            rotation: Math.round(finalAngle),
          };

          if (obj.type === 'i-text' || obj.type === 'text') {
            const textObj = obj as any;
            const originalFontSize = textObj.fontSize || 16;
            const scaleX = textObj.scaleX || 1;
            const scaleY = textObj.scaleY || 1;
            const groupScaleX = group.scaleX || 1;
            const groupScaleY = group.scaleY || 1;
            const avgScale = ((scaleX * groupScaleX) + (scaleY * groupScaleY)) / 2;
            const newFontSize = Math.round(originalFontSize * avgScale);
            updates.properties = {
              text: textObj.text || '',
              fontSize: newFontSize,
              fontFamily: textObj.fontFamily || 'Arial',
              color: textObj.fill || '#000000',
            };
          }

          itemsData.push({ id: obj.data.id, obj, updates });
        });

        // Update all elements in store
        itemsData.forEach(({ id, updates }) => {
          recentlyModifiedRef.current.add(id);
          updateElement(id, updates);
        });

        setTimeout(() => {
          isSyncingRef.current = false;
          itemsData.forEach(({ id }) => {
            recentlyModifiedRef.current.delete(id);
          });
        }, 300);

        return;
      }

      // Handle single object modification
      if (!target.data?.id) return;

      isSyncingRef.current = true;

      const calculatedWidth = (target.width || 0) * (target.scaleX || 1);
      const calculatedHeight = (target.height || 0) * (target.scaleY || 1);
      
      // For rotated elements, use the center point for reliable positioning
      // This ensures PDF export matches the canvas position
      const centerPoint = target.getCenterPoint ? target.getCenterPoint() : { x: target.left, y: target.top };
      const centerX = Math.round(centerPoint.x - pageOffsetLeft);
      const centerY = Math.round(centerPoint.y - pageOffsetTop);

      const updates: any = {
        x: centerX,
        y: centerY,
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
      // Element x,y are now center coordinates
      canvasObj.set({
        left: element.x,
        top: element.y,
        originX: 'center',
        originY: 'center',
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


import { useEffect } from 'react';
import { GRID_SIZE } from '../lib/constants';
import { createMarginsRect } from '../lib/fabricHelpers';
import { fabric } from 'fabric';

export const useGuides = (
  fabricRef: React.RefObject<any>,
  pageWidth: number,
  pageHeight: number,
  offsetX: number,
  offsetY: number
) => {
  useEffect(() => {
    const canvas = fabricRef.current;
    if (!canvas) return;

    // Grid
    for (let i = 0; i <= pageWidth; i += GRID_SIZE) {
      const line = new fabric.Line([offsetX + i, offsetY, offsetX + i, offsetY + pageHeight], {
        stroke: '#e0e0e0',
        strokeWidth: 0.5,
        selectable: false,
        evented: false,
        hasControls: false,
        hasBorders: false,
        hoverCursor: 'default',
        excludeFromExport: true,
      });
      line.set({ data: { type: 'background-grid' } });
      canvas.add(line);
    }

    for (let i = 0; i <= pageHeight; i += GRID_SIZE) {
      const line = new fabric.Line([offsetX, offsetY + i, offsetX + pageWidth, offsetY + i], {
        stroke: '#e0e0e0',
        strokeWidth: 0.5,
        selectable: false,
        evented: false,
        hasControls: false,
        hasBorders: false,
        hoverCursor: 'default',
        excludeFromExport: true,
      });
      line.set({ data: { type: 'background-grid' } });
      canvas.add(line);
    }

    // Margins
    const marginsRect = createMarginsRect(pageWidth, pageHeight, offsetX, offsetY);
    canvas.add(marginsRect);
  }, [fabricRef, pageWidth, pageHeight, offsetX, offsetY]);
};

export default useGuides;


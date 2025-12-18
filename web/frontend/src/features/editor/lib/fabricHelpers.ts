import type { DesignElement } from '../../design/types';
import { PAGE_MARGIN } from './constants';
import { fabric } from 'fabric';

export const setLineControls = (line: any) => {
  line.setControlsVisibility({
    mt: false,
    mb: false,
    ml: true,
    mr: true,
    tl: false,
    tr: false,
    bl: false,
    br: false,
    mtr: true,
  });
};

export const setTextControls = (text: any) => {
  text.setControlsVisibility({
    mt: false,
    mb: false,
    ml: false,
    mr: false,
  });
};

export const createFabricObject = (
  element: DesignElement,
  offsetX: number,
  offsetY: number
): any | null => {
  // element.x and element.y now store the CENTER point for reliable positioning
  const centerX = offsetX + element.x;
  const centerY = offsetY + element.y;
  
  switch (element.type) {
    case 'text': {
      const align = ['left', 'center', 'right', 'justify', 'start', 'end'].includes(
        (element.properties.align || '').toLowerCase()
      )
        ? element.properties.align || 'left'
        : 'left';
      const obj = new fabric.IText(element.properties.text || 'Text', {
        left: centerX,
        top: centerY,
        originX: 'center',
        originY: 'center',
        fontSize: element.properties.fontSize || 12,
        fontFamily: element.properties.fontFamily || 'Helvetica',
        fill: element.properties.color || '#000000',
        lockScalingFlip: true,
        textAlign: align as any,
        selectable: true,
        evented: true,
      });
      setTextControls(obj);
      return obj;
    }
    case 'rectangle':
      return new fabric.Rect({
        left: centerX,
        top: centerY,
        originX: 'center',
        originY: 'center',
        width: element.width,
        height: element.height,
        fill: element.properties.fill || 'transparent',
        stroke: element.properties.stroke || '#000000',
        strokeWidth: element.properties.strokeWidth || 1,
        selectable: true,
        evented: true,
      });
    case 'circle':
      return new fabric.Circle({
        left: centerX,
        top: centerY,
        originX: 'center',
        originY: 'center',
        radius: Math.min(element.width, element.height) / 2,
        fill: element.properties.fill || 'transparent',
        stroke: element.properties.stroke || '#000000',
        strokeWidth: element.properties.strokeWidth || 1,
        selectable: true,
        evented: true,
      });
    case 'line': {
      // For lines, use the center point and let rotation handle the angle
      const halfWidth = element.width / 2;
      const line = new fabric.Line(
        [centerX - halfWidth, centerY, centerX + halfWidth, centerY],
        {
          stroke: element.properties.stroke || '#000000',
          strokeWidth: element.properties.strokeWidth || 1,
          lockScalingY: true,
          lockRotation: false,
          selectable: true,
          evented: true,
          originX: 'center',
          originY: 'center',
        }
      );
      setLineControls(line);
      return line;
    }
    default:
      return null;
  }
};

export const createMarginsRect = (width: number, height: number, offsetX: number, offsetY: number) =>
  new fabric.Rect({
    left: offsetX + PAGE_MARGIN,
    top: offsetY + PAGE_MARGIN,
    width: width - 2 * PAGE_MARGIN,
    height: height - 2 * PAGE_MARGIN,
    fill: 'transparent',
    stroke: '#ff6b6b',
    strokeWidth: 1,
    strokeDashArray: [5, 5],
    selectable: false,
    evented: false,
    hasControls: false,
    hasBorders: false,
    hoverCursor: 'default',
    excludeFromExport: true,
    data: { type: 'background-margins' },
  });

export const applyZOrder = (canvas: any, elements: DesignElement[]) => {
  const allObjects = canvas.getObjects();
  const gridObjects = allObjects.filter((obj: any) => obj.data?.type === 'background-grid');
  const pageObjects = allObjects.filter((obj: any) => obj.data?.type === 'background-page');
  const marginObjects = allObjects.filter((obj: any) => obj.data?.type === 'background-margins');

  let bgPosition = 0;
  pageObjects.forEach((obj: any) => canvas.moveTo(obj, bgPosition++));
  gridObjects.forEach((obj: any) => canvas.moveTo(obj, bgPosition++));
  marginObjects.forEach((obj: any) => canvas.moveTo(obj, bgPosition++));

  const backgroundCount = gridObjects.length + pageObjects.length + marginObjects.length;
  const sorted = [...elements].sort((a, b) => a.z_index - b.z_index);
  sorted.forEach((el, idx) => {
    const obj = canvas.getObjects().find((o: any) => o.data?.id === el.id);
    if (obj) canvas.moveTo(obj, backgroundCount + idx);
  });
};


import { fabric } from 'fabric';
import { useEffect, useRef } from 'react';
import type { Design } from '../../design/types';
import { setLineControls, setTextControls } from '../lib/fabricHelpers';

type UseToolsArgs = {
  fabricRef: React.RefObject<any>;
  design: Design | null;
  activeTool: string;
  addElement: (el: any) => void;
};

export const useTools = ({ fabricRef, design, activeTool, addElement }: UseToolsArgs) => {
  const lastDrawnToolRef = useRef<string | null>(null);

  useEffect(() => {
    const canvas = fabricRef.current;
    if (!canvas || !design) return;

    switch (activeTool) {
      case 'select':
        canvas.isDrawingMode = false;
        canvas.selection = true;
        canvas.defaultCursor = 'default';
        canvas.forEachObject((obj: any) => {
          const type = obj.data?.type;
          const isBackground = type === 'background-page' || type === 'background-grid' || type === 'background-margins';
          if (isBackground) {
            obj.selectable = false;
            obj.evented = false;
          } else {
            obj.selectable = true;
            obj.evented = true;
          }
        });
        lastDrawnToolRef.current = 'select';
        break;
      case 'pan':
        canvas.isDrawingMode = false;
        canvas.selection = false;
        canvas.defaultCursor = 'grab';
        canvas.forEachObject((obj: any) => {
          const type = obj.data?.type;
          const isBackground = type === 'background-page' || type === 'background-grid' || type === 'background-margins';
          // keep backgrounds non-selectable; temporarily disable events on foreground while panning
          obj.selectable = !isBackground ? false : false;
          obj.evented = !isBackground ? false : false;
        });
        lastDrawnToolRef.current = 'pan';
        break;
      case 'text':
      case 'rectangle':
      case 'circle':
      case 'line':
        // Avoid re-running when state updates but tool stays the same
        if (lastDrawnToolRef.current === activeTool) break;
        if (activeTool === 'text') addText(canvas, design, addElement);
        else if (activeTool === 'rectangle') addRect(canvas, design, addElement);
        else if (activeTool === 'circle') addCircle(canvas, design, addElement);
        else if (activeTool === 'line') addLine(canvas, design, addElement);
        lastDrawnToolRef.current = activeTool;
        break;
      default:
        break;
    }
  }, [activeTool, fabricRef, design, addElement]);
};

const getViewportCenter = (canvas: any) => {
  const vpt = canvas.viewportTransform;
  const zoom = canvas.getZoom();
  const centerX = (canvas.width! / 2 - (vpt ? vpt[4] : 0)) / zoom;
  const centerY = (canvas.height! / 2 - (vpt ? vpt[5] : 0)) / zoom;
  return { centerX, centerY, zoom };
};

const addText = (canvas: any, design: Design | null, addElement: (el: any) => void) => {
  if (!design) return;
  const { centerX, centerY } = getViewportCenter(canvas);
  const text = new fabric.IText('Double-click to edit', {
    left: centerX,
    top: centerY,
    originX: 'center',
    originY: 'center',
    fontSize: 24,
    fontFamily: 'Helvetica',
    fill: '#000000',
    lockScalingFlip: true,
  });
  setTextControls(text);
  const id = `text_${Date.now()}`;
  text.set({ data: { id } });
  canvas.add(text);
  canvas.setActiveObject(text);
  canvas.renderAll();

  // Store center coordinates
  const textCenter = text.getCenterPoint();
  addElement({
    id,
    type: 'text',
    x: Math.round(textCenter.x),
    y: Math.round(textCenter.y),
    width: text.width || 100,
    height: text.height || 30,
    rotation: 0,
    z_index: canvas.getObjects().length,
    properties: {
      text: 'Double-click to edit',
      fontSize: 24,
      fontFamily: 'Helvetica',
      color: '#000000',
    },
  });
};

const addRect = (canvas: any, design: Design | null, addElement: (el: any) => void) => {
  if (!design) return;
  const { centerX, centerY } = getViewportCenter(canvas);
  const rect = new fabric.Rect({
    left: centerX,
    top: centerY,
    originX: 'center',
    originY: 'center',
    width: 100,
    height: 100,
    fill: 'transparent',
    stroke: '#000000',
    strokeWidth: 2,
  });
  const id = `rect_${Date.now()}`;
  rect.set({ data: { id } });
  canvas.add(rect);
  canvas.setActiveObject(rect);
  canvas.renderAll();

  // Store center coordinates
  const rectCenter = rect.getCenterPoint();
  addElement({
    id,
    type: 'rectangle',
    x: Math.round(rectCenter.x),
    y: Math.round(rectCenter.y),
    width: 100,
    height: 100,
    rotation: 0,
    z_index: canvas.getObjects().length,
    properties: { fill: 'transparent', stroke: '#000000', strokeWidth: 2 },
  });
};

const addCircle = (canvas: any, design: Design | null, addElement: (el: any) => void) => {
  if (!design) return;
  const { centerX, centerY } = getViewportCenter(canvas);
  const circle = new fabric.Circle({
    left: centerX,
    top: centerY,
    originX: 'center',
    originY: 'center',
    radius: 50,
    fill: 'transparent',
    stroke: '#000000',
    strokeWidth: 2,
  });
  const id = `circle_${Date.now()}`;
  circle.set({ data: { id } });
  canvas.add(circle);
  canvas.setActiveObject(circle);
  canvas.renderAll();

  // Store center coordinates
  const circleCenter = circle.getCenterPoint();
  addElement({
    id,
    type: 'circle',
    x: Math.round(circleCenter.x),
    y: Math.round(circleCenter.y),
    width: 100,
    height: 100,
    rotation: 0,
    z_index: canvas.getObjects().length,
    properties: { fill: 'transparent', stroke: '#000000', strokeWidth: 2 },
  });
};

const addLine = (canvas: any, design: Design | null, addElement: (el: any) => void) => {
  if (!design) return;
  const { centerX, centerY } = getViewportCenter(canvas);
  const line = new fabric.Line([centerX - 50, centerY, centerX + 50, centerY], {
    stroke: '#000000',
    strokeWidth: 2,
    lockScalingY: true,
    lockRotation: false,
    originX: 'center',
    originY: 'center',
  });
  setLineControls(line);
  const id = `line_${Date.now()}`;
  line.set({ data: { id } });
  canvas.add(line);
  canvas.setActiveObject(line);
  canvas.renderAll();

  // Store center coordinates (the center of the line)
  const lineCenter = line.getCenterPoint();
  addElement({
    id,
    type: 'line',
    x: Math.round(lineCenter.x),
    y: Math.round(lineCenter.y),
    width: 100,
    height: 0,
    rotation: 0,
    z_index: canvas.getObjects().length,
    properties: { stroke: '#000000', strokeWidth: 2 },
  });
};

export default useTools;


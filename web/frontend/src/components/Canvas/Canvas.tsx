/**
 * Canvas Component - Main editing canvas using Fabric.js
 */

import { useEffect, useRef } from 'react';
import { fabric } from 'fabric';
import { useDesignStore } from '../../store/designStore';

const Canvas = () => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const fabricRef = useRef<fabric.Canvas | null>(null);
  
  const { design, currentPage, activeTool, addElement, updateElement, selectElement } = useDesignStore();

  useEffect(() => {
    if (!canvasRef.current || !design) return;

    // Initialize Fabric canvas
    const canvas = new fabric.Canvas(canvasRef.current, {
      width: design.page_width,
      height: design.page_height,
      backgroundColor: '#ffffff',
    });

    fabricRef.current = canvas;

    // Add grid
    addGrid(canvas, design.page_width, design.page_height);

    // Add margins guide
    addMarginsGuide(canvas, design.page_width, design.page_height);

    // Load existing elements
    loadElements(canvas);

    // Handle object selection
    canvas.on('selection:created', (e) => {
      if (e.selected && e.selected[0]) {
        const obj = e.selected[0];
        if (obj.data?.id) {
          selectElement(obj.data.id);
        }
      }
    });

    canvas.on('selection:updated', (e) => {
      if (e.selected && e.selected[0]) {
        const obj = e.selected[0];
        if (obj.data?.id) {
          selectElement(obj.data.id);
        }
      }
    });

    // Handle object modification
    canvas.on('object:modified', (e) => {
      if (e.target && e.target.data?.id) {
        updateElement(e.target.data.id, {
          x: e.target.left || 0,
          y: e.target.top || 0,
          width: (e.target.width || 0) * (e.target.scaleX || 1),
          height: (e.target.height || 0) * (e.target.scaleY || 1),
          rotation: e.target.angle || 0,
        });
      }
    });

    // Cleanup
    return () => {
      canvas.dispose();
    };
  }, [design, currentPage]);

  // Handle tool changes
  useEffect(() => {
    if (!fabricRef.current) return;

    const canvas = fabricRef.current;

    switch (activeTool) {
      case 'select':
        canvas.isDrawingMode = false;
        canvas.selection = true;
        break;
      case 'text':
        canvas.isDrawingMode = false;
        canvas.selection = false;
        addTextElement(canvas);
        break;
      case 'rectangle':
        canvas.isDrawingMode = false;
        canvas.selection = false;
        addRectangleElement(canvas);
        break;
      case 'circle':
        canvas.isDrawingMode = false;
        canvas.selection = false;
        addCircleElement(canvas);
        break;
      case 'line':
        canvas.isDrawingMode = false;
        canvas.selection = false;
        addLineElement(canvas);
        break;
      default:
        canvas.isDrawingMode = false;
        canvas.selection = true;
    }
  }, [activeTool]);

  const addGrid = (canvas: fabric.Canvas, width: number, height: number) => {
    const gridSize = 36; // 0.5 inch
    const options = {
      stroke: '#e0e0e0',
      strokeWidth: 0.5,
      selectable: false,
      evented: false,
    };

    // Vertical lines
    for (let i = 0; i <= width; i += gridSize) {
      canvas.add(new fabric.Line([i, 0, i, height], options));
    }

    // Horizontal lines
    for (let i = 0; i <= height; i += gridSize) {
      canvas.add(new fabric.Line([0, i, width, i], options));
    }
  };

  const addMarginsGuide = (canvas: fabric.Canvas, width: number, height: number) => {
    const margin = 36; // 0.5 inch margin
    
    const rect = new fabric.Rect({
      left: margin,
      top: margin,
      width: width - (2 * margin),
      height: height - (2 * margin),
      fill: 'transparent',
      stroke: '#ff6b6b',
      strokeWidth: 1,
      strokeDashArray: [5, 5],
      selectable: false,
      evented: false,
    });

    canvas.add(rect);
  };

  const loadElements = (canvas: fabric.Canvas) => {
    if (!design) return;

    const page = design.pages[currentPage];
    if (!page) return;

    page.elements.forEach((element) => {
      let obj: fabric.Object | null = null;

      switch (element.type) {
        case 'text':
          obj = new fabric.IText(element.properties.text || 'Text', {
            left: element.x,
            top: element.y,
            fontSize: element.properties.fontSize || 12,
            fontFamily: element.properties.fontFamily || 'Helvetica',
            fill: element.properties.color || '#000000',
          });
          break;

        case 'rectangle':
          obj = new fabric.Rect({
            left: element.x,
            top: element.y,
            width: element.width,
            height: element.height,
            fill: element.properties.fill || 'transparent',
            stroke: element.properties.stroke || '#000000',
            strokeWidth: element.properties.strokeWidth || 1,
          });
          break;

        case 'circle':
          obj = new fabric.Circle({
            left: element.x,
            top: element.y,
            radius: Math.min(element.width, element.height) / 2,
            fill: element.properties.fill || 'transparent',
            stroke: element.properties.stroke || '#000000',
            strokeWidth: element.properties.strokeWidth || 1,
          });
          break;

        case 'line':
          obj = new fabric.Line([element.x, element.y, element.x + element.width, element.y + element.height], {
            stroke: element.properties.stroke || '#000000',
            strokeWidth: element.properties.strokeWidth || 1,
          });
          break;
      }

      if (obj) {
        obj.set({ data: { id: element.id } });
        canvas.add(obj);
      }
    });

    canvas.renderAll();
  };

  const addTextElement = (canvas: fabric.Canvas) => {
    const text = new fabric.IText('Double-click to edit', {
      left: 100,
      top: 100,
      fontSize: 24,
      fontFamily: 'Helvetica',
      fill: '#000000',
    });

    const id = `text_${Date.now()}`;
    text.set({ data: { id } });
    canvas.add(text);
    canvas.setActiveObject(text);

    addElement({
      id,
      type: 'text',
      x: 100,
      y: 100,
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

  const addRectangleElement = (canvas: fabric.Canvas) => {
    const rect = new fabric.Rect({
      left: 100,
      top: 100,
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

    addElement({
      id,
      type: 'rectangle',
      x: 100,
      y: 100,
      width: 100,
      height: 100,
      rotation: 0,
      z_index: canvas.getObjects().length,
      properties: {
        fill: 'transparent',
        stroke: '#000000',
        strokeWidth: 2,
      },
    });
  };

  const addCircleElement = (canvas: fabric.Canvas) => {
    const circle = new fabric.Circle({
      left: 100,
      top: 100,
      radius: 50,
      fill: 'transparent',
      stroke: '#000000',
      strokeWidth: 2,
    });

    const id = `circle_${Date.now()}`;
    circle.set({ data: { id } });
    canvas.add(circle);
    canvas.setActiveObject(circle);

    addElement({
      id,
      type: 'circle',
      x: 100,
      y: 100,
      width: 100,
      height: 100,
      rotation: 0,
      z_index: canvas.getObjects().length,
      properties: {
        fill: 'transparent',
        stroke: '#000000',
        strokeWidth: 2,
      },
    });
  };

  const addLineElement = (canvas: fabric.Canvas) => {
    const line = new fabric.Line([100, 100, 200, 100], {
      stroke: '#000000',
      strokeWidth: 2,
    });

    const id = `line_${Date.now()}`;
    line.set({ data: { id } });
    canvas.add(line);
    canvas.setActiveObject(line);

    addElement({
      id,
      type: 'line',
      x: 100,
      y: 100,
      width: 100,
      height: 0,
      rotation: 0,
      z_index: canvas.getObjects().length,
      properties: {
        stroke: '#000000',
        strokeWidth: 2,
      },
    });
  };

  return (
    <div className="flex items-center justify-center p-8">
      <div className="shadow-2xl">
        <canvas ref={canvasRef} />
      </div>
    </div>
  );
};

export default Canvas;

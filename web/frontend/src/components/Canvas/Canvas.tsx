/**
 * Canvas Component - Main editing canvas using Fabric.js
 */

import { useEffect, useRef, useState } from 'react';
import { fabric } from 'fabric';
import { useDesignStore } from '../../store/designStore';

const Canvas = () => {
  const containerRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const fabricRef = useRef<fabric.Canvas | null>(null);
  const isSyncingRef = useRef(false); // Prevent infinite loops
  const recentlyModifiedRef = useRef<Set<string>>(new Set()); // Track recently modified objects
  
  // Zoom and pan state
  const [zoom, setZoom] = useState(1);
  const [isPanning, setIsPanning] = useState(false);
  const panStartRef = useRef<{ x: number; y: number } | null>(null);
  
  const { design, currentPage, activeTool, addElement, updateElement, selectElement } = useDesignStore();

  useEffect(() => {
    if (!canvasRef.current || !design || !containerRef.current) return;

    // Create a large canvas workspace (much bigger than the page)
    // This creates an infinite canvas feel like Figma
    const workspaceWidth = Math.max(design.page_width * 3, 3000);
    const workspaceHeight = Math.max(design.page_height * 3, 3000);

    // Initialize Fabric canvas with large workspace
    const canvas = new fabric.Canvas(canvasRef.current, {
      width: workspaceWidth,
      height: workspaceHeight,
      backgroundColor: 'transparent', // Transparent so we see the dotted background
    });

    // Add white page rectangle as a background object (non-selectable)
    const pageRect = new fabric.Rect({
      left: (workspaceWidth - design.page_width) / 2,
      top: (workspaceHeight - design.page_height) / 2,
      width: design.page_width,
      height: design.page_height,
      fill: '#ffffff',
      selectable: false,
      evented: false,
      excludeFromExport: true,
    });
    canvas.add(pageRect);
    canvas.sendToBack(pageRect);

    // Page position in workspace
    const pageLeft = (workspaceWidth - design.page_width) / 2;
    const pageTop = (workspaceHeight - design.page_height) / 2;
    
    // Prevent moving/scaling outside margins (red border)
    const margin = 36;
    const pageW = design.page_width;
    const pageH = design.page_height;

    // Clamp helper for single object (relative to page position in workspace)
    const clampObjectWithinMargins = (o: any) => {
      const w = (o.width || 0) * (o.scaleX || 1);
      const h = (o.height || 0) * (o.scaleY || 1);
      const minLeft = pageLeft + margin;
      const minTop = pageTop + margin;
      const maxLeft = pageLeft + pageW - margin - w;
      const maxTop = pageTop + pageH - margin - h;
      if (typeof o.left === 'number') o.left = Math.min(Math.max(o.left, minLeft), Math.max(minLeft, maxLeft));
      if (typeof o.top === 'number') o.top = Math.min(Math.max(o.top, minTop), Math.max(minTop, maxTop));
    };

    // Clamp helper for active selection (use its bounding box)
    const clampGroupWithinMargins = (g: fabric.ActiveSelection) => {
      const gW = (g.getScaledWidth && g.getScaledWidth()) || ((g.width || 0) * (g.scaleX || 1));
      const gH = (g.getScaledHeight && g.getScaledHeight()) || ((g.height || 0) * (g.scaleY || 1));
      const minLeft = pageLeft + margin;
      const minTop = pageTop + margin;
      const maxLeft = pageLeft + pageW - margin - gW;
      const maxTop = pageTop + pageH - margin - gH;
      if (typeof g.left === 'number') g.left = Math.min(Math.max(g.left, minLeft), Math.max(minLeft, maxLeft));
      if (typeof g.top === 'number') g.top = Math.min(Math.max(g.top, minTop), Math.max(minTop, maxTop));
    };

    canvas.on('object:moving', (e: any) => {
      if (!e.target) return;
      if (e.target.type === 'activeSelection') {
        clampGroupWithinMargins(e.target as fabric.ActiveSelection);
      } else {
        clampObjectWithinMargins(e.target);
      }
    });

    canvas.on('object:scaling', (e: any) => {
      if (!e.target) return;
      if (e.target.type === 'activeSelection') {
        clampGroupWithinMargins(e.target as fabric.ActiveSelection);
        return;
      }
      const o: any = e.target;
      // Ensure scale does not push outside margins
      const baseW = o.width || 0;
      const baseH = o.height || 0;
      const left = o.left || 0;
      const top = o.top || 0;
      const maxScaleX = (pageW - margin - left) / Math.max(1, baseW);
      const maxScaleY = (pageH - margin - top) / Math.max(1, baseH);
      if (o.scaleX) o.scaleX = Math.min(o.scaleX, Math.max(0.1, maxScaleX));
      if (o.scaleY) o.scaleY = Math.min(o.scaleY, Math.max(0.1, maxScaleY));
      // After scaling, clamp position too
      clampObjectWithinMargins(o);
    });

    fabricRef.current = canvas;

    // Mouse wheel zoom
    canvas.on('mouse:wheel', (opt: any) => {
      const delta = opt.e.deltaY;
      let newZoom = canvas.getZoom();
      newZoom *= 0.999 ** delta;
      if (newZoom > 5) newZoom = 5;
      if (newZoom < 0.1) newZoom = 0.1;
      canvas.zoomToPoint({ x: opt.e.offsetX, y: opt.e.offsetY }, newZoom);
      setZoom(newZoom);
      opt.e.preventDefault();
      opt.e.stopPropagation();
    });

    // Pan with spacebar + drag
    let isPanningLocal = false;
    let lastPosX = 0;
    let lastPosY = 0;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.code === 'Space' && !isPanningLocal) {
        isPanningLocal = true;
        setIsPanning(true);
        canvas.selection = false;
        canvas.defaultCursor = 'grab';
        canvas.hoverCursor = 'grab';
      }
    };

    const handleKeyUp = (e: KeyboardEvent) => {
      if (e.code === 'Space') {
        isPanningLocal = false;
        setIsPanning(false);
        canvas.selection = true;
        canvas.defaultCursor = 'default';
        canvas.hoverCursor = 'move';
      }
    };

    canvas.on('mouse:down', (opt: any) => {
      if (isPanningLocal) {
        canvas.isDragging = true;
        canvas.selection = false;
        lastPosX = opt.e.clientX;
        lastPosY = opt.e.clientY;
        canvas.defaultCursor = 'grabbing';
      }
    });

    canvas.on('mouse:move', (opt: any) => {
      if (canvas.isDragging && isPanningLocal) {
        const vpt = canvas.viewportTransform;
        if (vpt) {
          vpt[4] += opt.e.clientX - lastPosX;
          vpt[5] += opt.e.clientY - lastPosY;
          canvas.requestRenderAll();
          lastPosX = opt.e.clientX;
          lastPosY = opt.e.clientY;
        }
      }
    });

    canvas.on('mouse:up', () => {
      canvas.setViewportTransform(canvas.viewportTransform);
      canvas.isDragging = false;
      if (isPanningLocal) {
        canvas.defaultCursor = 'grab';
      }
    });

    window.addEventListener('keydown', handleKeyDown);
    window.addEventListener('keyup', handleKeyUp);

    // Add grid (positioned on the white page)
    addGrid(canvas, design.page_width, design.page_height, pageLeft, pageTop);

    // Add margins guide (positioned on the white page)
    addMarginsGuide(canvas, design.page_width, design.page_height, pageLeft, pageTop);

    // Load existing elements (positioned on the white page)
    loadElements(canvas, pageLeft, pageTop);

    // Note: Removed automatic overlap resolution to allow free object placement
    // Objects can now overlap without jumping when released

    // Handle object selection
    canvas.on('selection:created', (e: any) => {
      console.log('🔍 Selection created:', e.target?.type, 'selected count:', e.selected?.length);
      
      // Handle group selection (multiple objects selected)
      if (e.selected && e.selected.length > 1) {
        console.log('🔵 Group selection detected');
        
        // Collect all IDs first
        const selectedIds: string[] = [];
        e.selected.forEach((obj: any) => {
          if (obj.data?.id) {
            selectedIds.push(obj.data.id);
          }
        });
        
        console.log('  Selected IDs:', selectedIds);
        
        // Select first element (clears previous)
        if (selectedIds.length > 0) {
          console.log('  Selecting first:', selectedIds[0]);
          selectElement(selectedIds[0], false);
          // Add remaining elements
          for (let i = 1; i < selectedIds.length; i++) {
            console.log('  Adding to selection:', selectedIds[i]);
            selectElement(selectedIds[i], true);
          }
        }
        
        // Hide side handles for group selections
        if (e.target) {
          e.target.setControlsVisibility({
            mt: false, // top middle
            mb: false, // bottom middle
            ml: false, // left middle
            mr: false, // right middle
          });
        }
      } 
      // Handle single selection
      else if (e.selected && e.selected[0]) {
        const obj = e.selected[0];
        if (obj.data?.id) {
          selectElement(obj.data.id);
        }
      }
    });

    canvas.on('selection:updated', (e: any) => {
      // Handle group selection (multiple objects selected)
      if (e.selected && e.selected.length > 1) {
        // Collect all IDs first
        const selectedIds: string[] = [];
        e.selected.forEach((obj: any) => {
          if (obj.data?.id) {
            selectedIds.push(obj.data.id);
          }
        });
        
        // Select first element (clears previous)
        if (selectedIds.length > 0) {
          selectElement(selectedIds[0], false);
          // Add remaining elements
          for (let i = 1; i < selectedIds.length; i++) {
            selectElement(selectedIds[i], true);
          }
        }
        
        // Hide side handles for group selections
        if (e.target) {
          e.target.setControlsVisibility({
            mt: false,
            mb: false,
            ml: false,
            mr: false,
          });
        }
      }
      // Handle single selection
      else if (e.selected && e.selected[0]) {
        const obj = e.selected[0];
        if (obj.data?.id) {
          selectElement(obj.data.id);
        }
      }
    });

    // Handle object modification (move, resize, rotate, text editing complete)
    canvas.on('object:modified', (e: any) => {
      if (!e.target || isSyncingRef.current) return;
      
      // Handle group selection (multiple objects moved/resized together)
      if (e.target.type === 'activeSelection') {
        isSyncingRef.current = true;
        const group = e.target as fabric.ActiveSelection;
        const objects = group.getObjects();
        
        // Get group transform
        const groupScaleX = group.scaleX || 1;
        const groupScaleY = group.scaleY || 1;
        
        objects.forEach((obj: any) => {
          if (obj.data?.id) {
            // Track as modified
            recentlyModifiedRef.current.add(obj.data.id);
            
            // Get object's absolute position after group transform
            // Use aCoords for accurate position after scaling/moving
            const matrix = group.calcTransformMatrix();
            const objectPoint = fabric.util.transformPoint(
              { x: obj.left, y: obj.top },
              matrix
            );
            
            const objLeft = objectPoint.x;
            const objTop = objectPoint.y;
            
            // Calculate new size with combined scales
            const objWidth = (obj.width || 0) * (obj.scaleX || 1) * groupScaleX;
            const objHeight = (obj.height || 0) * (obj.scaleY || 1) * groupScaleY;
            
            const updates: any = {
              x: Math.round(objLeft),
              y: Math.round(objTop),
              width: Math.max(1, Math.round(objWidth)),
              height: Math.max(1, Math.round(objHeight)),
            };
            
            // For text objects, scale the font size
            if (obj.type === 'i-text' || obj.type === 'text') {
              const textObj = obj as fabric.IText;
              const originalFontSize = textObj.fontSize || 16;
              const avgGroupScale = (groupScaleX + groupScaleY) / 2;
              const newFontSize = Math.round(originalFontSize * avgGroupScale);
              
              updates.properties = {
                text: textObj.text || '',
                fontSize: newFontSize,
                fontFamily: textObj.fontFamily || 'Arial',
                color: textObj.fill || '#000000',
              };
              
              // Reset text scale after applying to font size
              textObj.set({
                fontSize: newFontSize,
                scaleX: 1,
                scaleY: 1,
              });
            }
            
            updateElement(obj.data.id, updates);
          }
        });
        
        // Re-render canvas to show updated text sizes
        canvas.renderAll();
        
        // Reset flag and clear tracking after delay
        setTimeout(() => {
          isSyncingRef.current = false;
          objects.forEach((obj: any) => {
            if (obj.data?.id) {
              recentlyModifiedRef.current.delete(obj.data.id);
            }
          });
        }, 500);
        return;
      }
      
      // Handle single object modification
      if (e.target && e.target.data?.id) {
        isSyncingRef.current = true; // Set flag to prevent sync loop
        
        // Calculate width and height, ensuring valid numbers
        const calculatedWidth = (e.target.width || 0) * (e.target.scaleX || 1);
        const calculatedHeight = (e.target.height || 0) * (e.target.scaleY || 1);
        
        const updates: any = {
          x: Math.round(e.target.left || 0),
          y: Math.round(e.target.top || 0),
          width: isNaN(calculatedWidth) ? 1 : Math.max(1, Math.round(calculatedWidth)),
          height: isNaN(calculatedHeight) ? 1 : Math.max(1, Math.round(calculatedHeight)),
          rotation: Math.round(e.target.angle || 0),
        };

        // For text objects, update text content and font size
        if (e.target.type === 'i-text' || e.target.type === 'text') {
          const textObj = e.target as fabric.IText;
          
          // Calculate new font size based on scale
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
          
          // Reset scale after applying to font size
          textObj.set({
            fontSize: newFontSize,
            scaleX: 1,
            scaleY: 1,
          });
          canvas.renderAll();
        }

        // Track this object as recently modified
        recentlyModifiedRef.current.add(e.target.data.id);
        
        updateElement(e.target.data.id, updates);
        
        // Reset flag and clear modified tracking after delay
        setTimeout(() => {
          isSyncingRef.current = false;
          recentlyModifiedRef.current.delete(e.target.data.id);
        }, 500);
      }
    });

    // Handle when text editing ends (not during typing)
    canvas.on('text:editing:exited', (e: any) => {
      if (e.target && e.target.data?.id) {
        const textObj = e.target as fabric.IText;
        updateElement(e.target.data.id, {
          properties: {
            text: textObj.text || '',
          },
        });
      }
    });

    // Cleanup
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      window.removeEventListener('keyup', handleKeyUp);
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
        canvas.defaultCursor = 'default';
        // Disable panning
        canvas.forEachObject((obj) => {
          obj.selectable = true;
          obj.evented = true;
        });
        break;
      case 'pan':
        canvas.isDrawingMode = false;
        canvas.selection = false;
        canvas.defaultCursor = 'grab';
        // Make all objects non-selectable for panning
        canvas.forEachObject((obj) => {
          obj.selectable = false;
          obj.evented = false;
        });
        // Enable panning with mouse drag
        let isPanning = false;
        let lastPosX = 0;
        let lastPosY = 0;
        
        canvas.on('mouse:down', function(opt: any) {
          if (activeTool === 'pan') {
            isPanning = true;
            canvas.defaultCursor = 'grabbing';
            const evt = opt.e as MouseEvent;
            lastPosX = evt.clientX;
            lastPosY = evt.clientY;
          }
        });
        
        canvas.on('mouse:move', function(opt: any) {
          if (isPanning && activeTool === 'pan') {
            const evt = opt.e as MouseEvent;
            const vpt = canvas.viewportTransform;
            if (vpt) {
              vpt[4] += evt.clientX - lastPosX;
              vpt[5] += evt.clientY - lastPosY;
              canvas.requestRenderAll();
              lastPosX = evt.clientX;
              lastPosY = evt.clientY;
            }
          }
        });
        
        canvas.on('mouse:up', function() {
          if (activeTool === 'pan') {
            isPanning = false;
            canvas.defaultCursor = 'grab';
          }
        });
        break;
      case 'text':
        canvas.isDrawingMode = false;
        canvas.selection = false;
        canvas.defaultCursor = 'default';
        addTextElement(canvas);
        break;
      case 'rectangle':
        canvas.isDrawingMode = false;
        canvas.selection = false;
        canvas.defaultCursor = 'default';
        addRectangleElement(canvas);
        break;
      case 'circle':
        canvas.isDrawingMode = false;
        canvas.selection = false;
        canvas.defaultCursor = 'default';
        addCircleElement(canvas);
        break;
      case 'line':
        canvas.isDrawingMode = false;
        canvas.selection = false;
        canvas.defaultCursor = 'default';
        addLineElement(canvas);
        break;
      default:
        canvas.isDrawingMode = false;
        canvas.selection = true;
        canvas.defaultCursor = 'default';
    }
  }, [activeTool]);

  // Sync store changes back to canvas (when properties panel updates)
  useEffect(() => {
    if (!fabricRef.current || !design || isSyncingRef.current) return;

    const canvas = fabricRef.current;
    const currentPageElements = design.pages[currentPage]?.elements || [];

    // Update each canvas object from store
    currentPageElements.forEach(element => {
      // Skip recently modified objects to prevent overwriting user changes
      if (recentlyModifiedRef.current.has(element.id)) {
        return;
      }
      
      const canvasObj = canvas.getObjects().find((obj: any) => obj.data?.id === element.id);
      
      if (canvasObj) {
        // Update position, size, rotation
        canvasObj.set({
          left: element.x,
          top: element.y,
          angle: element.rotation || 0,
        });

        // Update type-specific properties
        if (element.type === 'text' && (canvasObj.type === 'i-text' || canvasObj.type === 'text')) {
          const textObj = canvasObj as fabric.IText;
          textObj.set({
            text: element.properties.text || '',
            fontSize: element.properties.fontSize || 12,
            fontFamily: element.properties.fontFamily || 'Helvetica',
            fill: element.properties.color || '#000000',
          });
        } else if (element.type === 'rectangle' && canvasObj.type === 'rect') {
          const rectObj = canvasObj as fabric.Rect;
          rectObj.set({
            width: element.width,
            height: element.height,
            fill: element.properties.fill || 'transparent',
            stroke: element.properties.stroke || '#000000',
            strokeWidth: element.properties.strokeWidth || 1,
          });
        } else if (element.type === 'circle' && canvasObj.type === 'circle') {
          const circleObj = canvasObj as fabric.Circle;
          circleObj.set({
            radius: Math.min(element.width, element.height) / 2,
            fill: element.properties.fill || 'transparent',
            stroke: element.properties.stroke || '#000000',
            strokeWidth: element.properties.strokeWidth || 1,
          });
        } else if (element.type === 'line' && canvasObj.type === 'line') {
          const lineObj = canvasObj as fabric.Line;
          lineObj.set({
            stroke: element.properties.stroke || '#000000',
            strokeWidth: element.properties.strokeWidth || 1,
          });
        }

        canvasObj.setCoords();
      }
    });

    // Update stacking order based on z_index
    const sortedElements = [...currentPageElements].sort((a, b) => a.z_index - b.z_index);
    sortedElements.forEach((element, index) => {
      const canvasObj = canvas.getObjects().find((obj: any) => obj.data?.id === element.id);
      if (canvasObj) {
        canvas.moveTo(canvasObj, index);
      }
    });

    canvas.renderAll();
  }, [design, currentPage]);

  const addGrid = (canvas: fabric.Canvas, width: number, height: number, offsetX: number, offsetY: number) => {
    const gridSize = 36; // 0.5 inch
    const options = {
      stroke: '#e0e0e0',
      strokeWidth: 0.5,
      selectable: false,
      evented: false,
    };

    // Vertical lines
    for (let i = 0; i <= width; i += gridSize) {
      canvas.add(new fabric.Line([offsetX + i, offsetY, offsetX + i, offsetY + height], options));
    }

    // Horizontal lines
    for (let i = 0; i <= height; i += gridSize) {
      canvas.add(new fabric.Line([offsetX, offsetY + i, offsetX + width, offsetY + i], options));
    }
  };

  const addMarginsGuide = (canvas: fabric.Canvas, width: number, height: number, offsetX: number, offsetY: number) => {
    const margin = 36; // 0.5 inch margin
    
    const rect = new fabric.Rect({
      left: offsetX + margin,
      top: offsetY + margin,
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

  const loadElements = (canvas: fabric.Canvas, offsetX: number, offsetY: number) => {
    if (!design) return;

    const page = design.pages[currentPage];
    if (!page) return;

    // Sort elements by z_index (lowest first) to ensure proper stacking
    const sortedElements = [...page.elements].sort((a, b) => a.z_index - b.z_index);

    sortedElements.forEach((element) => {
      let obj: fabric.Object | null = null;

      switch (element.type) {
        case 'text':
          {
            const align = ['left','center','right','justify','start','end'].includes(
              (element.properties.align || '').toLowerCase()
            ) ? (element.properties.align || 'left') : 'left';
            obj = new fabric.IText(element.properties.text || 'Text', {
              left: offsetX + element.x,
              top: offsetY + element.y,
              fontSize: element.properties.fontSize || 12,
              fontFamily: element.properties.fontFamily || 'Helvetica',
              fill: element.properties.color || '#000000',
              lockScalingFlip: true,
              textAlign: align as any,
            });
          }
          // Disable side handles, only allow corner resizing
          if (obj) {
            (obj as fabric.IText).setControlsVisibility({
              mt: false,
              mb: false,
              ml: false,
              mr: false,
            });
          }
          break;

        case 'rectangle':
          obj = new fabric.Rect({
            left: offsetX + element.x,
            top: offsetY + element.y,
            width: element.width,
            height: element.height,
            fill: element.properties.fill || 'transparent',
            stroke: element.properties.stroke || '#000000',
            strokeWidth: element.properties.strokeWidth || 1,
          });
          break;

        case 'circle':
          obj = new fabric.Circle({
            left: offsetX + element.x,
            top: offsetY + element.y,
            radius: Math.min(element.width, element.height) / 2,
            fill: element.properties.fill || 'transparent',
            stroke: element.properties.stroke || '#000000',
            strokeWidth: element.properties.strokeWidth || 1,
          });
          break;

        case 'line':
          obj = new fabric.Line([offsetX + element.x, offsetY + element.y, offsetX + element.x + element.width, offsetY + element.y + element.height], {
            stroke: element.properties.stroke || '#000000',
            strokeWidth: element.properties.strokeWidth || 1,
            lockScalingY: true,
            lockRotation: false,
          });
          // Only show left and right handles
          if (obj) {
            (obj as fabric.Line).setControlsVisibility({
              mt: false, mb: false,
              ml: true, mr: true,
              tl: false, tr: false,
              bl: false, br: false,
              mtr: true,
            });
          }
          break;
      }

      if (obj) {
        obj.set({ 
          data: { id: element.id },
          angle: element.rotation || 0
        });
        canvas.add(obj);
      }
    });

    canvas.renderAll();
  };

  const addTextElement = (canvas: fabric.Canvas) => {
    if (!design) return;
    // Calculate page offset in workspace
    const workspaceWidth = Math.max(design.page_width * 3, 3000);
    const workspaceHeight = Math.max(design.page_height * 3, 3000);
    const pageLeft = (workspaceWidth - design.page_width) / 2;
    const pageTop = (workspaceHeight - design.page_height) / 2;
    
    const text = new fabric.IText('Double-click to edit', {
      left: pageLeft + 100,
      top: pageTop + 100,
      fontSize: 24,
      fontFamily: 'Helvetica',
      fill: '#000000',
      lockScalingFlip: true,
    });

    // Disable side handles, only allow corner resizing
    text.setControlsVisibility({
      mt: false,
      mb: false,
      ml: false,
      mr: false,
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
    if (!design) return;
    // Calculate page offset in workspace
    const workspaceWidth = Math.max(design.page_width * 3, 3000);
    const workspaceHeight = Math.max(design.page_height * 3, 3000);
    const pageLeft = (workspaceWidth - design.page_width) / 2;
    const pageTop = (workspaceHeight - design.page_height) / 2;
    
    const rect = new fabric.Rect({
      left: pageLeft + 100,
      top: pageTop + 100,
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
    if (!design) return;
    // Calculate page offset in workspace
    const workspaceWidth = Math.max(design.page_width * 3, 3000);
    const workspaceHeight = Math.max(design.page_height * 3, 3000);
    const pageLeft = (workspaceWidth - design.page_width) / 2;
    const pageTop = (workspaceHeight - design.page_height) / 2;
    
    const circle = new fabric.Circle({
      left: pageLeft + 100,
      top: pageTop + 100,
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
    if (!design) return;
    // Calculate page offset in workspace
    const workspaceWidth = Math.max(design.page_width * 3, 3000);
    const workspaceHeight = Math.max(design.page_height * 3, 3000);
    const pageLeft = (workspaceWidth - design.page_width) / 2;
    const pageTop = (workspaceHeight - design.page_height) / 2;
    
    const line = new fabric.Line([pageLeft + 100, pageTop + 100, pageLeft + 200, pageTop + 100], {
      stroke: '#000000',
      strokeWidth: 2,
      lockScalingY: true, // Prevent vertical scaling
      lockRotation: false,
    });

    // Only show left and right handles for horizontal resizing
    line.setControlsVisibility({
      mt: false, // middle top
      mb: false, // middle bottom
      ml: true,  // middle left - KEEP
      mr: true,  // middle right - KEEP
      tl: false, // top left corner
      tr: false, // top right corner
      bl: false, // bottom left corner
      br: false, // bottom right corner
      mtr: true, // rotation handle - KEEP
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

  // Zoom handlers
  const handleZoomIn = () => {
    if (!fabricRef.current) return;
    const canvas = fabricRef.current;
    let newZoom = canvas.getZoom() * 1.1;
    if (newZoom > 5) newZoom = 5;
    canvas.setZoom(newZoom);
    setZoom(newZoom);
    canvas.requestRenderAll();
  };

  const handleZoomOut = () => {
    if (!fabricRef.current) return;
    const canvas = fabricRef.current;
    let newZoom = canvas.getZoom() / 1.1;
    if (newZoom < 0.1) newZoom = 0.1;
    canvas.setZoom(newZoom);
    setZoom(newZoom);
    canvas.requestRenderAll();
  };

  const handleFitToScreen = () => {
    if (!fabricRef.current || !containerRef.current || !design) return;
    const canvas = fabricRef.current;
    const container = containerRef.current;
    
    const containerWidth = container.clientWidth;
    const containerHeight = container.clientHeight;
    const canvasWidth = design.page_width;
    const canvasHeight = design.page_height;
    
    const scaleX = (containerWidth * 0.9) / canvasWidth;
    const scaleY = (containerHeight * 0.9) / canvasHeight;
    const newZoom = Math.min(scaleX, scaleY);
    
    canvas.setZoom(newZoom);
    setZoom(newZoom);
    canvas.setViewportTransform([newZoom, 0, 0, newZoom, 0, 0]);
    canvas.requestRenderAll();
  };

  return (
    <div 
      ref={containerRef}
      className="w-full h-full flex items-center justify-center bg-gray-900 relative overflow-auto"
      style={{
        backgroundImage: 'radial-gradient(circle, #374151 1px, transparent 1px)',
        backgroundSize: '20px 20px',
      }}
    >
      {/* Canvas - the white page is rendered inside */}
      <canvas ref={canvasRef} />
      
      {/* Zoom controls (Figma-style) */}
      <div className="absolute bottom-4 right-4 flex items-center gap-2 bg-gray-800 rounded-lg px-3 py-2 shadow-lg">
        <button 
          onClick={handleZoomOut}
          className="text-white hover:text-blue-400 text-sm font-medium px-2"
          title="Zoom out"
        >
          −
        </button>
        <span className="text-white text-xs font-mono min-w-[45px] text-center">
          {Math.round(zoom * 100)}%
        </span>
        <button 
          onClick={handleZoomIn}
          className="text-white hover:text-blue-400 text-sm font-medium px-2"
          title="Zoom in"
        >
          +
        </button>
        <div className="w-px h-4 bg-gray-600 mx-1"></div>
        <button 
          onClick={handleFitToScreen}
          className="text-white hover:text-blue-400 text-xs px-2"
          title="Fit to screen"
        >
          Fit
        </button>
      </div>
      
      {/* Pan hint */}
      {isPanning && (
        <div className="absolute top-4 left-1/2 transform -translate-x-1/2 bg-blue-600 text-white px-4 py-2 rounded-lg shadow-lg text-sm">
          Hold spacebar and drag to pan
        </div>
      )}
    </div>
  );
};

export default Canvas;

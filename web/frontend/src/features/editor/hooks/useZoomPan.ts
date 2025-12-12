import { useEffect, useState } from 'react';
import { ZOOM_MAX, ZOOM_MIN, ZOOM_STEP } from '../lib/constants';

type UseZoomPanArgs = {
  fabricRef: React.RefObject<any>;
  containerRef: React.RefObject<HTMLDivElement>;
  pageWidth: number;
  pageHeight: number;
};

export const useZoomPan = ({ fabricRef, containerRef, pageWidth, pageHeight }: UseZoomPanArgs) => {
  const [zoom, setZoom] = useState(1);
  const [isPanning, setIsPanning] = useState(false);

  useEffect(() => {
    const canvas = fabricRef.current;
    if (!canvas) return;

    // Wheel zoom
    canvas.on('mouse:wheel', (opt: any) => {
      const delta = opt.e.deltaY;
      let newZoom = canvas.getZoom();
      newZoom *= 0.999 ** delta;
      newZoom = Math.min(ZOOM_MAX, Math.max(ZOOM_MIN, newZoom));
      canvas.zoomToPoint({ x: opt.e.offsetX, y: opt.e.offsetY }, newZoom);
      setZoom(newZoom);
      opt.e.preventDefault();
      opt.e.stopPropagation();
    });

    // Spacebar pan
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
      if (isPanningLocal) canvas.defaultCursor = 'grab';
    });

    window.addEventListener('keydown', handleKeyDown);
    window.addEventListener('keyup', handleKeyUp);

    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      window.removeEventListener('keyup', handleKeyUp);
    };
  }, [fabricRef]);

  const zoomIn = () => {
    const canvas = fabricRef.current;
    if (!canvas) return;
    let newZoom = canvas.getZoom() * ZOOM_STEP;
    newZoom = Math.min(ZOOM_MAX, newZoom);
    canvas.setZoom(newZoom);
    setZoom(newZoom);
    canvas.requestRenderAll();
  };

  const zoomOut = () => {
    const canvas = fabricRef.current;
    if (!canvas) return;
    let newZoom = canvas.getZoom() / ZOOM_STEP;
    newZoom = Math.max(ZOOM_MIN, newZoom);
    canvas.setZoom(newZoom);
    setZoom(newZoom);
    canvas.requestRenderAll();
  };

  const fitToScreen = () => {
    const canvas = fabricRef.current;
    const container = containerRef.current;
    if (!canvas || !container) return;

    const containerWidth = container.clientWidth;
    const containerHeight = container.clientHeight;

    const scaleX = (containerWidth * 0.85) / pageWidth;
    const scaleY = (containerHeight * 0.85) / pageHeight;
    const newZoom = Math.min(scaleX, scaleY);

    const centerX = containerWidth / 2 - (pageWidth / 2) * newZoom;
    const centerY = containerHeight / 2 - (pageHeight / 2) * newZoom;

    canvas.setZoom(newZoom);
    setZoom(newZoom);
    canvas.setViewportTransform([newZoom, 0, 0, newZoom, centerX, centerY]);
    canvas.requestRenderAll();
  };

  return { zoom, isPanning, zoomIn, zoomOut, fitToScreen };
};

export default useZoomPan;


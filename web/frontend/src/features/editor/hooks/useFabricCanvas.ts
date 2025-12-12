import { useEffect, useRef } from 'react';
import { fabric } from 'fabric';

type UseFabricCanvasArgs = {
  containerRef: React.RefObject<HTMLDivElement>;
  canvasRef: React.RefObject<HTMLCanvasElement>;
  pageWidth: number;
  pageHeight: number;
};

export const useFabricCanvas = ({ containerRef, canvasRef, pageWidth, pageHeight }: UseFabricCanvasArgs) => {
  const fabricRef = useRef<fabric.Canvas | null>(null);

  useEffect(() => {
    if (!canvasRef.current || !containerRef.current) return;

    const containerWidth = containerRef.current?.clientWidth || 800;
    const containerHeight = containerRef.current?.clientHeight || 600;

    const canvas = new fabric.Canvas(canvasRef.current, {
      width: containerWidth,
      height: containerHeight,
      backgroundColor: 'transparent',
    });

    // Center the page in the viewport at 100% zoom
    const centerX = containerWidth / 2 - pageWidth / 2;
    const centerY = containerHeight / 2 - pageHeight / 2;
    canvas.setZoom(1);
    canvas.setViewportTransform([1, 0, 0, 1, centerX, centerY]);
    canvas.requestRenderAll();

    fabricRef.current = canvas;

    // Cleanup
    return () => {
      canvas.dispose();
      fabricRef.current = null;
    };
  }, [canvasRef, containerRef, pageWidth, pageHeight]);

  return { fabricRef, pageLeft: 0, pageTop: 0, pageWidth, pageHeight };
};

export default useFabricCanvas;


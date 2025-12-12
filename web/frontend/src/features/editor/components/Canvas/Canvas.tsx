import { useRef } from 'react';
import { useDesignStore } from '../../../../shared/store/designStore';
import useFabricCanvas from '../../hooks/useFabricCanvas';
import useGuides from '../../hooks/useGuides';
import useZoomPan from '../../hooks/useZoomPan';
import useElementsSync from '../../hooks/useElementsSync';
import useTools from '../../hooks/useTools';

const Canvas = () => {
  const containerRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const { design, currentPage, activeTool, addElement, updateElement, selectElement } = useDesignStore();

  const pageWidth = design?.page_width || 432;
  const pageHeight = design?.page_height || 648;

  const { fabricRef, pageLeft, pageTop } = useFabricCanvas({
    containerRef,
    canvasRef,
    pageWidth,
    pageHeight,
  });

  useGuides(fabricRef, pageWidth, pageHeight, pageLeft, pageTop);

  useElementsSync({
    fabricRef,
    design,
    currentPage,
    updateElement,
    selectElement,
    offsetX: pageLeft,
    offsetY: pageTop,
  });

  useTools({
    fabricRef,
    design,
    activeTool,
    addElement,
  });

  const { zoom, isPanning, zoomIn, zoomOut, fitToScreen } = useZoomPan({
    fabricRef,
    containerRef,
    pageWidth,
    pageHeight,
  });

  return (
    <div
      ref={containerRef}
      className="w-full h-full flex items-center justify-center bg-gray-900 relative overflow-auto"
      style={{
        backgroundImage: 'radial-gradient(circle, #374151 1px, transparent 1px)',
        backgroundSize: '20px 20px',
      }}
    >
      <canvas ref={canvasRef} />

      <div className="absolute bottom-4 right-4 flex items-center gap-2 bg-gray-800 rounded-lg px-3 py-2 shadow-lg">
        <button onClick={zoomOut} className="text-white hover:text-blue-400 text-sm font-medium px-2" title="Zoom out">
          −
        </button>
        <span className="text-white text-xs font-mono min-w-[45px] text-center">{Math.round(zoom * 100)}%</span>
        <button onClick={zoomIn} className="text-white hover:text-blue-400 text-sm font-medium px-2" title="Zoom in">
          +
        </button>
        <div className="w-px h-4 bg-gray-600 mx-1"></div>
        <button onClick={fitToScreen} className="text-white hover:text-blue-400 text-xs px-2" title="Fit to screen">
          Fit
        </button>
      </div>

      {isPanning && (
        <div className="absolute top-4 left-1/2 transform -translate-x-1/2 bg-blue-600 text-white px-4 py-2 rounded-lg shadow-lg text-sm">
          Hold spacebar and drag to pan
        </div>
      )}
    </div>
  );
};

export default Canvas;


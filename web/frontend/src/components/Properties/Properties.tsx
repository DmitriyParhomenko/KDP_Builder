/**
 * Properties Component - Right sidebar for element properties
 */

import { useDesignStore } from '../../store/designStore';

const Properties = () => {
  const { design, currentPage, selectedElements, updateElement } = useDesignStore();

  if (!design || selectedElements.length === 0) {
    return (
      <div className="p-4">
        <h3 className="text-sm font-semibold text-gray-400 mb-4">Properties</h3>
        <p className="text-sm text-gray-500">Select an element to edit its properties</p>
      </div>
    );
  }

  const selectedId = selectedElements[0];
  const element = design.pages[currentPage]?.elements.find(e => e.id === selectedId);

  if (!element) return null;

  const handlePropertyChange = (key: string, value: any) => {
    updateElement(element.id, {
      properties: {
        ...element.properties,
        [key]: value,
      },
    });
  };

  const handlePositionChange = (key: 'x' | 'y' | 'width' | 'height' | 'rotation', value: number) => {
    updateElement(element.id, { [key]: value });
  };

  return (
    <div className="p-4">
      <h3 className="text-sm font-semibold text-gray-400 mb-4">Properties</h3>

      {/* Position & Size */}
      <div className="mb-6">
        <h4 className="text-xs font-semibold text-gray-500 mb-2">Position & Size</h4>
        <div className="grid grid-cols-2 gap-2">
          <div>
            <label className="text-xs text-gray-400">X</label>
            <input
              type="number"
              value={Math.round(element.x)}
              onChange={(e) => handlePositionChange('x', parseFloat(e.target.value))}
              className="w-full px-2 py-1 bg-gray-700 border border-gray-600 rounded text-sm"
            />
          </div>
          <div>
            <label className="text-xs text-gray-400">Y</label>
            <input
              type="number"
              value={Math.round(element.y)}
              onChange={(e) => handlePositionChange('y', parseFloat(e.target.value))}
              className="w-full px-2 py-1 bg-gray-700 border border-gray-600 rounded text-sm"
            />
          </div>
          <div>
            <label className="text-xs text-gray-400">Width</label>
            <input
              type="number"
              value={Math.round(element.width)}
              onChange={(e) => handlePositionChange('width', parseFloat(e.target.value))}
              className="w-full px-2 py-1 bg-gray-700 border border-gray-600 rounded text-sm"
            />
          </div>
          <div>
            <label className="text-xs text-gray-400">Height</label>
            <input
              type="number"
              value={Math.round(element.height)}
              onChange={(e) => handlePositionChange('height', parseFloat(e.target.value))}
              className="w-full px-2 py-1 bg-gray-700 border border-gray-600 rounded text-sm"
            />
          </div>
        </div>
        <div className="mt-2">
          <label className="text-xs text-gray-400">Rotation (degrees)</label>
          <input
            type="number"
            value={Math.round(element.rotation || 0)}
            onChange={(e) => handlePositionChange('rotation', parseFloat(e.target.value))}
            className="w-full px-2 py-1 bg-gray-700 border border-gray-600 rounded text-sm"
            step="1"
            min="0"
            max="360"
          />
        </div>
      </div>

      {/* Text Properties */}
      {element.type === 'text' && (
        <div className="mb-6">
          <h4 className="text-xs font-semibold text-gray-500 mb-2">Text</h4>
          <div className="space-y-2">
            <div>
              <label className="text-xs text-gray-400">Content</label>
              <input
                type="text"
                value={element.properties.text || ''}
                onChange={(e) => handlePropertyChange('text', e.target.value)}
                className="w-full px-2 py-1 bg-gray-700 border border-gray-600 rounded text-sm"
              />
            </div>
            <div>
              <label className="text-xs text-gray-400">Font Size</label>
              <input
                type="number"
                value={element.properties.fontSize || 12}
                onChange={(e) => handlePropertyChange('fontSize', parseFloat(e.target.value))}
                className="w-full px-2 py-1 bg-gray-700 border border-gray-600 rounded text-sm"
              />
            </div>
            <div>
              <label className="text-xs text-gray-400">Font Family</label>
              <select
                value={element.properties.fontFamily || 'Helvetica'}
                onChange={(e) => handlePropertyChange('fontFamily', e.target.value)}
                className="w-full px-2 py-1 bg-gray-700 border border-gray-600 rounded text-sm"
              >
                <option value="Helvetica">Helvetica</option>
                <option value="Helvetica-Bold">Helvetica Bold</option>
                <option value="Times-Roman">Times Roman</option>
                <option value="Courier">Courier</option>
              </select>
            </div>
            <div>
              <label className="text-xs text-gray-400">Color</label>
              <input
                type="color"
                value={element.properties.color || '#000000'}
                onChange={(e) => handlePropertyChange('color', e.target.value)}
                className="w-full h-8 bg-gray-700 border border-gray-600 rounded"
              />
            </div>
          </div>
        </div>
      )}

      {/* Shape Properties */}
      {(element.type === 'rectangle' || element.type === 'circle') && (
        <div className="mb-6">
          <h4 className="text-xs font-semibold text-gray-500 mb-2">Fill & Stroke</h4>
          <div className="space-y-2">
            <div>
              <label className="text-xs text-gray-400">Fill</label>
              <input
                type="color"
                value={element.properties.fill === 'transparent' ? '#ffffff' : element.properties.fill || '#ffffff'}
                onChange={(e) => handlePropertyChange('fill', e.target.value)}
                className="w-full h-8 bg-gray-700 border border-gray-600 rounded"
              />
              <label className="flex items-center gap-2 mt-1">
                <input
                  type="checkbox"
                  checked={element.properties.fill === 'transparent'}
                  onChange={(e) => handlePropertyChange('fill', e.target.checked ? 'transparent' : '#ffffff')}
                  className="rounded"
                />
                <span className="text-xs text-gray-400">Transparent</span>
              </label>
            </div>
            <div>
              <label className="text-xs text-gray-400">Stroke</label>
              <input
                type="color"
                value={element.properties.stroke || '#000000'}
                onChange={(e) => handlePropertyChange('stroke', e.target.value)}
                className="w-full h-8 bg-gray-700 border border-gray-600 rounded"
              />
            </div>
            <div>
              <label className="text-xs text-gray-400">Stroke Width</label>
              <input
                type="number"
                value={element.properties.strokeWidth || 1}
                onChange={(e) => handlePropertyChange('strokeWidth', parseFloat(e.target.value))}
                className="w-full px-2 py-1 bg-gray-700 border border-gray-600 rounded text-sm"
                step="0.5"
                min="0"
              />
            </div>
          </div>
        </div>
      )}

      {/* Line Properties */}
      {element.type === 'line' && (
        <div className="mb-6">
          <h4 className="text-xs font-semibold text-gray-500 mb-2">Line</h4>
          <div className="space-y-2">
            <div>
              <label className="text-xs text-gray-400">Stroke</label>
              <input
                type="color"
                value={element.properties.stroke || '#000000'}
                onChange={(e) => handlePropertyChange('stroke', e.target.value)}
                className="w-full h-8 bg-gray-700 border border-gray-600 rounded"
              />
            </div>
            <div>
              <label className="text-xs text-gray-400">Stroke Width</label>
              <input
                type="number"
                value={element.properties.strokeWidth || 1}
                onChange={(e) => handlePropertyChange('strokeWidth', parseFloat(e.target.value))}
                className="w-full px-2 py-1 bg-gray-700 border border-gray-600 rounded text-sm"
                step="0.5"
                min="0"
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Properties;

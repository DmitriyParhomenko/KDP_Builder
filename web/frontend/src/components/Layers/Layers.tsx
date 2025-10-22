/**
 * Layers Component - Layer management panel
 */

import { Eye, EyeOff, Trash2 } from 'lucide-react';
import { useDesignStore } from '../../store/designStore';

const Layers = () => {
  const { design, currentPage, selectedElements, selectElement, deleteElement } = useDesignStore();

  if (!design) return null;

  const page = design.pages[currentPage];
  if (!page) return null;

  // Sort elements by z_index (top to bottom)
  const sortedElements = [...page.elements].sort((a, b) => b.z_index - a.z_index);

  const getElementLabel = (element: any) => {
    switch (element.type) {
      case 'text':
        return element.properties.text?.substring(0, 20) || 'Text';
      case 'rectangle':
        return 'Rectangle';
      case 'circle':
        return 'Circle';
      case 'line':
        return 'Line';
      default:
        return element.type;
    }
  };

  return (
    <div className="p-4">
      <h3 className="text-sm font-semibold text-gray-400 mb-4">Layers</h3>

      {sortedElements.length === 0 ? (
        <p className="text-sm text-gray-500">No elements yet</p>
      ) : (
        <div className="space-y-1">
          {sortedElements.map((element) => {
            const isSelected = selectedElements.includes(element.id);

            return (
              <div
                key={element.id}
                onClick={() => selectElement(element.id)}
                className={`
                  flex items-center gap-2 px-2 py-1.5 rounded cursor-pointer
                  ${isSelected ? 'bg-blue-600' : 'hover:bg-gray-700'}
                `}
              >
                <Eye className="w-4 h-4 text-gray-400" />
                
                <span className="flex-1 text-sm truncate">
                  {getElementLabel(element)}
                </span>

                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    deleteElement(element.id);
                  }}
                  className="p-1 hover:bg-red-600 rounded"
                  title="Delete"
                >
                  <Trash2 className="w-3 h-3" />
                </button>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default Layers;

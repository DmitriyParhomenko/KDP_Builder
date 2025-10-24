/**
 * Layers Component - Layer management panel
 */

import { useState } from 'react';
import { Eye, EyeOff, Trash2, GripVertical } from 'lucide-react';
import { useDesignStore } from '../../store/designStore';

const Layers = () => {
  const { design, currentPage, selectedElements, selectElement, deleteElement, reorderElement } = useDesignStore();
  const [draggedId, setDraggedId] = useState<string | null>(null);
  const [dragOverId, setDragOverId] = useState<string | null>(null);

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
                draggable
                onDragStart={(e) => {
                  setDraggedId(element.id);
                  e.dataTransfer.effectAllowed = 'move';
                }}
                onDragOver={(e) => {
                  e.preventDefault();
                  e.dataTransfer.dropEffect = 'move';
                  setDragOverId(element.id);
                }}
                onDragLeave={() => {
                  setDragOverId(null);
                }}
                onDrop={(e) => {
                  e.preventDefault();
                  if (draggedId && draggedId !== element.id) {
                    reorderElement(draggedId, element.z_index);
                  }
                  setDraggedId(null);
                  setDragOverId(null);
                }}
                onDragEnd={() => {
                  setDraggedId(null);
                  setDragOverId(null);
                }}
                onClick={() => selectElement(element.id)}
                className={`
                  flex items-center gap-2 px-2 py-1.5 rounded cursor-move transition-all
                  ${isSelected ? 'bg-blue-600' : 'hover:bg-gray-700'}
                  ${draggedId === element.id ? 'opacity-50' : ''}
                  ${dragOverId === element.id ? 'border-t-2 border-blue-400' : ''}
                `}
              >
                <GripVertical className="w-4 h-4 text-gray-500" />
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

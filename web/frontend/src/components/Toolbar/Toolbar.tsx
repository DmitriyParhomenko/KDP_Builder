/**
 * Toolbar Component - Left sidebar with tools
 */

import { MousePointer, Type, Square, Circle, Minus, Hand } from 'lucide-react';
import { useDesignStore } from '../../store/designStore';
import type { Tool } from '../../types/design';

const tools: { id: Tool; icon: any; label: string }[] = [
  { id: 'select', icon: MousePointer, label: 'Select' },
  { id: 'text', icon: Type, label: 'Text' },
  { id: 'rectangle', icon: Square, label: 'Rectangle' },
  { id: 'circle', icon: Circle, label: 'Circle' },
  { id: 'line', icon: Minus, label: 'Line' },
  { id: 'pan', icon: Hand, label: 'Pan' },
];

const Toolbar = () => {
  const { activeTool, setActiveTool } = useDesignStore();

  return (
    <div className="flex flex-col items-center py-4 gap-2">
      {tools.map((tool) => {
        const Icon = tool.icon;
        const isActive = activeTool === tool.id;

        return (
          <button
            key={tool.id}
            onClick={() => setActiveTool(tool.id)}
            className={`
              w-12 h-12 flex items-center justify-center rounded-lg
              transition-colors relative group
              ${isActive 
                ? 'bg-blue-600 text-white' 
                : 'text-gray-400 hover:bg-gray-700 hover:text-white'
              }
            `}
            title={tool.label}
          >
            <Icon className="w-5 h-5" />
            
            {/* Tooltip */}
            <div className="absolute left-full ml-2 px-2 py-1 bg-gray-700 text-white text-xs rounded opacity-0 group-hover:opacity-100 pointer-events-none whitespace-nowrap z-10">
              {tool.label}
            </div>
          </button>
        );
      })}
    </div>
  );
};

export default Toolbar;

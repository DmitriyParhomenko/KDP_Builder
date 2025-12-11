import { FileText, Sparkles, Download, Upload } from 'lucide-react';
import Canvas from './features/editor/components/Canvas/Canvas';
import Toolbar from './features/editor/components/Toolbar/Toolbar';
import Properties from './features/editor/components/Properties/Properties';
import Layers from './features/editor/components/Layers/Layers';
import { useEditorController } from './features/editor/hooks/useEditorController';

function App() {
  const {
    design,
    isLoading,
    showAIDialog,
    setShowAIDialog,
    aiPrompt,
    setAiPrompt,
    aiProgress,
    showDebugLogs,
    setShowDebugLogs,
    debugLogs,
    elapsedTime,
    isLearningFromPDF,
    learnProgress,
    learnLogs,
    showLearnLogs,
    setShowLearnLogs,
    handleLearnFromPDF,
    handleAISuggest,
    handleExport,
  } = useEditorController();


  
  if (isLoading && !design) {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-900 text-white">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-white mx-auto mb-4"></div>
          <p>Loading editor...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-screen bg-gray-900 text-white">
      {/* Top Bar */}
      <div className="flex items-center justify-between px-4 py-2 bg-gray-800 border-b border-gray-700">
        <div className="flex items-center gap-4">
          <FileText className="w-6 h-6 text-blue-500" />
          <h1 className="text-lg font-semibold">KDP Visual Editor</h1>
          {design && (
            <span className="text-sm text-gray-400">
              {design.name} - {design.page_width}x{design.page_height}pt
            </span>
          )}
        </div>

        <div className="flex items-center gap-2">
          {/* Upload PDF for Learning */}
          <label className="px-3 py-1.5 bg-purple-600 hover:bg-purple-700 rounded cursor-pointer text-sm flex items-center gap-2">
            <Upload className="w-4 h-4" />
            Learn from PDF
            <input
              type="file"
              accept=".pdf"
              onChange={handleLearnFromPDF}
              className="hidden"
              disabled={isLearningFromPDF}
            />
          </label>

          {/* AI Suggest Button */}
          <button
            onClick={() => setShowAIDialog(true)}
            className="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 rounded text-sm flex items-center gap-2"
            disabled={isLoading}
          >
            <Sparkles className="w-4 h-4" />
            AI Suggest
          </button>

          {/* Export Button */}
          <button
            onClick={handleExport}
            className="px-3 py-1.5 bg-green-600 hover:bg-green-700 rounded text-sm flex items-center gap-2"
            disabled={isLoading || !design}
          >
            <Download className="w-4 h-4" />
            Export PDF
          </button>
        </div>
      </div>

      {/* Learn from PDF Progress */}
      {isLearningFromPDF && (
        <div className="border-t border-purple-600">
          <div className="px-4 py-2 bg-purple-900 bg-opacity-30 flex items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-purple-400"></div>
              <span className="text-sm text-purple-300">{learnProgress}</span>
            </div>
            <button
              onClick={() => setShowLearnLogs(!showLearnLogs)}
              className="text-xs text-purple-400 hover:text-purple-300 underline"
            >
              {showLearnLogs ? '▼ Hide' : '▶'} Debug Console
            </button>
          </div>
          {/* Debug Console */}
          {showLearnLogs && learnLogs.length > 0 && (
            <div className="px-4 py-2 bg-purple-950 bg-opacity-50 border-t border-purple-700">
              <div className="font-mono text-xs space-y-1 max-h-64 overflow-y-auto">
                {learnLogs.map((log, i) => (
                  <div key={i} className="text-purple-200">{log}</div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Main Editor Area */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left Sidebar - Toolbar */}
        <div className="w-14 bg-gray-800 border-r border-gray-700 flex-shrink-0">
          <Toolbar />
        </div>

        {/* Center - Canvas (Figma-style infinite workspace) */}
        <div className="flex-1 bg-gray-900 relative overflow-hidden">
          {design && <Canvas />}
        </div>

        {/* Right Sidebar - Properties & Layers */}
        <div className="w-72 bg-gray-800 border-l border-gray-700 flex flex-col flex-shrink-0">
          <div className="flex-1 overflow-y-auto">
            <Properties />
          </div>
          <div className="h-56 border-t border-gray-700 overflow-y-auto">
            <Layers />
          </div>
        </div>
      </div>

      {/* AI Dialog */}
      {showAIDialog && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-gray-800 rounded-lg p-6 w-[600px] max-h-[80vh] overflow-auto">
            <h2 className="text-xl font-semibold mb-4">AI Layout Suggestion</h2>
            <textarea
              value={aiPrompt}
              onChange={(e) => setAiPrompt(e.target.value)}
              placeholder="Describe what you want... (e.g., 'Create a habit tracker with 7-day grid')"
              className="w-full h-32 px-3 py-2 bg-gray-700 border border-gray-600 rounded text-white resize-none"
              disabled={isLoading}
            />
            
            {/* Progress Status */}
            {isLoading && aiProgress && (
              <div className="mt-4 p-3 bg-blue-900 bg-opacity-30 border border-blue-600 rounded">
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-400"></div>
                    <span className="text-sm text-blue-300">{aiProgress}</span>
                  </div>
                  <span className="text-xs text-blue-400 font-mono">{elapsedTime}s</span>
                </div>
              </div>
            )}
            
            {/* Debug Logs Toggle */}
            {isLoading && (
              <button
                onClick={() => setShowDebugLogs(!showDebugLogs)}
                className="mt-2 text-xs text-blue-400 hover:text-blue-300 underline"
              >
                {showDebugLogs ? '▼ Hide' : '▶'} Debug Logs
              </button>
            )}
            
            {/* Debug Logs */}
            {showDebugLogs && debugLogs.length > 0 && (
              <div className="mt-2 p-3 bg-gray-900 border border-gray-700 rounded max-h-48 overflow-y-auto">
                <div className="font-mono text-xs space-y-1">
                  {debugLogs.map((log, i) => (
                    <div key={i} className="text-gray-300">{log}</div>
                  ))}
                </div>
              </div>
            )}
            
            <div className="flex gap-2 mt-4">
              <button
                onClick={handleAISuggest}
                disabled={isLoading || !aiPrompt.trim()}
                className="flex-1 px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isLoading ? 'Generating...' : 'Generate'}
              </button>
              <button
                onClick={() => {
                  if (!isLoading) {
                    setShowAIDialog(false);
                    setAiPrompt('');
                    setAiProgress('');
                    setShowDebugLogs(false);
                    setDebugLogs([]);
                  }
                }}
                disabled={isLoading}
                className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;

/**
 * Main App Component - KDP Visual Editor
 * 
 * Figma-like editor for creating KDP planner interiors
 */

import { useState, useEffect } from 'react';
import { FileText, Sparkles, Download, Upload } from 'lucide-react';
import Canvas from './components/Canvas/Canvas';
import Toolbar from './components/Toolbar/Toolbar';
import Properties from './components/Properties/Properties';
import Layers from './components/Layers/Layers';
import { useDesignStore } from './store/designStore';
import { designsAPI, aiAPI, exportAPI } from './api/client';

function App() {
  const { design, setDesign } = useDesignStore();
  const [isLoading, setIsLoading] = useState(false);
  const [showAIDialog, setShowAIDialog] = useState(false);
  const [aiPrompt, setAiPrompt] = useState('');
  const [aiProgress, setAiProgress] = useState('');
  const [showDebugLogs, setShowDebugLogs] = useState(false);
  const [debugLogs, setDebugLogs] = useState<string[]>([]);
  const [elapsedTime, setElapsedTime] = useState(0);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isLearningFromPDF, setIsLearningFromPDF] = useState(false);
  const [learnProgress, setLearnProgress] = useState('');
  const [learnLogs, setLearnLogs] = useState<string[]>([]);
  const [showLearnLogs, setShowLearnLogs] = useState(false);

  // Create new design on mount
  useEffect(() => {
    createNewDesign();
  }, []);

  // Timer for AI generation
  useEffect(() => {
    let interval: number;
    if (isGenerating) {
      setElapsedTime(0);
      interval = window.setInterval(() => {
        setElapsedTime(prev => {
          const newTime = prev + 1;
          // Add periodic progress updates
          if (newTime % 5 === 0) {
            addDebugLog(`⏱️ Still processing... ${newTime}s elapsed`);
          }
          return newTime;
        });
      }, 1000);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [isGenerating]);

  const createNewDesign = async () => {
    setIsLoading(true);
    try {
      const newDesign = await designsAPI.create({
        name: 'Untitled Design',
        page_width: 432,
        page_height: 648,
        num_pages: 1,
      });
      setDesign(newDesign);
    } catch (error) {
      console.error('Failed to create design:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const addDebugLog = (message: string) => {
    const timestamp = new Date().toLocaleTimeString();
    setDebugLogs(prev => [...prev, `[${timestamp}] ${message}`]);
  };

  const addLearnLog = (message: string) => {
    const timestamp = new Date().toLocaleTimeString();
    setLearnLogs(prev => [...prev, `[${timestamp}] ${message}`]);
  };

  const handleLearnFromPDF = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file || !file.name.toLowerCase().endsWith('.pdf')) {
      alert('Please select a PDF file.');
      return;
    }

    setIsLearningFromPDF(true);
    setLearnProgress('Initializing...');
    setLearnLogs([]);
    addLearnLog(`📂 Selected file: ${file.name} (${(file.size / 1024 / 1024).toFixed(2)} MB)`);
    addLearnLog(`🚀 Starting Learn from PDF flow...`);

    const formData = new FormData();
    formData.append('file', file);
    // Add AI parameters as query string (FastAPI supports Query for multipart)
    const params = new URLSearchParams({
      ai_detect: 'true',
      ai_model: 'both',
      imgsz: '1536',
      tile_size: '640',
      tile_overlap: '160',
    });

    try {
      setLearnProgress('Uploading PDF...');
      addLearnLog(`📤 Uploading PDF to /api/ai/learn`);
      const response = await fetch(`/api/ai/learn?${params}`, {
        method: 'POST',
        body: formData,
      });
      addLearnLog(`⏳ Server processing...`);
      const result = await response.json();
      if (!result.success) {
        throw new Error(result.error || 'Learning failed');
      }

      // Step-by-step logs based on backend flow
      addLearnLog(`✅ PDF analysis completed`);
      addLearnLog(`🤖 AI extraction (DocLayNet + Ollama VLM) completed`);
      addLearnLog(`💾 Pattern stored in ChromaDB: ${result.pattern_id}`);
      addLearnLog(`🖼️ Thumbnail generated`);
      addLearnLog(`📊 Extraction summary: ${result.blocks} blocks, ${result.elements} elements`);
      addLearnLog(`📝 AI description: ${result.description}`);

      setLearnProgress(`Done: ${result.blocks} blocks, ${result.elements} elements`);
    } catch (error: any) {
      setLearnProgress(`Error: ${error.message}`);
      addLearnLog(`❌ Learning failed: ${error.message}`);
    } finally {
      setIsLearningFromPDF(false);
      // Reset file input
      event.target.value = '';
    }
  };

  const handleAISuggest = async () => {
    if (!aiPrompt.trim() || !design) return;

    setIsLoading(true);
    setIsGenerating(true);
    setDebugLogs([]);
    setElapsedTime(0);
    setAiProgress('Initializing AI request...');
    addDebugLog('🚀 Starting AI layout generation');
    addDebugLog(`📝 Prompt: "${aiPrompt}"`);
    addDebugLog(`📐 Canvas size: ${design.page_width}x${design.page_height}pt`);
    addDebugLog('⏳ Waiting for Ollama response...');
    
    try {
      setAiProgress('🤖 Sending request to Ollama (Qwen2.5:7b)...');
      addDebugLog('🔗 Connecting to AI backend...');
      
      const startTime = Date.now();
      const result = await aiAPI.suggest(
        aiPrompt,
        design.page_width,
        design.page_height
      );
      const duration = ((Date.now() - startTime) / 1000).toFixed(1);
      
      addDebugLog(`✅ Response received in ${duration}s`);
      setAiProgress('⚙️ Processing AI response...');

      if (result.success && result.elements) {
        addDebugLog(`✨ Generated ${result.elements.length} elements`);
        setAiProgress(`📦 Adding ${result.elements.length} elements to canvas...`);
        
        // Add AI-generated elements to current page
        const newDesign = { ...design };
        result.elements.forEach((elem: any, index: number) => {
          addDebugLog(`  ${index + 1}. ${elem.type} at (${Math.round(elem.x)}, ${Math.round(elem.y)})`);
          newDesign.pages[0].elements.push({
            id: `elem_${Date.now()}_${Math.random()}`,
            type: elem.type,
            x: elem.x,
            y: elem.y,
            width: elem.width,
            height: elem.height,
            rotation: 0,
            z_index: newDesign.pages[0].elements.length,
            properties: elem.properties || {},
          });
        });
        
        setDesign(newDesign);
        setAiProgress('✅ Complete!');
        addDebugLog('✅ Layout generated successfully!');
        
        // Close dialog after 1 second
        setTimeout(() => {
          setShowAIDialog(false);
          setAiPrompt('');
          setAiProgress('');
          setShowDebugLogs(false);
        }, 1000);
      } else {
        addDebugLog('❌ No elements generated');
        setAiProgress('❌ Failed to generate layout');
      }
    } catch (error: any) {
      console.error('AI suggestion failed:', error);
      addDebugLog(`❌ Error: ${error.message || 'Unknown error'}`);
      setAiProgress(`❌ Error: ${error.message || 'Request failed'}`);
    } finally {
      setIsLoading(false);
      setIsGenerating(false);
    }
  };

  const handleExport = async () => {
    if (!design) return;

    setIsLoading(true);
    try {
      const downloadUrl = await exportAPI.toPDF(design, true);
      // Open download in new tab
      window.open(downloadUrl, '_blank');
    } catch (error) {
      console.error('Export failed:', error);
    } finally {
      setIsLoading(false);
    }
  };

  
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
        <div className="w-16 bg-gray-800 border-r border-gray-700">
          <Toolbar />
        </div>

        {/* Center - Canvas */}
        <div className="flex-1 bg-gray-900 overflow-auto">
          {design && <Canvas />}
        </div>

        {/* Right Sidebar - Properties & Layers */}
        <div className="w-80 bg-gray-800 border-l border-gray-700 flex flex-col">
          <div className="flex-1 overflow-auto">
            <Properties />
          </div>
          <div className="h-64 border-t border-gray-700 overflow-auto">
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

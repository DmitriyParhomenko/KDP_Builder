import { useEffect, useState } from 'react';
import { useDesignStore } from '../../../shared/store/designStore';
import { designsAPI } from '../../design/api/designs';
import { aiAPI } from '../api/ai';
import { exportAPI } from '../../export/api/export';

export const useEditorController = () => {
  const { design, setDesign } = useDesignStore();

  const [isLoading, setIsLoading] = useState(false);
  const [showAIDialog, setShowAIDialog] = useState(false);
  const [aiPrompt, setAiPrompt] = useState('');
  const [aiProgress, setAiProgress] = useState('');
  const [debugLogs, setDebugLogs] = useState<string[]>([]);
  const [showDebugLogs, setShowDebugLogs] = useState(false);
  const [elapsedTime, setElapsedTime] = useState(0);
  const [isGenerating, setIsGenerating] = useState(false);

  const [isLearningFromPDF, setIsLearningFromPDF] = useState(false);
  const [learnProgress, setLearnProgress] = useState('');
  const [learnLogs, setLearnLogs] = useState<string[]>([]);
  const [showLearnLogs, setShowLearnLogs] = useState(false);

  // init design
  useEffect(() => {
    createNewDesign();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // timer for AI generation
  useEffect(() => {
    let interval: number | undefined;
    if (isGenerating) {
      setElapsedTime(0);
      interval = window.setInterval(() => {
        setElapsedTime((prev) => {
          const next = prev + 1;
          if (next % 5 === 0) addDebugLog(`⏱️ Still processing... ${next}s elapsed`);
          return next;
        });
      }, 1000);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [isGenerating]);

  const addDebugLog = (message: string) => {
    const timestamp = new Date().toLocaleTimeString();
    setDebugLogs((prev) => [...prev, `[${timestamp}] ${message}`]);
  };

  const addLearnLog = (message: string) => {
    const timestamp = new Date().toLocaleTimeString();
    setLearnLogs((prev) => [...prev, `[${timestamp}] ${message}`]);
  };

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
    addLearnLog(`🚀 Starting OpenRouter AI learning (Claude Sonnet 3.5 + Grok Beta)...`);

    const formData = new FormData();
    formData.append('file', file);
    const params = new URLSearchParams({ use_openrouter: 'true' });

    try {
      setLearnProgress('Uploading PDF...');
      addLearnLog(`📤 Uploading PDF to /api/ai/learn with OpenRouter`);

      const startTime = Date.now();
      const response = await fetch(`/api/ai/learn?${params}`, {
        method: 'POST',
        body: formData,
      });

      addLearnLog(`⏳ Claude Sonnet 3.5 analyzing PDF...`);
      const result = await response.json();
      const duration = ((Date.now() - startTime) / 1000).toFixed(1);

      if (!result.success) {
        throw new Error(result.error || 'Learning failed');
      }

      addLearnLog(`✅ Claude analysis completed in ${duration}s`);
      addLearnLog(`🤖 Extracted ${result.blocks} blocks with AI vision`);
      addLearnLog(`🎨 Grok generated pattern template`);
      addLearnLog(`💾 Pattern stored in ChromaDB: ${result.pattern_id}`);
      addLearnLog(`🖼️ Full-size thumbnail generated (1800x2700px)`);
      addLearnLog(`📝 AI description: ${result.description.substring(0, 100)}...`);

      setLearnProgress(`✅ Done: ${result.blocks} blocks extracted in ${duration}s`);

      setTimeout(() => setShowLearnLogs(false), 3000);
    } catch (error: any) {
      setLearnProgress(`❌ Error: ${error.message}`);
      addLearnLog(`❌ Learning failed: ${error.message}`);
    } finally {
      setIsLearningFromPDF(false);
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
      const result = await aiAPI.suggest(aiPrompt, design.page_width, design.page_height);
      const duration = ((Date.now() - startTime) / 1000).toFixed(1);

      addDebugLog(`✅ Response received in ${duration}s`);
      setAiProgress('⚙️ Processing AI response...');

      if (result.success && result.elements) {
        addDebugLog(`✨ Generated ${result.elements.length} elements`);
        setAiProgress(`📦 Adding ${result.elements.length} elements to canvas...`);

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
      window.open(downloadUrl, '_blank');
    } catch (error) {
      console.error('Export failed:', error);
    } finally {
      setIsLoading(false);
    }
  };

  return {
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
  };
};

export default useEditorController;


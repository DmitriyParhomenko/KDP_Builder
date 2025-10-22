"""
AI service using Ollama for layout generation

This service uses Qwen2.5:7b to generate layout suggestions based on
learned patterns from Etsy PDFs.
"""

import ollama
import json
from typing import Dict, Any, List, Optional
from web.backend.services.pattern_db import pattern_db

class AIService:
    """AI-powered layout generation using Ollama"""
    
    def __init__(self, model: str = "qwen2.5:7b"):
        """
        Initialize AI service.
        
        Args:
            model: Ollama model to use
        """
        self.model = model
        print(f"🤖 AI Service initialized with model: {self.model}")
    
    def generate_layout(
        self,
        prompt: str,
        page_width: float = 432.0,
        page_height: float = 648.0,
        context_patterns: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Generate layout from prompt using AI.
        
        Args:
            prompt: User's layout request (e.g., "Create a habit tracker")
            page_width: Page width in points
            page_height: Page height in points
            context_patterns: Optional pre-fetched similar patterns
            
        Returns:
            Dictionary with generated elements and metadata
        """
        print(f"🎨 Generating layout for: {prompt}")
        
        # Search for similar patterns if not provided
        if context_patterns is None:
            context_patterns = pattern_db.search_patterns(prompt, n_results=3)
        
        # Build context from similar patterns
        context = self._build_context(context_patterns)
        
        # Create prompt for AI
        full_prompt = f"""You are a professional KDP planner designer. Generate a JSON layout for this request:

REQUEST: {prompt}

PAGE DIMENSIONS: {page_width}pt x {page_height}pt (6x9 inches)

PROFESSIONAL EXAMPLES FROM ETSY:
{context}

TASK: Generate a JSON array of design elements. Each element must have:
- type: "text", "rectangle", "circle", or "line"
- x, y: position in points (origin at bottom-left)
- width, height: dimensions in points
- properties: object with element-specific properties

EXAMPLE OUTPUT:
[
  {{
    "type": "text",
    "x": 216,
    "y": 580,
    "width": 300,
    "height": 50,
    "properties": {{
      "text": "HABIT TRACKER",
      "fontSize": 48,
      "fontFamily": "Helvetica-Bold",
      "color": "#2C2C2C",
      "align": "center"
    }}
  }},
  {{
    "type": "rectangle",
    "x": 50,
    "y": 400,
    "width": 15,
    "height": 15,
    "properties": {{
      "fill": "none",
      "stroke": "#CCCCCC",
      "strokeWidth": 0.5
    }}
  }}
]

IMPORTANT:
- Use professional measurements from examples
- Y-axis: 0 at bottom, {page_height} at top
- Keep margins: 36pt minimum from edges
- Use large fonts for headers (48pt)
- Use light colors for lines (#CCCCCC)
- Return ONLY valid JSON array, no explanations

GENERATE LAYOUT:"""
        
        try:
            # Generate with Ollama
            response = ollama.generate(
                model=self.model,
                prompt=full_prompt
            )
            
            # Extract JSON from response
            layout_json = self._extract_json(response['response'])
            
            if layout_json:
                return {
                    "success": True,
                    "elements": layout_json,
                    "context_patterns": [p["id"] for p in context_patterns],
                    "model": self.model
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to parse AI response",
                    "raw_response": response['response'][:500]
                }
                
        except Exception as e:
            print(f"❌ Error generating layout: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def suggest_improvements(
        self,
        current_design: Dict[str, Any]
    ) -> List[str]:
        """
        Suggest improvements for current design.
        
        Args:
            current_design: Current design data
            
        Returns:
            List of improvement suggestions
        """
        prompt = f"""Analyze this planner design and suggest 3 specific improvements:

CURRENT DESIGN:
{json.dumps(current_design, indent=2)}

Provide actionable suggestions for:
1. Layout and spacing
2. Typography and readability
3. Professional polish

Format as numbered list."""
        
        try:
            response = ollama.generate(
                model=self.model,
                prompt=prompt
            )
            
            # Parse suggestions (simple split for now)
            suggestions = []
            for line in response['response'].split('\n'):
                line = line.strip()
                if line and (line[0].isdigit() or line.startswith('-') or line.startswith('•')):
                    suggestions.append(line)
            
            return suggestions[:3]  # Return top 3
            
        except Exception as e:
            print(f"❌ Error generating suggestions: {e}")
            return ["Unable to generate suggestions at this time"]
    
    def analyze_pdf_pattern(
        self,
        pdf_analysis: Dict[str, Any]
    ) -> str:
        """
        Generate a description of a PDF pattern for storage.
        
        Args:
            pdf_analysis: Analysis results from PDF analyzer
            
        Returns:
            Human-readable description
        """
        prompt = f"""Describe this planner design pattern in 2-3 sentences:

ANALYSIS:
{json.dumps(pdf_analysis, indent=2)}

Focus on:
- Layout structure
- Key elements and their sizes
- Design style and purpose

Be concise and descriptive."""
        
        try:
            response = ollama.generate(
                model=self.model,
                prompt=prompt
            )
            return response['response'].strip()
        except Exception as e:
            print(f"❌ Error analyzing pattern: {e}")
            return "Professional planner layout"
    
    def _build_context(self, patterns: List[Dict[str, Any]]) -> str:
        """Build context string from similar patterns"""
        if not patterns:
            return "No similar patterns found. Use professional KDP standards."
        
        context_parts = []
        for i, pattern in enumerate(patterns, 1):
            context_parts.append(f"Example {i}:")
            context_parts.append(f"  Description: {pattern['description']}")
            if pattern.get('metadata'):
                context_parts.append(f"  Metadata: {json.dumps(pattern['metadata'])}")
        
        return "\n".join(context_parts)
    
    def _extract_json(self, text: str) -> Optional[List[Dict[str, Any]]]:
        """Extract JSON array from AI response"""
        # Try to find JSON array in response
        start = text.find('[')
        end = text.rfind(']')
        
        if start != -1 and end != -1:
            json_str = text[start:end+1]
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                pass
        
        # Try parsing entire response
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return None

# Global instance
ai_service = AIService()

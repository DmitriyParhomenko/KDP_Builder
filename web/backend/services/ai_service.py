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
    "width": 200,
    "height": 50,
    "properties": {{
      "text": "HABIT TRACKER",
      "fontSize": 48,
      "fontFamily": "Helvetica",
      "color": "#2C2C2C",
      "align": "center"
    }}
  }},
  {{
    "type": "rectangle",
    "x": 50,
    "y": 400,
    "width": 18,
    "height": 18,
    "properties": {{
      "fill": "none",
      "stroke": "#CCCCCC",
      "strokeWidth": 0.5
    }}
  }}
]

CRITICAL RULES:
1. TEXT WIDTH: Calculate based on content length
   - Short text (1-5 chars): 30-50pt
   - Medium text (6-15 chars): 60-120pt
   - Long text (16+ chars): 150-300pt
   - Headers: 200-350pt

2. FONT FAMILY: Use ONLY "Helvetica" (not "Helvetica-Bold")

3. ALIGNMENT: When creating rows of elements:
   - Align labels directly above/below their corresponding elements
   - Use same X position for aligned elements
   - Space evenly across available width

4. ELEMENT COUNTING: If request says "7 checkboxes", generate EXACTLY 7
   - Count carefully before generating
   - Verify all requested elements are included

5. SPACING: Calculate proper spacing
   - Total width available: {page_width - 72}pt (with 36pt margins)
   - For N elements: spacing = available_width / (N + 1)
   - Element X = margin + (spacing * element_number)

6. COORDINATES:
   - Y-axis: 0 at bottom, {page_height} at top
   - Keep margins: 36pt minimum from all edges
   - Headers at top: y = {page_height - 80}
   - Content area: y = 100 to {page_height - 120}

7. SIZES:
   - Checkboxes: 18x18pt (not 15x15)
   - Headers: 48pt font
   - Labels: 14-16pt font
   - Minimum clickable area: 18x18pt

8. RETURN FORMAT: ONLY valid JSON array, no explanations, no markdown

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
                # Validate and fix common issues
                layout_json = self._validate_and_fix_layout(layout_json, page_width, page_height)
                
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
    
    def _validate_and_fix_layout(
        self, 
        elements: List[Dict[str, Any]], 
        page_width: float, 
        page_height: float
    ) -> List[Dict[str, Any]]:
        """
        Validate and fix common issues in AI-generated layouts.
        
        Args:
            elements: List of generated elements
            page_width: Page width in points
            page_height: Page height in points
            
        Returns:
            Fixed list of elements
        """
        fixed_elements = []
        
        for elem in elements:
            # Fix font family
            if elem.get('properties', {}).get('fontFamily') == 'Helvetica-Bold':
                elem['properties']['fontFamily'] = 'Helvetica'
            
            # Fix text width for short labels
            if elem.get('type') == 'text':
                text = elem.get('properties', {}).get('text', '')
                current_width = elem.get('width', 300)
                # Sanitize text alignment and baseline to valid values
                props = elem.setdefault('properties', {})
                align = str(props.get('align', 'left')).lower()
                if align not in {'left','center','right','justify','start','end'}:
                    props['align'] = 'left'
                baseline = str(props.get('textBaseline', 'alphabetic')).lower()
                # valid canvas baselines: top, hanging, middle, alphabetic, ideographic, bottom
                if baseline == 'alphabetical':
                    baseline = 'alphabetic'
                if baseline not in {'top','hanging','middle','alphabetic','ideographic','bottom'}:
                    baseline = 'alphabetic'
                # store sanitized baseline if front-end ever uses it
                props['textBaseline'] = baseline
                
                # Calculate reasonable width based on text length
                if len(text) <= 5 and current_width > 100:
                    elem['width'] = 60
                elif len(text) <= 15 and current_width > 200:
                    elem['width'] = 120
            
            # Ensure minimum sizes and normalize styling for rectangles
            if elem.get('type') == 'rectangle':
                if elem.get('width', 0) < 15:
                    elem['width'] = 18
                if elem.get('height', 0) < 15:
                    elem['height'] = 18
                props = elem.setdefault('properties', {})
                # Normalize fill: treat 'none' or empty as transparent
                fill = str(props.get('fill', '') or '').lower()
                if fill in {'', 'none', 'null'}:
                    props['fill'] = 'transparent'
                # Clamp stroke color and width
                stroke = props.get('stroke') or '#CCCCCC'
                props['stroke'] = stroke
                sw = props.get('strokeWidth')
                try:
                    sw_val = float(sw) if sw is not None else 0.5
                except (TypeError, ValueError):
                    sw_val = 0.5
                props['strokeWidth'] = max(0.25, min(sw_val, 2.0))
            
            # Clamp positions to page bounds with margins
            elem['x'] = max(36, min(elem.get('x', 0), page_width - 36))
            elem['y'] = max(36, min(elem.get('y', 0), page_height - 36))
            
            fixed_elements.append(elem)
        
        # Post-processing: evenly distribute weekly columns and align labels
        try:
            margin = 36.0
            available_w = max(0.0, page_width - 2 * margin)
            
            # 1) Find checkbox rectangles (candidate columns)
            rects = [e for e in fixed_elements if e.get('type') == 'rectangle']
            texts = [e for e in fixed_elements if e.get('type') == 'text']
            
            # Helper: group items by approximate y (row clustering)
            def cluster_by_y(items: List[Dict[str, Any]], tol: float = 30.0) -> List[List[Dict[str, Any]]]:
                items_sorted = sorted(items, key=lambda it: it.get('y', 0))
                clusters: List[List[Dict[str, Any]]] = []
                for it in items_sorted:
                    placed = False
                    for cluster in clusters:
                        # compare with cluster center y
                        cy = sum(c.get('y', 0) for c in cluster) / max(1, len(cluster))
                        if abs(it.get('y', 0) - cy) <= tol:
                            cluster.append(it)
                            placed = True
                            break
                    if not placed:
                        clusters.append([it])
                return clusters
            
            rect_rows = cluster_by_y(rects)
            
            # 2) For each row that looks like columns (N>=3), distribute X evenly
            for row in rect_rows:
                if len(row) < 3:
                    continue
                # Sort by current x to preserve order left->right
                row_sorted = sorted(row, key=lambda r: r.get('x', 0))
                N = len(row_sorted)
                # Use average width to compute spacing to avoid clipping at right margin
                avg_w = sum(r.get('width', 18) for r in row_sorted) / N
                # distance between left edges so last rectangle's right edge stays within page
                step = (available_w - avg_w) / max(1, (N - 1)) if N > 1 else 0
                for idx, r in enumerate(row_sorted):
                    target_x = margin + idx * step
                    r['x'] = max(margin, min(target_x, page_width - margin - r.get('width', 18)))
                
                # 3) Align nearby day labels to same X
                # Find labels likely associated with this row: within vertical window above/below rectangles
                row_y_min = min(r.get('y', 0) for r in row_sorted)
                row_y_max = max(r.get('y', 0) + r.get('height', 0) for r in row_sorted)
                label_window_top = row_y_max + 60  # labels can be somewhat above
                label_window_bottom = row_y_min - 60  # or slightly below
                row_labels = [t for t in texts if label_window_bottom <= t.get('y', 0) <= label_window_top]
                if row_labels:
                    # sort both by x and pair by order
                    row_labels_sorted = sorted(row_labels, key=lambda t: t.get('x', 0))
                    pairs = min(len(row_sorted), len(row_labels_sorted))
                    for i in range(pairs):
                        label = row_labels_sorted[i]
                        rect = row_sorted[i]
                        rect_x = rect.get('x', 0)
                        rect_w = rect.get('width', 18)
                        # Fit label within its column span: step minus padding
                        max_label_w = max(30.0, step - 8.0) if step > 0 else label.get('width', 60) or 60
                        label_w = float(label.get('width', 60) or 60)
                        label_w = max(30.0, min(label_w, max_label_w))
                        label['width'] = label_w
                        # Center label horizontally over rect
                        label['x'] = rect_x + (rect_w / 2) - (label_w / 2)
                        # Ensure label is ABOVE checkbox in bottom-left coordinates
                        desired_gap = 12.0
                        label['y'] = max(label.get('y', 0), rect.get('y', 0) + rect.get('height', 0) + desired_gap)
            
        except Exception as _:
            # Fail-safe: never break generation because of post-processing
            pass
        
        # Helpers for approximate text measurement (simple heuristic)
        def _estimate_text_size(text: str, font_size: float) -> (float, float):
            avg_char_width = 0.55  # empirical for Helvetica
            width = max(1.0, len(text) * font_size * avg_char_width)
            height = max(12.0, font_size * 1.2)
            return width, height

        # Final pass: convert bottom-left (AI) -> top-left (Fabric) and clamp using estimated text sizes
        tl_elements: List[Dict[str, Any]] = []
        for elem in fixed_elements:
            w = float(elem.get('width', 0) or 0)
            h = float(elem.get('height', 0) or 0)
            t = elem.get('type')
            props = elem.get('properties', {})
            if t == 'text':
                text = props.get('text', '')
                fs = float(props.get('fontSize', 14) or 14)
                est_w, est_h = _estimate_text_size(text, fs)
                # Cap header/labels to available width
                max_w = available_w
                if est_w > max_w and est_w > 0:
                    scale = max(0.5, max_w / est_w)
                    fs = max(8.0, fs * scale)
                    props['fontSize'] = fs
                    est_w, est_h = _estimate_text_size(text, fs)
                w, h = est_w, est_h
                elem['width'] = w
                elem['height'] = h
                elem['properties'] = props
            # Convert Y: top = page_height - bottom_y - height
            bottom_y = float(elem.get('y', 0) or 0)
            top_y = page_height - bottom_y - h
            # Clamp in top-left coordinates
            clamped_x = max(36.0, min(float(elem.get('x', 0) or 0), page_width - 36.0 - w))
            clamped_y = max(36.0, min(top_y, page_height - 36.0 - h))
            elem['x'] = clamped_x
            elem['y'] = clamped_y
            tl_elements.append(elem)

        # Resolve overlaps by pushing elements down with a small gap
        def _overlap(a: Dict[str, Any], b: Dict[str, Any]) -> bool:
            ax, ay, aw, ah = a['x'], a['y'], a.get('width', 0), a.get('height', 0)
            bx, by, bw, bh = b['x'], b['y'], b.get('width', 0), b.get('height', 0)
            return not (ax + aw <= bx or bx + bw <= ax or ay + ah <= by or by + bh <= ay)

        tl_elements.sort(key=lambda e: (e['y'], e['x']))  # top to bottom
        gap = 8.0
        for i in range(len(tl_elements)):
            for j in range(i):
                if _overlap(tl_elements[i], tl_elements[j]):
                    # push current below previous bottom + gap
                    prev_bottom = tl_elements[j]['y'] + tl_elements[j].get('height', 0)
                    tl_elements[i]['y'] = max(tl_elements[i]['y'], prev_bottom + gap)
                    # keep inside bottom margin
                    max_top = page_height - 36.0 - tl_elements[i].get('height', 0)
                    tl_elements[i]['y'] = min(tl_elements[i]['y'], max_top)

        fixed_elements = tl_elements
        
        print(f"✅ Validated {len(fixed_elements)} elements")
        return fixed_elements
    
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

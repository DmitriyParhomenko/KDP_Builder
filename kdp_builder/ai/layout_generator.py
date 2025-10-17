import json
import re
import requests
from typing import Dict, List, Any
import click

class AILayoutGenerator:
    def __init__(self, model: str = "tinyllama", base_url: str = "http://localhost:11434"):
        # Using tinyllama for faster local AI generation (1.1B params vs llama3.2's 3B)
        self.model = model
        self.base_url = base_url

    def generate_layout(self, prompt: str, schema: Dict[str, Any], gutter_pt: float = 0.0) -> Dict[str, Any]:
        """
        Generate a layout JSON based on the prompt, schema, and gutter settings.

        Args:
            prompt: User prompt describing the layout.
            schema: JSON schema for the layout structure.
            gutter_pt: Gutter in points for binding side (left for odd, right for even).

        Returns:
            Generated layout as a dictionary.
        """
        # Incorporate gutter into the prompt for better AI understanding
        gutter_prompt = f"Include a {gutter_pt}pt gutter on the binding side (left for odd pages, right for even pages)."
        full_prompt = f"""
You are an expert layout designer for KDP book interiors. I need you to generate a JSON layout for a habit tracker.

IMPORTANT INSTRUCTIONS:
- Output ONLY valid JSON - no explanations, no markdown, no extra text
- Generate EXACTLY 4 pages
- Each page must have a "page_number" and "elements" array
- Elements must have "type", "x", "y", "width", "height" (required)
- For habit tracker: use "checkbox" elements for habits, "text" for labels
- Apply gutters correctly: odd pages have left gutter, even pages have right gutter

PROMPT: {prompt} {gutter_prompt}

SCHEMA: {json.dumps(schema, indent=2)}

OUTPUT FORMAT (copy this structure exactly):
{{
  "pages": [
    {{
      "page_number": 1,
      "elements": [
        {{
          "type": "text",
          "x": 18,
          "y": 50,
          "width": 100,
          "height": 20,
          "content": "Habit 1",
          "style": {{"fontFamily": "Arial", "fontSize": 12}}
        }},
        {{
          "type": "checkbox",
          "x": 18,
          "y": 75,
          "width": 15,
          "height": 15,
          "content": ""
        }}
      ]
    }},
    {{
      "page_number": 2,
      "elements": [
        {{
          "type": "text",
          "x": 18,
          "y": 50,
          "width": 100,
          "height": 20,
          "content": "Habit 2",
          "style": {{"fontFamily": "Arial", "fontSize": 12}}
        }}
      ]
    }},
    {{
      "page_number": 3,
      "elements": []
    }},
    {{
      "page_number": 4,
      "elements": []
    }}
  ]
}}

Generate the layout JSON now - ONLY the JSON object, nothing else:
"""

        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": full_prompt,
                    "stream": True  # Enable streaming for progress
                },
                timeout=120
            )
            response.raise_for_status()
            
            layout_str = ""
            click.echo("🤖 Ollama is thinking...", err=True)
            for line in response.iter_lines():
                if line:
                    try:
                        data = json.loads(line.decode('utf-8'))
                        if 'response' in data:
                            chunk = data['response']
                            layout_str += chunk
                            click.echo(chunk, nl=False, err=True)  # Print chunks as they arrive
                        if data.get('done', False):
                            break
                    except json.JSONDecodeError:
                        continue
            
            click.echo("\n✅ Layout generated!", err=True)  # New line after response
            
            # Clean the response (remove any non-JSON text)
            layout_str = layout_str.strip()
            if layout_str.startswith("```json"):
                layout_str = layout_str[7:]
            if layout_str.endswith("```"):
                layout_str = layout_str[:-3]

            # Remove any leading/trailing non-JSON text - handle cases like [Object] or other prefixes
            layout_str = re.sub(r'^[^{]*', '', layout_str)  # Remove anything before {
            layout_str = re.sub(r'}[^}]*$', '}', layout_str)  # Remove anything after }

            # Additional cleaning for common AI response artifacts
            layout_str = re.sub(r'^\[Object\]\s*', '', layout_str)  # Remove [Object] prefix
            layout_str = re.sub(r'^Object\s*', '', layout_str)  # Remove Object prefix
            layout_str = re.sub(r'^\[\s*', '{', layout_str)  # Fix array start
            layout_str = re.sub(r'\s*\]$', '}', layout_str)  # Fix array end

            # Remove any text that looks like explanations or metadata
            layout_str = re.sub(r'^[A-Za-z\s]+:\s*', '', layout_str)  # Remove "Response:" type prefixes
            layout_str = re.sub(r'^[^{]*\{', '{', layout_str)  # Ensure starts with {

            # Clean up any remaining non-JSON characters at the end
            layout_str = re.sub(r'[^}]*$', '}', layout_str)

            # Fix trailing commas before closing brackets
            layout_str = re.sub(r',(\s*[\]}])', r'\1', layout_str)

            # Fix common issues: remove extra keys like 'type' and 'required' if present
            try:
                parsed = json.loads(layout_str)
                if 'type' in parsed:
                    del parsed['type']
                if 'required' in parsed:
                    del parsed['required']
                layout = parsed
            except json.JSONDecodeError as e:
                # If still fails, try to extract just the pages array
                pages_match = re.search(r'("pages":\s*\[.*\])', layout_str, re.DOTALL)
                if pages_match:
                    layout_str = '{' + pages_match.group(1) + '}'
                    try:
                        layout = json.loads(layout_str)
                    except json.JSONDecodeError:
                        # Try to find a complete JSON object within the string
                        json_objects = re.findall(r'\{[^}]*"pages"[^}]*\}', layout_str, re.DOTALL)
                        for obj in json_objects:
                            try:
                                layout = json.loads(obj)
                                break
                            except json.JSONDecodeError:
                                continue
                        else:
                            # Last resort: try to manually construct a basic layout
                            layout = {"pages": []}
                            click.echo("⚠️ Warning: AI response was malformed, using empty layout", err=True)
                else:
                    # Last resort: try to fix common issues like trailing commas
                    layout_str = re.sub(r',(\s*[\]}])', r'\1', layout_str)
                    try:
                        layout = json.loads(layout_str)
                    except json.JSONDecodeError:
                        # Ultimate fallback: create empty layout
                        layout = {"pages": []}
                        click.echo("⚠️ Warning: Could not parse AI response, using empty layout", err=True)

            # If AI generated empty layout, use fallback generator
            if not layout.get("pages"):
                click.echo("🤖 AI failed, using fallback layout generator...", err=True)
                layout = self._generate_fallback_layout(prompt, gutter_pt)

            # Post-process to adjust positions for gutters (if not handled by AI)
            layout = self._apply_gutters(layout, gutter_pt)
            return layout
        except requests.exceptions.Timeout:
            raise RuntimeError("Ollama took too long to respond (timeout after 120s). Try a simpler prompt or check Ollama status.")
        except Exception as e:
            raise RuntimeError(f"Error generating layout with Ollama: {str(e)}")

    def _apply_gutters(self, layout: Dict[str, Any], gutter_pt: float) -> Dict[str, Any]:
        """
        Adjust element positions for even/odd page gutters.
        """
        pages = layout.get("pages", [])
        for page in pages:
            page_num = page.get("page_number", 1)
            is_odd = page_num % 2 == 1
            for element in page.get("elements", []):
                x = element.get("x", 0)
                if is_odd:
                    # Odd page: shift elements right by gutter
                    element["x"] = x + gutter_pt
                else:
                    # Even page: shift elements left by gutter (but ensure no negative)
                    element["x"] = max(0, x - gutter_pt)
    def _generate_fallback_layout(self, prompt: str, gutter_pt: float) -> Dict[str, Any]:
        """
        Generate a basic layout when AI fails completely.
        """
        # Parse the prompt to determine layout type
        prompt_lower = prompt.lower()
        if "habit tracker" in prompt_lower:
            return self._generate_basic_habit_tracker(gutter_pt)
        elif "weekly" in prompt_lower or "planner" in prompt_lower:
            return self._generate_basic_weekly_planner(gutter_pt)
        else:
            return self._generate_basic_lined_layout(gutter_pt)

    def _generate_basic_habit_tracker(self, gutter_pt: float) -> Dict[str, Any]:
        """Generate a simple habit tracker layout."""
        pages = []
        for page_num in range(1, 5):  # 4 pages
            elements = []
            # Add title
            elements.append({
                "type": "text",
                "x": gutter_pt + 20 if page_num % 2 == 1 else 20,  # Apply gutter
                "y": 50,
                "width": 200,
                "height": 20,
                "content": f"Habit Tracker - Page {page_num}",
                "style": {"fontFamily": "Arial", "fontSize": 14}
            })

            # Add some basic checkboxes (5 habits, 7 days)
            for habit in range(5):
                for day in range(7):
                    elements.append({
                        "type": "checkbox",
                        "x": gutter_pt + 30 + (day * 25) if page_num % 2 == 1 else 30 + (day * 25),
                        "y": 80 + (habit * 25),
                        "width": 15,
                        "height": 15,
                        "content": ""
                    })

            pages.append({
                "page_number": page_num,
                "elements": elements
            })

        return {"pages": pages}

    def _generate_basic_weekly_planner(self, gutter_pt: float) -> Dict[str, Any]:
        """Generate a simple weekly planner layout."""
        pages = []
        for page_num in range(1, 5):
            elements = []
            # Add title
            elements.append({
                "type": "text",
                "x": gutter_pt + 20 if page_num % 2 == 1 else 20,
                "y": 50,
                "width": 200,
                "height": 20,
                "content": f"Weekly Planner - Page {page_num}",
                "style": {"fontFamily": "Arial", "fontSize": 14}
            })

            # Add hourly slots
            for hour in range(8, 20):  # 8 AM to 8 PM
                elements.append({
                    "type": "text",
                    "x": gutter_pt + 20 if page_num % 2 == 1 else 20,
                    "y": 80 + ((hour - 8) * 20),
                    "width": 30,
                    "height": 15,
                    "content": f"{hour}:00",
                    "style": {"fontFamily": "Arial", "fontSize": 10}
                })
                elements.append({
                    "type": "line",
                    "x": gutter_pt + 55 if page_num % 2 == 1 else 55,
                    "y": 80 + ((hour - 8) * 20) + 10,
                    "width": 300,
                    "height": 1,
                    "content": ""
                })

            pages.append({
                "page_number": page_num,
                "elements": elements
            })

        return {"pages": pages}

    def _generate_basic_lined_layout(self, gutter_pt: float) -> Dict[str, Any]:
        """Generate a basic lined page layout."""
        pages = []
        for page_num in range(1, 5):
            elements = []
            # Add horizontal lines
            for line in range(20):
                elements.append({
                    "type": "line",
                    "x": gutter_pt + 20 if page_num % 2 == 1 else 20,
                    "y": 60 + (line * 18),
                    "width": 400,
                    "height": 0.5,
                    "content": ""
                })

            pages.append({
                "page_number": page_num,
                "elements": elements
            })

        return {"pages": pages}
LAYOUT_SCHEMA = {
    "type": "object",
    "properties": {
        "pages": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "page_number": {"type": "integer"},
                    "elements": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "type": {"type": "string", "enum": ["text", "line", "grid", "dot_grid", "checkbox", "image", "rectangle"]},
                                "x": {"type": "number"},
                                "y": {"type": "number"},
                                "width": {"type": "number"},
                                "height": {"type": "number"},
                                "content": {"type": "string"},
                                "style": {"type": "object"}
                            },
                            "required": ["type", "x", "y", "width", "height"]
                        }
                    }
                }
            }
        }
    },
    "required": ["pages"]
}

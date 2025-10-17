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
You are an expert layout designer for KDP book interiors. Generate a JSON layout based on the following prompt and schema.

IMPORTANT: You must output ONLY valid JSON that matches the schema exactly. Do NOT include explanations, examples, or any text outside the JSON.

Prompt: {prompt} {gutter_prompt}

Schema: {json.dumps(schema, indent=2)}

Output ONLY the JSON object with "pages" array containing page objects with "page_number" and "elements" array. Each element must have "type", "x", "y", "width", "height" and optionally "content" and "style".

Example format:
{{
  "pages": [
    {{
      "page_number": 1,
      "elements": [
        {{
          "type": "text",
          "x": 0,
          "y": 0,
          "width": 100,
          "height": 20,
          "content": "Sample text"
        }}
      ]
    }}
  ]
}}

Generate the layout JSON now:
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

            # Remove any leading/trailing non-JSON text
            layout_str = re.sub(r'^[^{]*', '', layout_str)  # Remove anything before {
            layout_str = re.sub(r'}[^}]*$', '}', layout_str)  # Remove anything after }

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
                            raise RuntimeError(f"Could not parse AI response as valid JSON. Response preview: {layout_str[:200]}...")
                else:
                    # Last resort: try to fix common issues like trailing commas
                    layout_str = re.sub(r',(\s*[}\]])', r'\1', layout_str)
                    layout = json.loads(layout_str)
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
        return layout

# Example schema for internal page layouts
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

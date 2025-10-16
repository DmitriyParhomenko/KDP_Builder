import json
import requests
from typing import Dict, List, Any

class AILayoutGenerator:
    def __init__(self, model: str = "llama3.2", base_url: str = "http://localhost:11434"):
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

Prompt: {prompt} {gutter_prompt}

Schema: {json.dumps(schema, indent=2)}

Output only valid JSON matching the schema. Ensure elements respect even/odd page gutters for binding.
"""

        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": full_prompt,
                    "stream": False
                }
            )
            response.raise_for_status()
            result = response.json()
            layout_str = result.get("response", "")
            layout_str = layout_str.strip()
            if layout_str.startswith("```json"):
                layout_str = layout_str[7:]
            if layout_str.endswith("```"):
                layout_str = layout_str[:-3]
            layout = json.loads(layout_str)
            # Post-process to adjust positions for gutters (if not handled by AI)
            layout = self._apply_gutters(layout, gutter_pt)
            return layout
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
                                "type": {"type": "string", "enum": ["text", "line", "grid", "dot_grid"]},
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

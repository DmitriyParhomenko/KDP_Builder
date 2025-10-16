import json
import requests
from typing import Dict, List, Any

class AILayoutGenerator:
    def __init__(self, model: str = "llama3.2", base_url: str = "http://localhost:11434"):
        self.model = model
        self.base_url = base_url

    def generate_layout(self, prompt: str, schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a layout JSON based on the prompt and schema using Ollama.

        Args:
            prompt: User prompt describing the layout (e.g., "Create a habit tracker with 30 days").
            schema: JSON schema for the layout structure.

        Returns:
            Generated layout as a dictionary.
        """
        # Craft the full prompt for Ollama
        schema_str = json.dumps(schema, indent=2)
        full_prompt = f"""
You are an expert layout designer for KDP book interiors. Generate a JSON layout based on the following prompt and schema.

Prompt: {prompt}

Schema: {schema_str}

Output only valid JSON matching the schema. No explanations or extra text.
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
            # Clean the response (remove any non-JSON text)
            layout_str = layout_str.strip()
            if layout_str.startswith("```json"):
                layout_str = layout_str[7:]
            if layout_str.endswith("```"):
                layout_str = layout_str[:-3]
            layout = json.loads(layout_str)
            return layout
        except Exception as e:
            raise RuntimeError(f"Error generating layout with Ollama: {str(e)}")

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

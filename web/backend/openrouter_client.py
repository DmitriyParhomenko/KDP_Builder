"""
OpenRouter AI Client for Claude Sonnet 4.5 and Grok Vision
"""
import os
import base64
import asyncio
from typing import Dict, Any, List, Optional
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

# OpenRouter configuration
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "anthropic/claude-3.5-sonnet")
GROK_MODEL = os.getenv("GROK_MODEL", "x-ai/grok-vision-beta")

# Initialize OpenRouter client
client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

_claude_lock = asyncio.Lock()
_grok_lock = asyncio.Lock()


async def analyze_with_claude(image_path: str, prompt: str, timeout_s: int = 60) -> Dict[str, Any]:
    """
    Analyze image with Claude Sonnet 4.5 and extract structured blocks.
    
    Args:
        image_path: Path to PNG/JPG image
        prompt: Analysis prompt
        timeout_s: Timeout in seconds
        
    Returns:
        Structured analysis result with blocks
    """
    # Read and encode image
    with open(image_path, "rb") as f:
        img_data = f.read()
    b64 = base64.b64encode(img_data).decode("utf-8")
    
    # Determine image type
    ext = image_path.lower().split(".")[-1]
    mime_type = f"image/{ext}" if ext in ["png", "jpg", "jpeg", "webp"] else "image/png"
    
    async with _claude_lock:
        try:
            response = await asyncio.wait_for(
                client.chat.completions.create(
                    model=CLAUDE_MODEL,
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:{mime_type};base64,{b64}"
                                    }
                                },
                                {
                                    "type": "text",
                                    "text": prompt
                                }
                            ]
                        }
                    ],
                    max_tokens=4000,
                    temperature=0.1,
                ),
                timeout=timeout_s
            )
            
            content = response.choices[0].message.content
            return {"success": True, "content": content, "model": CLAUDE_MODEL}
            
        except asyncio.TimeoutError:
            return {"success": False, "error": "Timeout", "model": CLAUDE_MODEL}
        except Exception as e:
            return {"success": False, "error": str(e), "model": CLAUDE_MODEL}


async def generate_pattern_with_grok(analysis: str, prompt: str, timeout_s: int = 45) -> Dict[str, Any]:
    """
    Generate pattern template from analysis using Grok Code Fast.
    
    Args:
        analysis: Claude's analysis result
        prompt: Generation prompt
        timeout_s: Timeout in seconds
        
    Returns:
        Generated pattern structure
    """
    async with _grok_lock:
        try:
            response = await asyncio.wait_for(
                client.chat.completions.create(
                    model=GROK_MODEL,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a KDP interior design pattern generator. Generate structured JSON patterns for planner layouts."
                        },
                        {
                            "role": "user",
                            "content": f"{prompt}\n\nAnalysis:\n{analysis}"
                        }
                    ],
                    max_tokens=1500,
                    temperature=0.3,
                ),
                timeout=timeout_s
            )
            
            content = response.choices[0].message.content
            return {"success": True, "content": content, "model": GROK_MODEL}
            
        except asyncio.TimeoutError:
            return {"success": False, "error": "Timeout", "model": GROK_MODEL}
        except Exception as e:
            return {"success": False, "error": str(e), "model": GROK_MODEL}


# Specialized prompts for planner analysis
CLAUDE_EXTRACT_PROMPT = """Analyze this planner/journal page and extract ALL visual elements.

For each element, identify:
1. **Type**: text_field, checkbox, line, grid, calendar, habit_tracker, title, notes_area, rating_stars, category_box, date_field, decorative_element
2. **Position**: Approximate x, y coordinates (0-100% of page width/height)
3. **Size**: Width and height (0-100% of page dimensions)
4. **Content**: What text or purpose (e.g., "Title:", "Author:", checkbox for "FICTION")
5. **Style**: Font size (small/medium/large), line thickness, spacing

Return a JSON array of blocks:
```json
[
  {
    "type": "text_field",
    "label": "Title",
    "x": 55,
    "y": 14,
    "width": 40,
    "height": 3,
    "style": "medium"
  },
  ...
]
```

Be thorough - capture every line, checkbox, text field, and decorative element."""

GROK_PATTERN_PROMPT = """Based on the extracted blocks, generate a reusable KDP pattern template.

Create a JSON structure with:
1. **Pattern metadata**: name, category, page_size
2. **Block library**: Reusable components (header, checkbox_list, rating_stars, etc.)
3. **Layout rules**: Positioning, spacing, alignment
4. **Variants**: Different configurations (with/without certain sections)

Return valid JSON that can be used to recreate similar layouts."""

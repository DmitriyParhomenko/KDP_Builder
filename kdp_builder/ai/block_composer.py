"""
AI Block Composer

Uses Ollama to intelligently compose page layouts from a library of blocks.
The AI learns which blocks work well together and can create novel combinations.
"""

import json
import requests
import click
from typing import Dict, List, Any, Optional

from kdp_builder.blocks.block_library import BlockLibrary
from kdp_builder.blocks.block_schema import BlockCategory


class AIBlockComposer:
    """Composes page layouts using AI and a block library"""
    
    def __init__(
        self,
        model: str = "qwen2.5:7b",
        base_url: str = "http://localhost:11434",
        library_path: str = "kdp_builder/blocks/library"
    ):
        """
        Initialize AI Block Composer.
        
        Args:
            model: Ollama model to use (qwen2.5:7b recommended for best results)
            base_url: Ollama API base URL
            library_path: Path to block library
        """
        self.model = model
        self.base_url = base_url
        self.library = BlockLibrary(library_path)
        
    def _create_daily_planner_template(
        self,
        page_width: float,
        page_height: float,
        gutter_pt: float,
        page_num: int
    ) -> Dict[str, Any]:
        """
        Create a pre-designed daily planner template with correct positioning.
        
        This uses a template-based approach instead of AI to ensure proper layout.
        """
        is_odd = page_num % 2 == 1
        left_margin = gutter_pt + 36 if is_odd else 36
        right_margin = 36 if is_odd else gutter_pt + 36
        top_margin = 36
        bottom_margin = 36
        
        # Calculate available content area
        content_width = page_width - left_margin - right_margin
        content_height = page_height - top_margin - bottom_margin
        
        # Get blocks from library
        header_blocks = self.library.search_blocks(tags=["daily", "header", "professional"])
        time_blocks = self.library.search_blocks(tags=["schedule", "hourly", "professional"])
        notes_blocks = self.library.search_blocks(tags=["notes", "professional"])
        priorities_blocks = self.library.search_blocks(tags=["priorities", "daily"])
        
        block_placements = []
        current_y = page_height - top_margin
        
        # 1. Header at top (50pt)
        if header_blocks:
            header = header_blocks[0]
            block_placements.append({
                "block_id": header["id"],
                "x": left_margin,
                "y": current_y - 50,
                "width": content_width,
                "height": 50
            })
            current_y -= 70  # Header + gap
        
        # 2. Time blocks in middle (takes most space)
        if time_blocks:
            time_block = time_blocks[0]
            time_height = 425  # Fixed height for 6 AM - 10 PM
            block_placements.append({
                "block_id": time_block["id"],
                "x": left_margin,
                "y": current_y - time_height,
                "width": content_width,
                "height": time_height
            })
            current_y -= time_height + 20
        
        # 3. Notes section at bottom (120pt)
        if notes_blocks and current_y - 120 > bottom_margin:
            notes = notes_blocks[0]
            block_placements.append({
                "block_id": notes["id"],
                "x": left_margin,
                "y": current_y - 120,
                "width": content_width,
                "height": 120
            })
        
        return {
            "page_number": page_num,
            "blocks": block_placements
        }
    
    def _create_habit_tracker_template(
        self,
        page_width: float,
        page_height: float,
        gutter_pt: float,
        page_num: int
    ) -> Dict[str, Any]:
        """
        Create Etsy-style habit tracker template.
        Based on analyzed patterns: large header + checkbox grid.
        """
        is_odd = page_num % 2 == 1
        left_margin = gutter_pt + 36 if is_odd else 36
        top_margin = 36
        
        content_width = page_width - left_margin - 36
        
        # Get Etsy-style blocks
        header_blocks = self.library.search_blocks(tags=["etsy", "header", "large"])
        checkbox_blocks = self.library.search_blocks(tags=["etsy", "checkbox", "grid"])
        lined_blocks = self.library.search_blocks(tags=["etsy", "lines"])
        
        block_placements = []
        current_y = page_height - top_margin
        
        # 1. Large Etsy header (80pt height)
        if header_blocks:
            block_placements.append({
                "block_id": header_blocks[0]["id"],
                "x": left_margin,
                "y": current_y - 80,
                "width": content_width,
                "height": 80
            })
            current_y -= 100
        
        # 2. Checkbox grid (180pt height)
        if checkbox_blocks:
            block_placements.append({
                "block_id": checkbox_blocks[0]["id"],
                "x": left_margin,
                "y": current_y - 180,
                "width": content_width,
                "height": 180
            })
            current_y -= 200
        
        # 3. Lined section for notes
        if lined_blocks and current_y > 100:
            remaining_height = current_y - 50
            block_placements.append({
                "block_id": lined_blocks[0]["id"],
                "x": left_margin,
                "y": remaining_height,
                "width": content_width,
                "height": remaining_height
            })
        
        return {
            "page_number": page_num,
            "blocks": block_placements
        }
    
    def _create_meal_planner_template(
        self,
        page_width: float,
        page_height: float,
        gutter_pt: float,
        page_num: int
    ) -> Dict[str, Any]:
        """
        Create Etsy-style meal planner template.
        Based on analyzed patterns: large header + meal grid.
        """
        is_odd = page_num % 2 == 1
        left_margin = gutter_pt + 36 if is_odd else 36
        top_margin = 36
        
        content_width = page_width - left_margin - 36
        
        # Get Etsy-style blocks
        header_blocks = self.library.search_blocks(tags=["etsy", "header", "title"])
        meal_blocks = self.library.search_blocks(tags=["etsy", "meal", "planner"])
        lined_blocks = self.library.search_blocks(tags=["etsy", "lines"])
        
        block_placements = []
        current_y = page_height - top_margin
        
        # 1. Title with subtitle (100pt height)
        if header_blocks:
            block_placements.append({
                "block_id": header_blocks[0]["id"],
                "x": left_margin,
                "y": current_y - 100,
                "width": content_width,
                "height": 100
            })
            current_y -= 120
        
        # 2. Meal planner grid (200pt height)
        if meal_blocks:
            block_placements.append({
                "block_id": meal_blocks[0]["id"],
                "x": left_margin,
                "y": current_y - 200,
                "width": content_width,
                "height": 200
            })
            current_y -= 220
        
        # 3. Lined section for notes/shopping list
        if lined_blocks and current_y > 100:
            remaining_height = current_y - 50
            block_placements.append({
                "block_id": lined_blocks[0]["id"],
                "x": left_margin,
                "y": remaining_height,
                "width": content_width,
                "height": remaining_height
            })
        
        return {
            "page_number": page_num,
            "blocks": block_placements
        }
        
    def compose_planner(
        self,
        planner_type: str,
        num_pages: int = 4,
        page_width: float = 432.0,  # 6 inches at 72 DPI
        page_height: float = 648.0,  # 9 inches at 72 DPI
        gutter_pt: float = 36.0
    ) -> Dict[str, Any]:
        """
        Compose a complete planner using AI and blocks.
        
        Args:
            planner_type: Type of planner (e.g., "daily", "weekly", "monthly", "habit_tracker")
            num_pages: Number of pages to generate
            page_width: Page width in points
            page_height: Page height in points
            gutter_pt: Gutter for binding
        
        Returns:
            Complete planner layout with pages and block placements
        """
        click.echo(f"📐 Composing {planner_type} planner with {num_pages} pages...", err=True)
        
        # Use template-based approach for specific planner types (guaranteed correct layout)
        planner_lower = planner_type.lower()
        
        if planner_lower == "daily":
            click.echo("✨ Using Etsy-style daily planner template", err=True)
            template_func = self._create_daily_planner_template
        elif planner_lower == "habit_tracker":
            click.echo("✨ Using Etsy-style habit tracker template", err=True)
            template_func = self._create_habit_tracker_template
        elif planner_lower in ["meal_planner", "meal"]:
            click.echo("✨ Using Etsy-style meal planner template", err=True)
            template_func = self._create_meal_planner_template
        else:
            template_func = None
        
        if template_func:
            pages = []
            for page_num in range(1, num_pages + 1):
                page = template_func(
                    page_width=page_width,
                    page_height=page_height,
                    gutter_pt=gutter_pt,
                    page_num=page_num
                )
                pages.append(page)
            
            return {
                "planner_type": planner_type,
                "pages": pages
            }
        
        # For other planner types, use AI composition
        relevant_blocks = self._get_relevant_blocks(planner_type)
        
        if not relevant_blocks:
            click.echo("⚠️ No relevant blocks found in library", err=True)
            return {"pages": []}
        
        click.echo(f"📚 Found {len(relevant_blocks)} relevant blocks", err=True)
        
        # Generate composition using AI
        composition = self._generate_composition_with_ai(
            planner_type=planner_type,
            num_pages=num_pages,
            blocks=relevant_blocks,
            page_width=page_width,
            page_height=page_height,
            gutter_pt=gutter_pt
        )
        
        return composition
    
    def _get_relevant_blocks(self, planner_type: str) -> List[Dict[str, Any]]:
        """
        Get blocks relevant to the planner type.
        
        Args:
            planner_type: Type of planner
        
        Returns:
            List of relevant blocks
        """
        planner_type_lower = planner_type.lower()
        
        # Map planner types to relevant categories and tags
        relevance_map = {
            "daily": {
                "categories": [BlockCategory.HEADER, BlockCategory.TIME_BLOCK, BlockCategory.CHECKLIST, 
                              BlockCategory.NOTE_SECTION, BlockCategory.HABIT_TRACKER],
                "tags": ["daily", "tasks", "schedule", "notes"]
            },
            "weekly": {
                "categories": [BlockCategory.HEADER, BlockCategory.WEEKLY_PLANNER, BlockCategory.GOAL_TRACKER,
                              BlockCategory.HABIT_TRACKER],
                "tags": ["weekly", "overview", "goals"]
            },
            "monthly": {
                "categories": [BlockCategory.HEADER, BlockCategory.MONTHLY_PLANNER, BlockCategory.CALENDAR,
                              BlockCategory.GOAL_TRACKER],
                "tags": ["monthly", "calendar", "goals"]
            },
            "habit_tracker": {
                "categories": [BlockCategory.HEADER, BlockCategory.HABIT_TRACKER, BlockCategory.GOAL_TRACKER],
                "tags": ["habit", "tracker", "daily", "weekly"]
            },
            "goal_tracker": {
                "categories": [BlockCategory.HEADER, BlockCategory.GOAL_TRACKER, BlockCategory.CHECKLIST],
                "tags": ["goals", "progress", "tracker"]
            }
        }
        
        # Get relevance criteria
        criteria = relevance_map.get(planner_type_lower, {
            "categories": list(BlockCategory),
            "tags": []
        })
        
        # Search for relevant blocks
        relevant_blocks = []
        
        # Get blocks by category
        for category in criteria.get("categories", []):
            blocks = self.library.search_blocks(category=category)
            relevant_blocks.extend(blocks)
        
        # Get blocks by tags
        if criteria.get("tags"):
            tag_blocks = self.library.search_blocks(tags=criteria["tags"])
            relevant_blocks.extend(tag_blocks)
        
        # Remove duplicates (by ID)
        seen_ids = set()
        unique_blocks = []
        for block in relevant_blocks:
            if block["id"] not in seen_ids:
                seen_ids.add(block["id"])
                unique_blocks.append(block)
        
        # Prioritize high-quality blocks
        unique_blocks.sort(key=lambda b: b.get("success_rate", 0), reverse=True)
        
        return unique_blocks
    
    def _generate_composition_with_ai(
        self,
        planner_type: str,
        num_pages: int,
        blocks: List[Dict[str, Any]],
        page_width: float,
        page_height: float,
        gutter_pt: float
    ) -> Dict[str, Any]:
        """
        Use AI to compose pages from blocks.
        
        Args:
            planner_type: Type of planner
            num_pages: Number of pages
            blocks: Available blocks
            page_width: Page width
            page_height: Page height
            gutter_pt: Gutter size
        
        Returns:
            Page composition
        """
        # Create a simplified block catalog for AI
        block_catalog = []
        for block in blocks[:20]:  # Limit to top 20 blocks to avoid token limits
            block_catalog.append({
                "id": block["id"],
                "name": block["name"],
                "category": block["category"],
                "description": block["description"],
                "dimensions": block["dimensions"],
                "tags": block.get("tags", [])
            })
        
        # Build AI prompt
        prompt = self._build_composition_prompt(
            planner_type=planner_type,
            num_pages=num_pages,
            block_catalog=block_catalog,
            page_width=page_width,
            page_height=page_height,
            gutter_pt=gutter_pt
        )
        
        try:
            # Call Ollama API
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": True,
                    "options": {
                        "temperature": 0.7,  # Some creativity
                        "top_p": 0.9
                    }
                },
                timeout=180
            )
            response.raise_for_status()
            
            # Collect response
            composition_str = ""
            click.echo("🤖 AI is composing layout...", err=True)
            
            for line in response.iter_lines():
                if line:
                    try:
                        data = json.loads(line.decode('utf-8'))
                        if 'response' in data:
                            chunk = data['response']
                            composition_str += chunk
                            click.echo(chunk, nl=False, err=True)
                        if data.get('done', False):
                            break
                    except json.JSONDecodeError:
                        continue
            
            click.echo("\n✅ Composition generated!", err=True)
            
            # Parse AI response
            composition = self._parse_composition(composition_str, blocks)
            
            # Update block statistics
            for page in composition.get("pages", []):
                for block_placement in page.get("blocks", []):
                    block_id = block_placement.get("block_id")
                    if block_id:
                        self.library.update_block_stats(block_id, success=True)
            
            return composition
            
        except Exception as e:
            click.echo(f"❌ AI composition failed: {e}", err=True)
            # Fallback to simple composition
            return self._fallback_composition(planner_type, num_pages, blocks, page_width, page_height, gutter_pt)
    
    def _build_composition_prompt(
        self,
        planner_type: str,
        num_pages: int,
        block_catalog: List[Dict[str, Any]],
        page_width: float,
        page_height: float,
        gutter_pt: float
    ) -> str:
        """Build the AI prompt for composition"""
        
        prompt = f"""You are an expert planner designer. Create a {planner_type} planner layout using the available blocks.

REQUIREMENTS:
- Create {num_pages} pages
- Page dimensions: {page_width}pt wide × {page_height}pt tall
- Gutter: {gutter_pt}pt (odd pages: left side, even pages: right side)
- Use blocks from the catalog below
- Position blocks to create a functional, beautiful layout
- Avoid overlapping blocks
- Leave appropriate margins and spacing

AVAILABLE BLOCKS:
{json.dumps(block_catalog, indent=2)}

OUTPUT FORMAT (JSON only, no explanations):
{{
  "planner_type": "{planner_type}",
  "pages": [
    {{
      "page_number": 1,
      "blocks": [
        {{
          "block_id": "block-id-here",
          "x": 50,
          "y": 600,
          "width": 400,
          "height": 60
        }}
      ]
    }}
  ]
}}

DESIGN GUIDELINES:
- Start each page with a header block at the top
- Place time-sensitive blocks (schedules, calendars) in prominent positions
- Add note sections or trackers in remaining space
- End pages with footer blocks if appropriate
- For odd pages: add {gutter_pt}pt to left margin
- For even pages: add {gutter_pt}pt to right margin

Generate the layout JSON now:"""
        
        return prompt
    
    def _parse_composition(self, composition_str: str, blocks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Parse AI-generated composition"""
        import re
        
        # Clean the response
        composition_str = composition_str.strip()
        
        # Remove markdown code blocks
        if composition_str.startswith("```json"):
            composition_str = composition_str[7:]
        if composition_str.startswith("```"):
            composition_str = composition_str[3:]
        if composition_str.endswith("```"):
            composition_str = composition_str[:-3]
        
        # Extract JSON
        composition_str = re.sub(r'^[^{]*', '', composition_str)
        composition_str = re.sub(r'}[^}]*$', '}', composition_str)
        
        try:
            composition = json.loads(composition_str)
            
            # Validate block IDs exist
            valid_block_ids = {b["id"] for b in blocks}
            for page in composition.get("pages", []):
                page["blocks"] = [
                    bp for bp in page.get("blocks", [])
                    if bp.get("block_id") in valid_block_ids
                ]
            
            return composition
            
        except json.JSONDecodeError as e:
            click.echo(f"⚠️ Failed to parse AI composition: {e}", err=True)
            return {"pages": []}
    
    def _fallback_composition(
        self,
        planner_type: str,
        num_pages: int,
        blocks: List[Dict[str, Any]],
        page_width: float,
        page_height: float,
        gutter_pt: float
    ) -> Dict[str, Any]:
        """
        Fallback composition when AI fails.
        Creates a simple, functional layout.
        """
        click.echo("🔄 Using fallback composition...", err=True)
        
        pages = []
        
        # Get key blocks
        header_blocks = [b for b in blocks if b["category"] == "header"]
        content_blocks = [b for b in blocks if b["category"] not in ["header", "footer"]]
        footer_blocks = [b for b in blocks if b["category"] == "footer"]
        
        for page_num in range(1, num_pages + 1):
            is_odd = page_num % 2 == 1
            left_margin = gutter_pt + 36 if is_odd else 36
            
            block_placements = []
            current_y = page_height - 60  # Start from top
            
            # Add header
            if header_blocks:
                header = header_blocks[0]
                block_placements.append({
                    "block_id": header["id"],
                    "x": left_margin,
                    "y": current_y,
                    "width": page_width - left_margin - 36,
                    "height": header["dimensions"]["height"]
                })
                current_y -= header["dimensions"]["height"] + 20
            
            # Add content blocks
            for content_block in content_blocks[:3]:  # Max 3 content blocks per page
                if current_y < 100:  # Leave space at bottom
                    break
                
                block_placements.append({
                    "block_id": content_block["id"],
                    "x": left_margin,
                    "y": current_y,
                    "width": page_width - left_margin - 36,
                    "height": min(content_block["dimensions"]["height"], current_y - 80)
                })
                current_y -= content_block["dimensions"]["height"] + 20
            
            # Add footer
            if footer_blocks:
                footer = footer_blocks[0]
                block_placements.append({
                    "block_id": footer["id"],
                    "x": left_margin,
                    "y": 40,
                    "width": page_width - left_margin - 36,
                    "height": footer["dimensions"]["height"]
                })
            
            pages.append({
                "page_number": page_num,
                "blocks": block_placements
            })
        
        return {
            "planner_type": planner_type,
            "pages": pages
        }
    
    def get_library_stats(self) -> Dict[str, Any]:
        """Get statistics about the block library"""
        return self.library.get_library_stats()

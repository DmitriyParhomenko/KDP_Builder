# AI Block-Based Planner Generation System

## Overview

The KDP Builder now includes an advanced AI-powered system that generates complete, print-ready planner interiors by intelligently composing layouts from a library of reusable "blocks". This system can understand, combine, and eventually create new page structures fully automatically.

## Key Features

### 🧱 Block Library System
- **20+ Starter Blocks**: Pre-built components including headers, calendars, habit trackers, time blocks, note sections, and more
- **Categorized & Tagged**: Blocks organized by category (header, footer, calendar, habit_tracker, etc.) with searchable tags
- **Complexity Levels**: Simple, moderate, and complex blocks for different use cases
- **Usage Tracking**: Automatic tracking of block usage and success rates for continuous improvement

### 🤖 AI Composition Engine
- **Intelligent Layout**: Uses Ollama (qwen2.5:7b or llama3.2) to compose professional layouts
- **Context-Aware**: Selects relevant blocks based on planner type
- **Smart Positioning**: Automatically positions blocks with proper spacing and margins
- **Fallback System**: Graceful degradation to rule-based composition if AI fails

### 📄 Block-to-PDF Rendering
- **Vector Output**: All blocks rendered as crisp, scalable vectors
- **KDP Compliant**: Automatic gutter handling for binding, bleed support
- **Flexible Sizing**: Blocks can be resized while maintaining proportions
- **Style Preservation**: Fonts, colors, line weights preserved from block definitions

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Block Library                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐             │
│  │ Headers  │  │ Trackers │  │ Calendars│  ... 20+    │
│  └──────────┘  └──────────┘  └──────────┘             │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│              AI Block Composer (Ollama)                  │
│  • Analyzes planner type (daily/weekly/monthly)         │
│  • Selects relevant blocks from library                 │
│  • Composes intelligent layouts                         │
│  • Handles gutters & spacing                            │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│                Block Renderer                            │
│  • Converts block compositions to PDF                   │
│  • Renders all element types (text, lines, shapes)      │
│  • Applies KDP compliance (bleed, trim)                 │
└─────────────────────────────────────────────────────────┘
                        ↓
                Print-Ready PDF
```

## Usage

### Quick Start

Generate a daily planner with AI:
```bash
python main.py --ai-planner daily --pages 4 --out outputs/daily_planner.pdf
```

### Planner Types

```bash
# Daily planner with time blocks and task lists
python main.py --ai-planner daily --pages 4

# Weekly overview with goals and habits
python main.py --ai-planner weekly --pages 4

# Monthly calendar grid
python main.py --ai-planner monthly --pages 4

# Habit tracker with checkboxes
python main.py --ai-planner habit_tracker --pages 4

# Goal tracker with progress monitoring
python main.py --ai-planner goal_tracker --pages 4
```

### Advanced Options

```bash
# Use specific AI model (qwen2.5:7b recommended for best results)
python main.py --ai-planner daily --ai-model qwen2.5:7b

# Custom page count and gutter
python main.py --ai-planner weekly --pages 8 --gutter-pt 54

# Different trim size
python main.py --ai-planner daily --trim 8.5x11 --pages 4
```

## Block Library

### Current Blocks (20+)

**Headers**
- Simple Page Header - Centered title with underline
- Date Header - Date display with day of week
- Weekly Overview Header - Week number and date range

**Time Management**
- Hourly Time Blocks - 6 AM to 10 PM schedule
- Daily Meal Planner - Breakfast, lunch, dinner sections
- Focus Block - Single daily intention

**Trackers**
- Weekly Habit Tracker - 7-day checkbox grid
- Water Intake Tracker - 8 glasses tracking
- Mood Tracker - 5-level mood selection
- Exercise Tracker - Type and duration
- Sleep Tracker - Hours and quality rating

**Planning**
- Monthly Calendar Grid - Full month view
- Goal Tracker - Progress checkboxes
- Priority Task List - Color-coded priorities

**Notes & Writing**
- Lined Notes Section - Multiple ruled lines
- Gratitude Section - 3 gratitude items
- Dot Grid Section - Bullet journal style

**Decorative**
- Inspirational Quote Box - Styled quote display
- Decorative Divider - Horizontal separator
- Simple Page Footer - Page numbers

### Block Structure

Each block is defined with:
```json
{
  "id": "unique-uuid",
  "name": "Block Name",
  "category": "header|footer|calendar|habit_tracker|...",
  "complexity": "simple|moderate|complex",
  "description": "What this block does",
  "tags": ["searchable", "tags"],
  "dimensions": {
    "width": 400,
    "height": 100,
    "flexible_width": true,
    "flexible_height": true
  },
  "elements": [
    {
      "type": "text|line|rectangle|circle|checkbox",
      "x": 0,
      "y": 0,
      "width": 100,
      "height": 20,
      "content": "Text content",
      "style": {
        "fontFamily": "Helvetica",
        "fontSize": 12,
        "color": "#000000"
      }
    }
  ],
  "parameters": {},
  "usage_count": 0,
  "success_rate": 1.0
}
```

## AI Models

### Recommended: qwen2.5:7b
- **Best Results**: Superior layout composition and block selection
- **Size**: ~4.7GB
- **Speed**: Moderate (10-30 seconds per planner)
- **Install**: `ollama pull qwen2.5:7b`

### Alternative: llama3.2
- **Good Results**: Decent layout composition
- **Size**: ~2GB
- **Speed**: Fast (5-15 seconds per planner)
- **Install**: `ollama pull llama3.2`

### Fallback: tinyllama
- **Basic Results**: Simple layouts only
- **Size**: ~637MB
- **Speed**: Very fast (2-5 seconds)
- **Install**: `ollama pull tinyllama`

## How It Works

### 1. Block Selection
The AI composer analyzes the planner type and searches the library for relevant blocks:
- **Daily planner** → headers, time blocks, task lists, notes
- **Weekly planner** → weekly headers, habit trackers, goal sections
- **Monthly planner** → calendar grids, goal trackers
- **Habit tracker** → habit grids, progress indicators
- **Goal tracker** → goal lists, progress tracking

### 2. AI Composition
Ollama receives:
- Planner type and requirements
- Available blocks with descriptions
- Page dimensions and constraints
- Gutter and spacing requirements

The AI generates a JSON composition specifying:
- Which blocks to use on each page
- Exact x, y positions
- Width and height (if resizing)

### 3. PDF Rendering
The BlockRenderer:
- Loads each block from the library
- Positions it according to AI composition
- Renders all elements (text, lines, shapes)
- Applies KDP compliance (gutters, bleed)
- Outputs print-ready PDF

### 4. Learning & Improvement
The system tracks:
- **Usage counts**: Which blocks are used most
- **Success rates**: Which blocks work well together
- **Composition patterns**: What layouts succeed

This data enables future improvements:
- Better block recommendations
- Smarter composition strategies
- Identification of missing block types

## Future Enhancements

### Phase 1: PDF Learning (Planned)
- Extract blocks from existing PDFs
- Analyze successful planner designs
- Automatically add new blocks to library
- Learn design patterns from real products

### Phase 2: Block Evolution (Planned)
- AI creates new blocks based on needs
- Combines existing blocks into new ones
- Optimizes block parameters
- Generates variations of successful blocks

### Phase 3: Style Learning (Planned)
- Learn color schemes from examples
- Extract typography patterns
- Understand spacing preferences
- Apply consistent design systems

### Phase 4: Full Autonomy (Vision)
- Generate complete planner series
- Create matching covers
- Optimize for different niches
- A/B test designs automatically

## Technical Details

### File Structure
```
kdp_builder/
├── blocks/
│   ├── __init__.py
│   ├── block_schema.py       # Block definitions & schemas
│   ├── block_library.py      # Library management
│   ├── starter_blocks.py     # 20+ initial blocks
│   └── library/              # JSON files for each block
│       ├── block-uuid-1.json
│       ├── block-uuid-2.json
│       └── ...
├── ai/
│   ├── block_composer.py     # AI composition engine
│   └── layout_generator.py   # Legacy prompt-based AI
└── renderer/
    ├── block_renderer.py     # Block-to-PDF rendering
    └── pdf_renderer.py       # Legacy template rendering
```

### Dependencies
- **reportlab**: PDF generation
- **requests**: Ollama API communication
- **pypdf**: PDF manipulation (bleed boxes)
- **click**: CLI interface

### Performance
- **Block library load**: <100ms
- **AI composition**: 5-30 seconds (model-dependent)
- **PDF rendering**: <1 second
- **Total time**: ~10-35 seconds per planner

## Examples

### Daily Planner Output
```
Page 1:
├── Date Header (top)
├── Hourly Time Blocks (6 AM - 10 PM)
├── Priority Task List
└── Notes Section

Page 2:
├── Date Header
├── Meal Planner
├── Water Tracker
├── Mood Tracker
└── Gratitude Section
```

### Weekly Planner Output
```
Page 1:
├── Weekly Overview Header
├── Weekly Habit Tracker (7 days × 5 habits)
├── Goal Tracker
└── Notes Section

Page 2-4:
├── Daily sections with time blocks
├── Task lists
└── Reflection areas
```

## Contributing

### Adding New Blocks

1. **Define the block** in `starter_blocks.py`:
```python
blocks.append(create_block(
    name="My Custom Block",
    category=BlockCategory.CUSTOM,
    complexity=BlockComplexity.MODERATE,
    description="What it does",
    tags=["custom", "useful"],
    dimensions={"width": 400, "height": 100, 
                "flexible_width": True, "flexible_height": False},
    elements=[
        {
            "type": "text",
            "x": 10,
            "y": 50,
            "width": 380,
            "height": 20,
            "content": "Custom content",
            "style": {"fontFamily": "Helvetica", "fontSize": 12}
        }
    ]
))
```

2. **Regenerate library**:
```bash
python -c "from kdp_builder.blocks.starter_blocks import populate_starter_library; populate_starter_library()"
```

3. **Test with AI**:
```bash
python main.py --ai-planner daily --pages 4
```

### Improving AI Prompts

Edit `kdp_builder/ai/block_composer.py` → `_build_composition_prompt()` to refine how the AI understands layout requirements.

### Adding New Planner Types

1. Add to CLI choices in `main.py`
2. Add relevance mapping in `block_composer.py` → `_get_relevant_blocks()`
3. Test with various block combinations

## Troubleshooting

### "404 Client Error: Not Found"
- Ollama model not installed
- Run: `ollama pull qwen2.5:7b` or `ollama pull llama3.2`

### "Using fallback composition"
- AI failed to generate valid layout
- Fallback creates simple but functional layout
- Check Ollama is running: `ollama list`

### Empty or malformed PDF
- Check block library exists: `ls kdp_builder/blocks/library/`
- Regenerate if needed: Run starter_blocks.py

### Blocks not rendering correctly
- Verify block JSON is valid
- Check element coordinates are within bounds
- Test individual blocks in isolation

## License

Same as main project (MIT for code, All Rights Reserved for models/data)

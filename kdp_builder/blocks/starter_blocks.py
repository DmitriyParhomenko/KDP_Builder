"""
Starter Block Library

Creates ~20 diverse, reusable layout blocks to bootstrap the AI system.
"""

from kdp_builder.blocks.block_schema import BlockCategory, BlockComplexity, create_block


def create_starter_blocks():
    """Create a diverse set of starter blocks"""
    blocks = []
    
    # 1. Simple Page Header
    blocks.append(create_block(
        name="Simple Page Header",
        category=BlockCategory.HEADER,
        complexity=BlockComplexity.SIMPLE,
        description="Centered text header with underline",
        tags=["header", "title", "simple"],
        dimensions={"width": 400, "height": 40, "flexible_width": True, "flexible_height": False},
        elements=[
            {
                "type": "text",
                "x": 200,
                "y": 25,
                "width": 200,
                "height": 20,
                "content": "{{title}}",
                "style": {"fontFamily": "Helvetica-Bold", "fontSize": 16, "color": "#000000"}
            },
            {
                "type": "line",
                "x": 50,
                "y": 5,
                "width": 300,
                "height": 1,
                "content": "",
                "style": {"lineWeight": 0.5, "color": "#000000"}
            }
        ],
        parameters={"title": "Page Title"}
    ))
    
    # 2. Date Header Block
    blocks.append(create_block(
        name="Date Header",
        category=BlockCategory.HEADER,
        complexity=BlockComplexity.MODERATE,
        description="Date display with day of week",
        tags=["date", "header", "daily"],
        dimensions={"width": 400, "height": 50, "flexible_width": True, "flexible_height": False},
        elements=[
            {
                "type": "text",
                "x": 20,
                "y": 30,
                "width": 150,
                "height": 20,
                "content": "{{day_of_week}}",
                "style": {"fontFamily": "Helvetica", "fontSize": 12, "color": "#666666"}
            },
            {
                "type": "text",
                "x": 20,
                "y": 10,
                "width": 200,
                "height": 25,
                "content": "{{date}}",
                "style": {"fontFamily": "Helvetica-Bold", "fontSize": 18, "color": "#000000"}
            }
        ],
        parameters={"day_of_week": "Monday", "date": "January 1, 2025"}
    ))
    
    # 3. Hourly Time Blocks
    blocks.append(create_block(
        name="Hourly Time Blocks",
        category=BlockCategory.TIME_BLOCK,
        complexity=BlockComplexity.COMPLEX,
        description="Hourly schedule with time labels",
        tags=["schedule", "hourly", "planner", "daily"],
        dimensions={"width": 400, "height": 400, "flexible_width": True, "flexible_height": True},
        elements=[
            {
                "type": "text",
                "x": 10,
                "y": 380 - (i * 30),
                "width": 50,
                "height": 15,
                "content": f"{hour:02d}:00",
                "style": {"fontFamily": "Helvetica", "fontSize": 10, "color": "#666666"}
            } for i, hour in enumerate(range(6, 22))  # 6 AM to 10 PM
        ] + [
            {
                "type": "line",
                "x": 70,
                "y": 375 - (i * 30),
                "width": 320,
                "height": 1,
                "content": "",
                "style": {"lineWeight": 0.3, "color": "#CCCCCC"}
            } for i in range(16)
        ],
        parameters={"start_hour": 6, "end_hour": 22}
    ))
    
    # 4. Weekly Habit Tracker
    blocks.append(create_block(
        name="Weekly Habit Tracker",
        category=BlockCategory.HABIT_TRACKER,
        complexity=BlockComplexity.COMPLEX,
        description="7-day habit tracker with checkboxes",
        tags=["habit", "weekly", "tracker", "checkbox"],
        dimensions={"width": 400, "height": 200, "flexible_width": True, "flexible_height": True},
        elements=[
            # Day headers
            *[{
                "type": "text",
                "x": 100 + (i * 40),
                "y": 180,
                "width": 35,
                "height": 15,
                "content": day,
                "style": {"fontFamily": "Helvetica", "fontSize": 9, "color": "#666666"}
            } for i, day in enumerate(["M", "T", "W", "T", "F", "S", "S"])],
            # Checkboxes for 5 habits
            *[{
                "type": "checkbox",
                "x": 105 + (day * 40),
                "y": 150 - (habit * 30),
                "width": 15,
                "height": 15,
                "content": "",
                "style": {}
            } for habit in range(5) for day in range(7)],
            # Habit labels
            *[{
                "type": "text",
                "x": 10,
                "y": 150 - (i * 30),
                "width": 80,
                "height": 15,
                "content": f"Habit {i+1}",
                "style": {"fontFamily": "Helvetica", "fontSize": 9, "color": "#000000"}
            } for i in range(5)]
        ],
        parameters={"num_habits": 5, "num_days": 7}
    ))
    
    # 5. Monthly Calendar Grid
    blocks.append(create_block(
        name="Monthly Calendar Grid",
        category=BlockCategory.MONTHLY_PLANNER,
        complexity=BlockComplexity.COMPLEX,
        description="Month view calendar grid",
        tags=["calendar", "monthly", "grid"],
        dimensions={"width": 400, "height": 300, "flexible_width": True, "flexible_height": True},
        elements=[
            # Grid lines
            *[{
                "type": "line",
                "x": 0,
                "y": i * 50,
                "width": 400,
                "height": 1,
                "content": "",
                "style": {"lineWeight": 0.5, "color": "#000000"}
            } for i in range(7)],
            *[{
                "type": "line",
                "x": i * 57,
                "y": 0,
                "width": 1,
                "height": 300,
                "content": "",
                "style": {"lineWeight": 0.5, "color": "#000000"}
            } for i in range(8)]
        ],
        parameters={"rows": 6, "cols": 7}
    ))
    
    # 6. Goal Tracker Block
    blocks.append(create_block(
        name="Goal Tracker",
        category=BlockCategory.GOAL_TRACKER,
        complexity=BlockComplexity.MODERATE,
        description="List of goals with progress checkboxes",
        tags=["goals", "tracker", "progress"],
        dimensions={"width": 400, "height": 250, "flexible_width": True, "flexible_height": True},
        elements=[
            {
                "type": "text",
                "x": 10,
                "y": 230,
                "width": 100,
                "height": 20,
                "content": "Goals",
                "style": {"fontFamily": "Helvetica-Bold", "fontSize": 14, "color": "#000000"}
            },
            *[{
                "type": "checkbox",
                "x": 10,
                "y": 200 - (i * 25),
                "width": 12,
                "height": 12,
                "content": "",
                "style": {}
            } for i in range(8)],
            *[{
                "type": "line",
                "x": 30,
                "y": 200 - (i * 25),
                "width": 360,
                "height": 1,
                "content": "",
                "style": {"lineWeight": 0.3, "color": "#CCCCCC"}
            } for i in range(8)]
        ],
        parameters={"num_goals": 8}
    ))
    
    # 7. Notes Section
    blocks.append(create_block(
        name="Lined Notes Section",
        category=BlockCategory.NOTE_SECTION,
        complexity=BlockComplexity.SIMPLE,
        description="Lined area for notes",
        tags=["notes", "lined", "writing"],
        dimensions={"width": 400, "height": 200, "flexible_width": True, "flexible_height": True},
        elements=[
            {
                "type": "text",
                "x": 10,
                "y": 185,
                "width": 80,
                "height": 15,
                "content": "Notes:",
                "style": {"fontFamily": "Helvetica", "fontSize": 11, "color": "#666666"}
            },
            *[{
                "type": "line",
                "x": 10,
                "y": 170 - (i * 18),
                "width": 380,
                "height": 1,
                "content": "",
                "style": {"lineWeight": 0.3, "color": "#CCCCCC"}
            } for i in range(10)]
        ],
        parameters={"num_lines": 10, "line_spacing": 18}
    ))
    
    # 8. Priority Task List
    blocks.append(create_block(
        name="Priority Task List",
        category=BlockCategory.CHECKLIST,
        complexity=BlockComplexity.MODERATE,
        description="Task list with priority indicators",
        tags=["tasks", "priority", "checklist", "daily"],
        dimensions={"width": 400, "height": 180, "flexible_width": True, "flexible_height": True},
        elements=[
            {
                "type": "text",
                "x": 10,
                "y": 165,
                "width": 120,
                "height": 18,
                "content": "Top Priorities",
                "style": {"fontFamily": "Helvetica-Bold", "fontSize": 13, "color": "#000000"}
            },
            *[{
                "type": "checkbox",
                "x": 10,
                "y": 140 - (i * 30),
                "width": 15,
                "height": 15,
                "content": "",
                "style": {}
            } for i in range(5)],
            *[{
                "type": "circle",
                "x": 30,
                "y": 140 - (i * 30),
                "width": 8,
                "height": 8,
                "content": "",
                "style": {"lineWeight": 1, "color": "#FF6B6B" if i == 0 else "#FFA500" if i == 1 else "#4ECDC4"}
            } for i in range(5)],
            *[{
                "type": "line",
                "x": 45,
                "y": 140 - (i * 30),
                "width": 345,
                "height": 1,
                "content": "",
                "style": {"lineWeight": 0.3, "color": "#CCCCCC"}
            } for i in range(5)]
        ],
        parameters={"num_tasks": 5}
    ))
    
    # 9. Water Intake Tracker
    blocks.append(create_block(
        name="Water Intake Tracker",
        category=BlockCategory.HABIT_TRACKER,
        complexity=BlockComplexity.SIMPLE,
        description="8 glasses water tracking",
        tags=["water", "health", "tracker", "daily"],
        dimensions={"width": 200, "height": 50, "flexible_width": False, "flexible_height": False},
        elements=[
            {
                "type": "text",
                "x": 10,
                "y": 35,
                "width": 80,
                "height": 15,
                "content": "Water:",
                "style": {"fontFamily": "Helvetica", "fontSize": 10, "color": "#666666"}
            },
            *[{
                "type": "circle",
                "x": 60 + (i * 18),
                "y": 30,
                "width": 12,
                "height": 12,
                "content": "",
                "style": {"lineWeight": 1, "color": "#4ECDC4"}
            } for i in range(8)]
        ],
        parameters={"num_glasses": 8}
    ))
    
    # 10. Gratitude Section
    blocks.append(create_block(
        name="Gratitude Section",
        category=BlockCategory.NOTE_SECTION,
        complexity=BlockComplexity.SIMPLE,
        description="3 things I'm grateful for",
        tags=["gratitude", "mindfulness", "daily"],
        dimensions={"width": 400, "height": 100, "flexible_width": True, "flexible_height": False},
        elements=[
            {
                "type": "text",
                "x": 10,
                "y": 85,
                "width": 200,
                "height": 15,
                "content": "I'm grateful for:",
                "style": {"fontFamily": "Helvetica", "fontSize": 11, "color": "#666666"}
            },
            *[{
                "type": "text",
                "x": 10,
                "y": 65 - (i * 25),
                "width": 15,
                "height": 15,
                "content": f"{i+1}.",
                "style": {"fontFamily": "Helvetica", "fontSize": 10, "color": "#999999"}
            } for i in range(3)],
            *[{
                "type": "line",
                "x": 30,
                "y": 65 - (i * 25),
                "width": 360,
                "height": 1,
                "content": "",
                "style": {"lineWeight": 0.3, "color": "#CCCCCC"}
            } for i in range(3)]
        ],
        parameters={"num_items": 3}
    ))
    
    # 11. Mood Tracker
    blocks.append(create_block(
        name="Mood Tracker",
        category=BlockCategory.HABIT_TRACKER,
        complexity=BlockComplexity.SIMPLE,
        description="Simple mood selection",
        tags=["mood", "emotions", "daily", "wellness"],
        dimensions={"width": 250, "height": 50, "flexible_width": False, "flexible_height": False},
        elements=[
            {
                "type": "text",
                "x": 10,
                "y": 35,
                "width": 80,
                "height": 15,
                "content": "Mood:",
                "style": {"fontFamily": "Helvetica", "fontSize": 10, "color": "#666666"}
            },
            *[{
                "type": "circle",
                "x": 60 + (i * 35),
                "y": 30,
                "width": 20,
                "height": 20,
                "content": "",
                "style": {"lineWeight": 1, "color": ["#FF6B6B", "#FFA500", "#FFD93D", "#6BCB77", "#4D96FF"][i]}
            } for i in range(5)]
        ],
        parameters={"num_moods": 5}
    ))
    
    # 12. Weekly Overview Header
    blocks.append(create_block(
        name="Weekly Overview Header",
        category=BlockCategory.HEADER,
        complexity=BlockComplexity.MODERATE,
        description="Week number and date range",
        tags=["weekly", "header", "overview"],
        dimensions={"width": 400, "height": 60, "flexible_width": True, "flexible_height": False},
        elements=[
            {
                "type": "text",
                "x": 10,
                "y": 40,
                "width": 100,
                "height": 20,
                "content": "Week {{week_num}}",
                "style": {"fontFamily": "Helvetica-Bold", "fontSize": 16, "color": "#000000"}
            },
            {
                "type": "text",
                "x": 10,
                "y": 20,
                "width": 200,
                "height": 15,
                "content": "{{date_range}}",
                "style": {"fontFamily": "Helvetica", "fontSize": 11, "color": "#666666"}
            },
            {
                "type": "line",
                "x": 0,
                "y": 5,
                "width": 400,
                "height": 2,
                "content": "",
                "style": {"lineWeight": 2, "color": "#000000"}
            }
        ],
        parameters={"week_num": 1, "date_range": "Jan 1 - Jan 7"}
    ))
    
    # 13. Meal Planner
    blocks.append(create_block(
        name="Daily Meal Planner",
        category=BlockCategory.CHECKLIST,
        complexity=BlockComplexity.MODERATE,
        description="Breakfast, lunch, dinner sections",
        tags=["meals", "food", "planner", "daily"],
        dimensions={"width": 400, "height": 150, "flexible_width": True, "flexible_height": False},
        elements=[
            {
                "type": "text",
                "x": 10,
                "y": 135,
                "width": 80,
                "height": 15,
                "content": "Meals",
                "style": {"fontFamily": "Helvetica-Bold", "fontSize": 12, "color": "#000000"}
            },
            *[{
                "type": "text",
                "x": 10,
                "y": 110 - (i * 40),
                "width": 80,
                "height": 15,
                "content": meal,
                "style": {"fontFamily": "Helvetica", "fontSize": 10, "color": "#666666"}
            } for i, meal in enumerate(["Breakfast:", "Lunch:", "Dinner:"])],
            *[{
                "type": "line",
                "x": 90,
                "y": 110 - (i * 40),
                "width": 300,
                "height": 1,
                "content": "",
                "style": {"lineWeight": 0.3, "color": "#CCCCCC"}
            } for i in range(3)]
        ],
        parameters={"meals": ["Breakfast", "Lunch", "Dinner"]}
    ))
    
    # 14. Focus Block
    blocks.append(create_block(
        name="Focus Block",
        category=BlockCategory.TEXT_BOX,
        complexity=BlockComplexity.SIMPLE,
        description="Single focus/intention for the day",
        tags=["focus", "intention", "daily", "mindfulness"],
        dimensions={"width": 400, "height": 70, "flexible_width": True, "flexible_height": False},
        elements=[
            {
                "type": "text",
                "x": 10,
                "y": 55,
                "width": 150,
                "height": 15,
                "content": "Today's Focus:",
                "style": {"fontFamily": "Helvetica", "fontSize": 11, "color": "#666666"}
            },
            {
                "type": "rectangle",
                "x": 10,
                "y": 10,
                "width": 380,
                "height": 40,
                "content": "",
                "style": {"lineWeight": 1, "color": "#4ECDC4", "fillColor": "#F0F8FF"}
            }
        ],
        parameters={}
    ))
    
    # 15. Exercise Tracker
    blocks.append(create_block(
        name="Exercise Tracker",
        category=BlockCategory.HABIT_TRACKER,
        complexity=BlockComplexity.MODERATE,
        description="Exercise type and duration",
        tags=["exercise", "fitness", "health", "daily"],
        dimensions={"width": 400, "height": 100, "flexible_width": True, "flexible_height": False},
        elements=[
            {
                "type": "text",
                "x": 10,
                "y": 85,
                "width": 100,
                "height": 15,
                "content": "Exercise",
                "style": {"fontFamily": "Helvetica-Bold", "fontSize": 12, "color": "#000000"}
            },
            {
                "type": "text",
                "x": 10,
                "y": 60,
                "width": 60,
                "height": 15,
                "content": "Type:",
                "style": {"fontFamily": "Helvetica", "fontSize": 10, "color": "#666666"}
            },
            {
                "type": "line",
                "x": 70,
                "y": 60,
                "width": 320,
                "height": 1,
                "content": "",
                "style": {"lineWeight": 0.3, "color": "#CCCCCC"}
            },
            {
                "type": "text",
                "x": 10,
                "y": 35,
                "width": 60,
                "height": 15,
                "content": "Duration:",
                "style": {"fontFamily": "Helvetica", "fontSize": 10, "color": "#666666"}
            },
            {
                "type": "line",
                "x": 70,
                "y": 35,
                "width": 100,
                "height": 1,
                "content": "",
                "style": {"lineWeight": 0.3, "color": "#CCCCCC"}
            }
        ],
        parameters={}
    ))
    
    # 16. Quote Box
    blocks.append(create_block(
        name="Inspirational Quote Box",
        category=BlockCategory.QUOTE_BOX,
        complexity=BlockComplexity.SIMPLE,
        description="Decorative quote or affirmation",
        tags=["quote", "inspiration", "decorative"],
        dimensions={"width": 400, "height": 80, "flexible_width": True, "flexible_height": False},
        elements=[
            {
                "type": "rectangle",
                "x": 10,
                "y": 10,
                "width": 380,
                "height": 60,
                "content": "",
                "style": {"lineWeight": 2, "color": "#FFD93D", "fillColor": "#FFFEF7"}
            },
            {
                "type": "text",
                "x": 200,
                "y": 45,
                "width": 360,
                "height": 20,
                "content": "{{quote}}",
                "style": {"fontFamily": "Helvetica-Oblique", "fontSize": 11, "color": "#666666"}
            }
        ],
        parameters={"quote": "Make today amazing"}
    ))
    
    # 17. Sleep Tracker
    blocks.append(create_block(
        name="Sleep Tracker",
        category=BlockCategory.HABIT_TRACKER,
        complexity=BlockComplexity.SIMPLE,
        description="Sleep hours and quality",
        tags=["sleep", "health", "wellness", "daily"],
        dimensions={"width": 300, "height": 60, "flexible_width": False, "flexible_height": False},
        elements=[
            {
                "type": "text",
                "x": 10,
                "y": 45,
                "width": 80,
                "height": 15,
                "content": "Sleep:",
                "style": {"fontFamily": "Helvetica", "fontSize": 10, "color": "#666666"}
            },
            {
                "type": "text",
                "x": 10,
                "y": 25,
                "width": 60,
                "height": 15,
                "content": "Hours:",
                "style": {"fontFamily": "Helvetica", "fontSize": 9, "color": "#999999"}
            },
            {
                "type": "line",
                "x": 70,
                "y": 25,
                "width": 50,
                "height": 1,
                "content": "",
                "style": {"lineWeight": 0.3, "color": "#CCCCCC"}
            },
            *[{
                "type": "circle",
                "x": 140 + (i * 25),
                "y": 20,
                "width": 15,
                "height": 15,
                "content": "",
                "style": {"lineWeight": 1, "color": "#4D96FF"}
            } for i in range(5)]
        ],
        parameters={"quality_levels": 5}
    ))
    
    # 18. Page Footer
    blocks.append(create_block(
        name="Simple Page Footer",
        category=BlockCategory.FOOTER,
        complexity=BlockComplexity.SIMPLE,
        description="Page number and optional text",
        tags=["footer", "page_number"],
        dimensions={"width": 400, "height": 30, "flexible_width": True, "flexible_height": False},
        elements=[
            {
                "type": "line",
                "x": 0,
                "y": 25,
                "width": 400,
                "height": 1,
                "content": "",
                "style": {"lineWeight": 0.5, "color": "#CCCCCC"}
            },
            {
                "type": "text",
                "x": 200,
                "y": 10,
                "width": 50,
                "height": 15,
                "content": "{{page_num}}",
                "style": {"fontFamily": "Helvetica", "fontSize": 9, "color": "#999999"}
            }
        ],
        parameters={"page_num": "1"}
    ))
    
    # 19. Divider Line
    blocks.append(create_block(
        name="Decorative Divider",
        category=BlockCategory.DIVIDER,
        complexity=BlockComplexity.SIMPLE,
        description="Horizontal divider line",
        tags=["divider", "separator", "decorative"],
        dimensions={"width": 400, "height": 20, "flexible_width": True, "flexible_height": False},
        elements=[
            {
                "type": "line",
                "x": 50,
                "y": 10,
                "width": 300,
                "height": 2,
                "content": "",
                "style": {"lineWeight": 2, "color": "#CCCCCC"}
            }
        ],
        parameters={}
    ))
    
    # 20. Dot Grid Section
    blocks.append(create_block(
        name="Dot Grid Section",
        category=BlockCategory.DOT_GRID,
        complexity=BlockComplexity.MODERATE,
        description="Dot grid for bullet journaling",
        tags=["dot_grid", "bullet_journal", "notes"],
        dimensions={"width": 400, "height": 200, "flexible_width": True, "flexible_height": True},
        elements=[
            {
                "type": "circle",
                "x": x,
                "y": y,
                "width": 1,
                "height": 1,
                "content": "",
                "style": {"fillColor": "#CCCCCC"}
            }
            for x in range(10, 400, 20)
            for y in range(10, 200, 20)
        ],
        parameters={"dot_spacing": 20}
    ))
    
    return blocks


def populate_starter_library(library_path: str = "kdp_builder/blocks/library"):
    """
    Create and save starter blocks to the library.
    
    Args:
        library_path: Path to save blocks
    """
    from kdp_builder.blocks.block_library import BlockLibrary
    
    library = BlockLibrary(library_path)
    blocks = create_starter_blocks()
    
    for block in blocks:
        library.add_block(block)
    
    print(f"✅ Created {len(blocks)} starter blocks")
    print(f"📊 Library stats: {library.get_library_stats()}")
    
    return library


if __name__ == "__main__":
    # Run this to populate the starter library
    populate_starter_library()

# Training Data for PDF Learning System

## 📁 Folder Structure

```
training_data/
├── etsy_examples/          ← PUT YOUR ETSY PDFs HERE
├── extracted_blocks/       ← Auto-generated blocks from PDFs
└── learned_patterns/       ← Analysis results (JSON)
```

## 🚀 Quick Start

### Step 1: Add Your Etsy PDFs

1. Buy professional planner PDFs from Etsy
2. Save them to `etsy_examples/` folder
3. Recommended: 10-20 PDFs for best results

### Step 2: Analyze PDFs

```bash
# Analyze all PDFs in the folder
.venv/bin/python -m kdp_builder.analysis.pdf_analyzer kdp_builder/training_data/etsy_examples daily

# Or analyze a single PDF
.venv/bin/python -m kdp_builder.analysis.pdf_analyzer kdp_builder/training_data/etsy_examples/my_planner.pdf daily
```

### Step 3: Review Results

Check `learned_patterns/` for:
- Individual PDF analysis (JSON files)
- Aggregate summary (`daily_AGGREGATE_patterns.json`)
- Recommended font sizes, line weights, spacing

### Step 4: Apply Learned Patterns

The system will automatically use learned patterns to improve your generated planners!

## 📊 What Gets Analyzed

- **Page dimensions** - Width, height
- **Typography** - Font sizes, font names
- **Line weights** - Thickness of lines
- **Spacing** - Vertical/horizontal spacing between elements
- **Layout structure** - Text positions, line positions, boxes
- **Design patterns** - Common patterns across multiple PDFs

## 🎯 Expected Output

After analyzing 10+ PDFs, you'll get recommendations like:

```json
{
  "recommended_font_sizes": [8, 9, 10, 12],
  "recommended_line_weights": [0.25, 0.5, 1.0],
  "recommended_spacing": [15, 18, 20, 25]
}
```

## 💡 Tips

1. **Quality over quantity** - 10 high-quality Etsy PDFs > 100 low-quality ones
2. **Same type** - Analyze daily planners separately from weekly planners
3. **Professional sources** - Buy from top-rated Etsy sellers
4. **Variety** - Get different styles to learn diverse patterns

## 🔧 Troubleshooting

**No PDFs found?**
- Make sure PDFs are in `etsy_examples/` folder
- Check file extensions are `.pdf`

**Analysis fails?**
- Install dependencies: `pip install pypdf pdfplumber`
- Check PDF is not password-protected
- Try with a different PDF

## 📈 Next Steps

After analysis:
1. Review learned patterns in `learned_patterns/`
2. Update your blocks with professional measurements
3. Generate new planners with improved quality
4. Compare output with Etsy examples
5. Iterate until matching professional quality!

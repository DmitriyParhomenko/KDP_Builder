"""
PDF Design Analyzer

Extracts design patterns from professional planner PDFs (Etsy examples).
Learns spacing, typography, colors, and layout structures.
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
from collections import Counter
import click

try:
    from pypdf import PdfReader
    import pdfplumber
except ImportError:
    click.echo("⚠️  Installing required packages: pypdf pdfplumber")
    os.system("pip install pypdf pdfplumber")
    from pypdf import PdfReader
    import pdfplumber


class PDFDesignAnalyzer:
    """Analyzes professional PDF planners to extract design patterns"""
    
    def __init__(self, output_dir: str = "kdp_builder/training_data/learned_patterns"):
        """
        Initialize PDF analyzer.
        
        Args:
            output_dir: Directory to save learned patterns
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.patterns = {
            "page_sizes": [],
            "margins": [],
            "text_elements": [],
            "line_elements": [],
            "rect_elements": [],
            "font_sizes": [],
            "line_weights": [],
            "spacing_vertical": [],
            "spacing_horizontal": [],
            "colors": []
        }
    
    def analyze_pdf(self, pdf_path: str, planner_type: str = "daily") -> Dict[str, Any]:
        """
        Analyze a professional PDF and extract all design patterns.
        
        Args:
            pdf_path: Path to PDF file
            planner_type: Type of planner (daily, weekly, monthly, etc.)
        
        Returns:
            Dictionary of extracted patterns
        """
        click.echo(f"\n📄 Analyzing: {Path(pdf_path).name}")
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                num_pages = len(pdf.pages)
                click.echo(f"   Pages: {num_pages}")
                
                for page_num, page in enumerate(pdf.pages, 1):
                    click.echo(f"   Analyzing page {page_num}/{num_pages}...", nl=False)
                    self._analyze_page(page, page_num)
                    click.echo(" ✓")
            
            # Summarize patterns
            summary = self._summarize_patterns(planner_type)
            
            # Save patterns
            self._save_patterns(summary, planner_type, Path(pdf_path).stem)
            
            click.echo(f"✅ Analysis complete!")
            return summary
            
        except Exception as e:
            click.echo(f"❌ Error analyzing PDF: {e}")
            return {}
    
    def _analyze_page(self, page, page_num: int):
        """Extract all elements from a single page"""
        
        # Page dimensions
        self.patterns["page_sizes"].append({
            "width": page.width,
            "height": page.height,
            "page_num": page_num
        })
        
        # Extract text elements
        words = page.extract_words()
        for word in words:
            self.patterns["text_elements"].append({
                "text": word.get("text", ""),
                "x": word.get("x0", 0),
                "y": word.get("top", 0),
                "width": word.get("x1", 0) - word.get("x0", 0),
                "height": word.get("bottom", 0) - word.get("top", 0),
                "font_size": word.get("height", 0),
                "font_name": word.get("fontname", ""),
                "page": page_num
            })
            
            # Track font sizes
            if word.get("height"):
                self.patterns["font_sizes"].append(word["height"])
        
        # Extract lines
        lines = page.lines
        for line in lines:
            self.patterns["line_elements"].append({
                "x0": line.get("x0", 0),
                "y0": line.get("top", 0),
                "x1": line.get("x1", 0),
                "y1": line.get("bottom", 0),
                "width": line.get("width", 0),
                "height": line.get("height", 0),
                "linewidth": line.get("linewidth", 0.5),
                "page": page_num
            })
            
            # Track line weights
            if line.get("linewidth"):
                self.patterns["line_weights"].append(line["linewidth"])
        
        # Extract rectangles/boxes
        rects = page.rects
        for rect in rects:
            self.patterns["rect_elements"].append({
                "x": rect.get("x0", 0),
                "y": rect.get("top", 0),
                "width": rect.get("width", 0),
                "height": rect.get("height", 0),
                "linewidth": rect.get("linewidth", 0.5),
                "page": page_num
            })
        
        # Calculate spacing between text elements (vertical)
        if len(words) > 1:
            sorted_words = sorted(words, key=lambda w: w.get("top", 0))
            for i in range(len(sorted_words) - 1):
                spacing = sorted_words[i+1].get("top", 0) - sorted_words[i].get("bottom", 0)
                if 0 < spacing < 100:  # Reasonable spacing range
                    self.patterns["spacing_vertical"].append(spacing)
    
    def _summarize_patterns(self, planner_type: str) -> Dict[str, Any]:
        """Summarize all learned patterns"""
        from statistics import mean, median, mode
        
        summary = {
            "planner_type": planner_type,
            "total_pages_analyzed": len(self.patterns["page_sizes"]),
            "page_dimensions": {
                "avg_width": mean([p["width"] for p in self.patterns["page_sizes"]]) if self.patterns["page_sizes"] else 0,
                "avg_height": mean([p["height"] for p in self.patterns["page_sizes"]]) if self.patterns["page_sizes"] else 0
            },
            "typography": {
                "font_sizes": self._get_common_values(self.patterns["font_sizes"], top_n=5),
                "avg_font_size": mean(self.patterns["font_sizes"]) if self.patterns["font_sizes"] else 10,
                "median_font_size": median(self.patterns["font_sizes"]) if self.patterns["font_sizes"] else 10
            },
            "lines": {
                "line_weights": self._get_common_values(self.patterns["line_weights"], top_n=3),
                "avg_line_weight": mean(self.patterns["line_weights"]) if self.patterns["line_weights"] else 0.5,
                "total_lines": len(self.patterns["line_elements"])
            },
            "spacing": {
                "vertical_spacing": self._get_common_values(self.patterns["spacing_vertical"], top_n=5),
                "avg_vertical_spacing": mean(self.patterns["spacing_vertical"]) if self.patterns["spacing_vertical"] else 18
            },
            "layout": {
                "total_text_elements": len(self.patterns["text_elements"]),
                "total_line_elements": len(self.patterns["line_elements"]),
                "total_rect_elements": len(self.patterns["rect_elements"])
            }
        }
        
        return summary
    
    def _get_common_values(self, values: List[float], top_n: int = 5) -> List[Dict[str, Any]]:
        """Get most common values with their frequencies"""
        if not values:
            return []
        
        # Round to 1 decimal place for grouping
        rounded = [round(v, 1) for v in values]
        counter = Counter(rounded)
        
        return [
            {"value": value, "count": count, "percentage": round(count/len(values)*100, 1)}
            for value, count in counter.most_common(top_n)
        ]
    
    def _save_patterns(self, summary: Dict[str, Any], planner_type: str, filename: str):
        """Save learned patterns to JSON file"""
        output_file = self.output_dir / f"{planner_type}_{filename}_patterns.json"
        
        with open(output_file, "w") as f:
            json.dump(summary, f, indent=2)
        
        click.echo(f"💾 Patterns saved to: {output_file}")
    
    def analyze_directory(self, directory: str, planner_type: str = "daily") -> List[Dict[str, Any]]:
        """
        Analyze all PDFs in a directory.
        
        Args:
            directory: Directory containing PDF files
            planner_type: Type of planner
        
        Returns:
            List of pattern summaries
        """
        pdf_dir = Path(directory)
        pdf_files = list(pdf_dir.glob("*.pdf"))
        
        if not pdf_files:
            click.echo(f"⚠️  No PDF files found in {directory}")
            return []
        
        click.echo(f"\n🔍 Found {len(pdf_files)} PDF files to analyze")
        
        summaries = []
        for pdf_file in pdf_files:
            summary = self.analyze_pdf(str(pdf_file), planner_type)
            summaries.append(summary)
        
        # Create aggregate summary
        self._create_aggregate_summary(summaries, planner_type)
        
        return summaries
    
    def _create_aggregate_summary(self, summaries: List[Dict[str, Any]], planner_type: str):
        """Create an aggregate summary from all analyzed PDFs"""
        if not summaries:
            return
        
        from statistics import mean
        
        aggregate = {
            "planner_type": planner_type,
            "total_pdfs_analyzed": len(summaries),
            "avg_page_width": mean([s["page_dimensions"]["avg_width"] for s in summaries if s]),
            "avg_page_height": mean([s["page_dimensions"]["avg_height"] for s in summaries if s]),
            "recommended_font_sizes": self._aggregate_font_sizes(summaries),
            "recommended_line_weights": self._aggregate_line_weights(summaries),
            "recommended_spacing": self._aggregate_spacing(summaries)
        }
        
        output_file = self.output_dir / f"{planner_type}_AGGREGATE_patterns.json"
        with open(output_file, "w") as f:
            json.dump(aggregate, f, indent=2)
        
        click.echo(f"\n📊 Aggregate patterns saved to: {output_file}")
        click.echo(f"\n✨ Recommendations for {planner_type} planners:")
        click.echo(f"   Font sizes: {aggregate['recommended_font_sizes']}")
        click.echo(f"   Line weights: {aggregate['recommended_line_weights']}")
        click.echo(f"   Vertical spacing: {aggregate['recommended_spacing']}")
    
    def _aggregate_font_sizes(self, summaries: List[Dict[str, Any]]) -> List[float]:
        """Aggregate font sizes from all summaries"""
        all_sizes = []
        for s in summaries:
            if s and "typography" in s:
                for size_info in s["typography"].get("font_sizes", []):
                    all_sizes.extend([size_info["value"]] * size_info["count"])
        
        if not all_sizes:
            return [9, 10, 12, 14]
        
        from collections import Counter
        return [size for size, _ in Counter(all_sizes).most_common(4)]
    
    def _aggregate_line_weights(self, summaries: List[Dict[str, Any]]) -> List[float]:
        """Aggregate line weights from all summaries"""
        all_weights = []
        for s in summaries:
            if s and "lines" in s:
                for weight_info in s["lines"].get("line_weights", []):
                    all_weights.extend([weight_info["value"]] * weight_info["count"])
        
        if not all_weights:
            return [0.25, 0.5, 1.0]
        
        from collections import Counter
        return [weight for weight, _ in Counter(all_weights).most_common(3)]
    
    def _aggregate_spacing(self, summaries: List[Dict[str, Any]]) -> List[float]:
        """Aggregate spacing from all summaries"""
        all_spacing = []
        for s in summaries:
            if s and "spacing" in s:
                for spacing_info in s["spacing"].get("vertical_spacing", []):
                    all_spacing.extend([spacing_info["value"]] * spacing_info["count"])
        
        if not all_spacing:
            return [15, 18, 20, 25]
        
        from collections import Counter
        return [spacing for spacing, _ in Counter(all_spacing).most_common(4)]


def main():
    """CLI for PDF analysis"""
    import sys
    
    if len(sys.argv) < 2:
        click.echo("Usage: python -m kdp_builder.analysis.pdf_analyzer <pdf_file_or_directory> [planner_type]")
        click.echo("Example: python -m kdp_builder.analysis.pdf_analyzer kdp_builder/training_data/etsy_examples daily")
        return
    
    path = sys.argv[1]
    planner_type = sys.argv[2] if len(sys.argv) > 2 else "daily"
    
    analyzer = PDFDesignAnalyzer()
    
    if os.path.isdir(path):
        analyzer.analyze_directory(path, planner_type)
    else:
        analyzer.analyze_pdf(path, planner_type)


if __name__ == "__main__":
    main()

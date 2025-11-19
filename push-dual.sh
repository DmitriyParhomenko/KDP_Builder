#!/bin/bash
# Dual Repository Push Script
# Push full version to private, light version to public

set -e

echo "🔄 Dual Repository Push"
echo "======================="
echo "Private: git@github.com:DmitriyParhomenko/KDP_Builder_FULL.git"
echo "Public:  git@github.com:DmitriyParhomenko/KDP_Builder.git"
echo ""

# Check if we have uncommitted changes
if [[ -n $(git status -s) ]]; then
    echo "⚠️  You have uncommitted changes. Commit them first!"
    git status -s
    exit 1
fi

# Push to private repo (full version)
echo "📦 Pushing FULL version to PRIVATE repo..."
git push private main
echo "✅ Private repo updated!"

echo ""
echo "🌍 Pushing LIGHT version to PUBLIC repo..."

# Create a temporary branch for public
git checkout -b public-temp

# Remove sensitive/proprietary files
echo "  Removing proprietary code..."
git rm -rf kdp_builder/ai/ 2>/dev/null || true
git rm -rf kdp_builder/blocks/ 2>/dev/null || true
git rm -rf kdp_builder/patterns/ 2>/dev/null || true
git rm -rf kdp_builder/renderer/ 2>/dev/null || true
git rm -rf chroma_db/ 2>/dev/null || true
git rm .env 2>/dev/null || true
git rm .env.local 2>/dev/null || true
git rm -rf PRIVATE_*.md 2>/dev/null || true

# Add public README
cat > README_PUBLIC.md << 'EOF'
# KDP Visual Editor

A Figma-like visual editor for creating KDP (Kindle Direct Publishing) planner interiors.

## Features

- 🎨 Drag & drop visual editor
- 📐 Real-time KDP preview with margins
- 🔧 Text, shapes, and line tools
- 📱 Responsive canvas with zoom/pan
- 💾 Design storage and management
- 📤 Export to print-ready PDF

## Tech Stack

**Frontend:**
- React + TypeScript
- Fabric.js for canvas
- TailwindCSS for styling
- Zustand for state management

**Backend:**
- FastAPI (Python)
- PostgreSQL
- Redis

## Getting Started

### Frontend
```bash
cd web/frontend
npm install
npm run dev
```

### Backend
```bash
cd web/backend
pip install -r requirements.txt
uvicorn main:app --reload
```

## License

MIT License

---

**Note:** This is the public/light version. Full version with AI features is private.
EOF

git add README_PUBLIC.md 2>/dev/null || true

# Commit public version
git commit -m "Public release - light version (frontend only)" --allow-empty

# Push to public
git push public public-temp:main --force

# Return to main branch
git checkout main
git branch -D public-temp

echo "✅ Public repo updated!"
echo ""
echo "🎉 Done! Both repositories are up to date."

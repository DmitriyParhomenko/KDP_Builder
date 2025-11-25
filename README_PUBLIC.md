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

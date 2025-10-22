# KDP Visual Editor - Frontend

React + TypeScript + Fabric.js visual editor for creating KDP planner interiors.

## Setup

```bash
# Install dependencies
npm install

# Start dev server
npm run dev

# Build for production
npm run build
```

## Tech Stack

- **React 18** - UI framework
- **TypeScript** - Type safety
- **Fabric.js** - Canvas manipulation
- **Zustand** - State management
- **TailwindCSS** - Styling
- **Vite** - Build tool
- **Axios** - API client

## Project Structure

```
src/
├── components/
│   ├── Canvas/       # Main canvas editor with Fabric.js
│   ├── Toolbar/      # Left sidebar tools
│   ├── Properties/   # Right sidebar properties panel
│   └── Layers/       # Layer management panel
├── store/
│   └── designStore.ts    # Zustand state management
├── api/
│   └── client.ts         # Backend API client
├── types/
│   └── design.ts         # TypeScript types
├── App.tsx               # Main app component
└── main.tsx              # Entry point
```

## Features

### Canvas Editor
- ✅ Drag & drop elements
- ✅ Text, rectangles, circles, lines
- ✅ Real-time editing
- ✅ KDP margin guides
- ✅ Grid overlay

### Toolbar
- ✅ Select tool
- ✅ Text tool
- ✅ Shape tools
- ✅ Line tool
- ✅ Pan tool

### Properties Panel
- ✅ Position & size controls
- ✅ Text properties (font, size, color)
- ✅ Shape properties (fill, stroke)
- ✅ Real-time updates

### Layers Panel
- ✅ Layer list
- ✅ Layer selection
- ✅ Delete layers
- ✅ Z-index ordering

### AI Features
- ✅ AI layout suggestions
- ✅ Learn from uploaded PDFs
- ✅ Context-aware recommendations

### Export
- ✅ Export to print-ready PDF
- ✅ KDP-compliant output
- ✅ Bleed support

## Development

### Running Locally

1. Start backend:
```bash
cd ../backend
python main.py
```

2. Start frontend:
```bash
npm run dev
```

3. Open browser:
```
http://localhost:5173
```

### API Endpoints

The frontend communicates with the backend API:

- `POST /api/designs/` - Create design
- `GET /api/designs/` - List designs
- `PUT /api/designs/{id}` - Update design
- `POST /api/ai/suggest` - AI suggestions
- `POST /api/ai/learn` - Learn from PDF
- `POST /api/export/pdf` - Export to PDF

## Usage

1. **Create Design** - Opens with blank canvas
2. **Add Elements** - Click toolbar tools to add text, shapes, lines
3. **Edit Properties** - Select element and edit in properties panel
4. **AI Suggest** - Click "AI Suggest" and describe what you want
5. **Learn from PDF** - Upload Etsy PDFs to teach AI
6. **Export** - Click "Export PDF" to download print-ready file

## Keyboard Shortcuts

- `Delete` - Delete selected element
- `Ctrl/Cmd + Z` - Undo
- `Ctrl/Cmd + Shift + Z` - Redo
- `Ctrl/Cmd + C` - Copy
- `Ctrl/Cmd + V` - Paste

## Contributing

This is part of the KDP Builder project. See main README for details.

## License

MIT

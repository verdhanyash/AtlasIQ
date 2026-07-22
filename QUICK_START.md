# AtlasIQ Quick Start - HTML/CSS/JS Frontend

## ✅ What's Available

AtlasIQ uses a pure **HTML/CSS/JavaScript frontend** that implements the Liquid Glass design system:

- ✅ **Zero latency** - No page reloads, instant interactions
- ✅ **Glassmorphic UI** - Liquid Glass aesthetic with proper animations
- ✅ **Three states**: Empty (home with examples), Loading (skeleton shimmer), Results (with citations)
- ✅ **Backend integration** - Connects to FastAPI backend

## 🚀 How to Start

### Option 1: Manual Start (Recommended First Time)

**Terminal 1 - Backend:**
```bash
cd C:\Users\yashv\Desktop\AtlasIQ
.venv\Scripts\activate
python -m uvicorn atlasiq.backend.main:app --host 0.0.0.0 --port 8000 --reload
```

**Terminal 2 - Frontend:**
```bash
cd C:\Users\yashv\Desktop\AtlasIQ
.venv\Scripts\activate
python atlasiq/frontend/serve.py
```

**Then open your browser to:**
```
http://localhost:8502
```

### Option 2: Automatic Start (Use Later)

Double-click `START_ATLASIQ.bat` in the project root - it will:
1. Start backend on port 8000
2. Start frontend on port 8502
3. Open your browser automatically

## 📁 Frontend Files

```
atlasiq/
├── frontend/
│   ├── static/
│   │   ├── index.html          ← Main frontend (complete app in one file)
│   │   └── logo.png            ← AtlasIQ logo
│   ├── serve.py                ← Simple HTTP server script
│   ├── README.md               ← Frontend documentation
│   └── __init__.py             ← Package init
├── docs/
│   └── NEW_FRONTEND_GUIDE.md   ← Complete documentation
└── START_ATLASIQ.bat           ← Startup script (optional)
```

## 🎨 Features

### Home State (Empty)
- Hero text: "How can I help you today?"
- Large glassmorphic search input
- 4 example cards:
  - **Finance**: "What is the projected revenue for Q4?"
  - **Analysis**: "Summarize the market analysis report."
  - **Legal**: "Review the termination clauses in current vendor contracts."
  - **Strategy**: "Identify cross-departmental synergy opportunities."
- Click any card to auto-search

### Loading State
- Animated glowing border on search input
- Bouncing dots: "Retrieving evidence..."
- Skeleton shimmer animation
- Smooth transitions

###Results State
- **Confidence badge**: High/Medium/Low with color coding
- **Answer**: Formatted text with inline citation superscripts [1], [2]
- **Citations grid**: 3-column layout with:
  - Index badge
  - Document title
  - Text excerpt
  - Relevance score
- **Response time**: Shows query execution time
- **New search button**: Click to start over

### Sidebar (240px Fixed)
- AtlasIQ branding
- Navigation: Document Library, Collections, Settings, User Profile
- Upload button at bottom
- Glassmorphic styling

### Top Bar
- System status (checks backend health)
- Notifications and help icons

## 🎯 Current Status

### ✅ Backend Running
- Port: 8000
- Status: **HEALTHY**
- All endpoints working
- Database: Connected
- Vector store: Connected

### ⚠️ Frontend Setup Needed
The frontend files are ready, but you need to start the server:

```bash
cd C:\Users\yashv\Desktop\AtlasIQ
.venv\Scripts\activate
python atlasiq/frontend/serve.py
```

Then open: http://localhost:8502

## 🔧 Troubleshooting

### Backend not responding
```bash
# Check if running
curl http://localhost:8000/health

# If not, start it
.venv\Scripts\activate
python -m uvicorn atlasiq.backend.main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend won't load
```bash
# Make sure you're in the project root
cd C:\Users\yashv\Desktop\AtlasIQ

# Activate virtual environment
.venv\Scripts\activate

# Start the frontend server
python atlasiq/frontend/serve.py

# Open browser to http://localhost:8502
```

### Port already in use
If port 8502 is busy, edit `atlasiq/frontend/serve.py` and change the PORT variable to a different port (e.g., 8503).

### Search not working
- Open browser console (F12) to see errors
- Verify backend is running: http://localhost:8000/health
- Check CORS headers (should be enabled)

## 📖 Documentation

- **NEW_FRONTEND_GUIDE.md** - Complete frontend documentation
- **atlasiq/frontend/README.md** - Frontend-specific readme
- **Stitch_design/** - Original design mockups

## 🔄 What's Included

- **Backend** - No changes, all APIs work as before
- **Database** - PostgreSQL unchanged
- **Vector store** - Qdrant unchanged
- **RAG pipeline** - All retrieval logic unchanged
- **Document ingestion** - Works the same

The frontend is pure HTML/CSS/JS served via Python HTTP server!

## 🎬 Next Steps

1. **Start the frontend** (see instructions above)
2. **Test the UI** - Try the example queries
3. **Upload documents** (feature coming soon in UI, use API for now)
4. **Enjoy the new design!** 🎉

## 📞 Need Help?

Check these in order:
1. Browser console (F12) for JavaScript errors
2. Backend logs for API errors
3. NEW_FRONTEND_GUIDE.md for detailed docs
4. This file for quick fixes

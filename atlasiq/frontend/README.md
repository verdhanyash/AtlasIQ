# AtlasIQ Frontend

## New Standalone Frontend (Recommended)

The new frontend is a single-file HTML/CSS/JavaScript application that matches the Stitch design exactly.

### Quick Start

**From project root:**
```bash
# Start backend
.venv\Scripts\activate
python -m uvicorn atlasiq.backend.main:app --host 0.0.0.0 --port 8000 --reload

# In another terminal, start frontend
python atlasiq/frontend/serve.py

# Open browser to http://localhost:8501
```

**OR use the startup script:**
```bash
# Double-click START_ATLASIQ.bat in project root
# Opens two terminals automatically and launches browser
```

### Files

- **`static/index.html`** - Complete frontend application
- **`serve.py`** - Simple HTTP server (port 8501)
- **`app.py`** - Old Streamlit app (deprecated)

### Features

✅ **Zero Latency** - No page reloads, instant interactions
✅ **Exact Stitch Design** - Matches design mockups perfectly
✅ **Three States**: Empty (home), Loading (shimmer), Results (citations)
✅ **Glassmorphic UI** - Liquid Glass aesthetic with animations
✅ **Backend Integration** - Connects to FastAPI `/query` endpoint

### Documentation

See `docs/NEW_FRONTEND_GUIDE.md` for complete documentation.

## Old Streamlit Frontend (Deprecated)

The Streamlit app (`app.py`) is deprecated due to:
- Full page reruns causing latency
- Cannot achieve exact Stitch design
- Limited customization options

Use the new standalone frontend instead.

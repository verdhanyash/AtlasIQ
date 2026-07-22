# AtlasIQ Frontend

The AtlasIQ frontend is a pure HTML/CSS/JavaScript application that implements the Liquid Glass design system.

## Quick Start

**From project root:**
```bash
# Start backend
.venv\Scripts\activate
python -m uvicorn atlasiq.backend.main:app --host 0.0.0.0 --port 8000 --reload

# In another terminal, start frontend
python atlasiq/frontend/serve.py

# Open browser to http://localhost:8502
```

### Files

- **`static/index.html`** - Complete frontend application
- **`static/logo.png`** - AtlasIQ logo
- **`serve.py`** - Simple HTTP server (port 8502)

### Features

✅ **Zero Latency** - No page reloads, instant interactions
✅ **Liquid Glass Design** - Glassmorphic aesthetic with animations
✅ **Three States**: Empty (home), Loading (shimmer), Results (citations)
✅ **Backend Integration** - Connects to FastAPI `/query` endpoint
✅ **File Upload** - Drag & drop or browse document upload
✅ **Collections View** - Browse indexed documents
✅ **LLM Settings** - Configure provider (Ollama, NVIDIA, OpenAI, Anthropic)

### Documentation

See `docs/NEW_FRONTEND_GUIDE.md` for complete documentation.


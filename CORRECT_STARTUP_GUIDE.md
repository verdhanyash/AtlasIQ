# AtlasIQ - Correct Startup Guide

## Important Note
AtlasIQ uses **HTML/CSS/JavaScript** for the frontend, NOT Streamlit!
The correct frontend is served by `atlasiq/frontend/serve.py`.

## Current Status ✅

Both services are now running:

### Backend (FastAPI)
- **URL**: http://localhost:8000
- **Health**: http://localhost:8000/health
- **Command**: `python -m uvicorn atlasiq.backend.main:app --host 0.0.0.0 --port 8000`

### Frontend (HTML/CSS/JS)
- **URL**: http://localhost:8502
- **Serves**: `atlasiq/frontend/static/index.html`
- **Command**: `python atlasiq/frontend/serve.py`

## Access the Application

Open your browser and go to: **http://localhost:8502**

You should see the Liquid Glass UI with:
- ✅ AtlasIQ logo in the sidebar
- ✅ Dark glassmorphism theme
- ✅ Document Library navigation
- ✅ Settings panel
- ✅ Clean search interface

## Logo Configuration

The logo is already configured in `index.html`:
```html
<img src="/logo.png" alt="AtlasIQ Logo" class="w-full h-full object-contain">
```

The logo file is located at:
```
atlasiq/frontend/static/logo.png
```

## Recent Fixes Applied

1. **Citation Format Fix** ✅
   - Updated `prompts/system_prompt.txt`
   - Updated `prompts/qa_prompt.txt`
   - Answers no longer contain inline `[Source: ...]` references
   - Citations display separately in the UI

2. **Logo Already Working** ✅
   - Logo path is correct in HTML
   - Static file serving is configured properly
   - No changes needed - just needed to start the correct frontend!

## To Stop Services

Press `Ctrl+C` in the terminals running the services, or run:
```powershell
Get-Process python | Stop-Process -Force
```

## Files Structure

```
atlasiq/
├── backend/
│   └── main.py              # FastAPI backend
└── frontend/
    ├── serve.py             # ✅ Correct frontend server (HTML/CSS/JS)
    ├── app.py               # ❌ Old Streamlit version (not used)
    └── static/
        ├── index.html       # ✅ Main UI file
        └── logo.png         # ✅ Logo image
```

## Next Time

To start the project, run these two commands in separate terminals:

**Terminal 1 - Backend:**
```cmd
.venv\Scripts\activate
python -m uvicorn atlasiq.backend.main:app --host 0.0.0.0 --port 8000
```

**Terminal 2 - Frontend:**
```cmd
.venv\Scripts\activate
python atlasiq/frontend/serve.py
```

Then open: http://localhost:8502

# 🚀 Quick Start - AtlasIQ

## Start the Project (One Command)

```bash
cd C:\Users\yashv\Desktop\AtlasIQ
.venv\Scripts\python.exe start_atlasiq.py
```

This single command:
- ✅ Checks port availability (8000, 8502)
- ✅ Starts backend (FastAPI on port 8000)
- ✅ Starts frontend (HTTP server on port 8502)
- ✅ Displays URLs and status
- ✅ Press **Ctrl+C** to stop both services

## Access AtlasIQ

Once started, open your browser:

- **Frontend UI:** http://localhost:8502
- **Backend API:** http://localhost:8000/docs
- **Health Check:** http://localhost:8000/health

## Why This Works Better

**Before:** Batch files + background processes = unreliable on Windows

**Now:** Single Python script that:
- Manages both processes properly
- Handles graceful shutdown
- Checks for port conflicts
- Shows clear status messages

## Troubleshooting

### Port Already in Use?

```bash
# Check what's using port 8000 or 8502
netstat -ano | findstr :8000
netstat -ano | findstr :8502

# Kill the process
taskkill /PID <PID> /F
```

### Virtual Environment Missing?

```bash
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
```

### Backend Won't Start?

Check:
- PostgreSQL is running (port 5433)
- Qdrant is running (port 6333)
- `.env` file exists with proper configuration

## Manual Start (Two Terminals)

If you prefer manual control:

**Terminal 1 - Backend:**
```bash
cd C:\Users\yashv\Desktop\AtlasIQ
.venv\Scripts\activate
.venv\Scripts\uvicorn.exe atlasiq.backend.main:app --host 0.0.0.0 --port 8000
```

**Terminal 2 - Frontend:**
```bash
cd C:\Users\yashv\Desktop\AtlasIQ
.venv\Scripts\activate
python -m atlasiq.frontend.serve
```

## What to Test

1. **Upload a document** (PDF, DOCX, TXT, MD)
2. **Query:** "What is [document] about?"
3. **Check citations** - Should be accurate and relevant
4. **Confidence score** - Should show 20-95% (not 1-3%)
5. **Retrieval details** - Scroll down to see technical breakdown

---

**For full documentation:** See `START_PROJECT.md`

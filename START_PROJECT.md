# 🚀 AtlasIQ - Quick Start Guide

**Date:** 2026-07-22  
**Recent Changes:** Confidence fix + Enhanced citations + Retrieval details

---

## 📋 Prerequisites Check

Before starting, ensure you have:
- ✅ PostgreSQL running (port 5433)
- ✅ Qdrant running (port 6333)
- ✅ Python virtual environment (`.venv`)
- ✅ Documents uploaded to database

---

## 🎯 Start AtlasIQ (One Command!)

### Method A: Using Python Startup Script (Recommended!) ⭐

**Single Command:**
```bash
cd C:\Users\yashv\Desktop\AtlasIQ
.venv\Scripts\python.exe start_atlasiq.py
```

This will:
- ✅ Check if ports 8000 and 8502 are available
- ✅ Start backend (FastAPI/Uvicorn) on port 8000
- ✅ Start frontend (HTTP server) on port 8502
- ✅ Display status and URLs
- ✅ Press Ctrl+C to stop both services cleanly

**Done!** Open http://localhost:8502 in your browser.

---

### Method B: Manual Commands (Two Terminals)

**Terminal 1: Backend**
```bash
cd C:\Users\yashv\Desktop\AtlasIQ
.venv\Scripts\activate
.venv\Scripts\uvicorn.exe atlasiq.backend.main:app --host 0.0.0.0 --port 8000
```

**Terminal 2: Frontend**
```bash
cd C:\Users\yashv\Desktop\AtlasIQ
.venv\Scripts\activate
python -m atlasiq.frontend.serve
```

---

## 🌐 Access AtlasIQ

Open your browser and navigate to:

**Frontend:** http://localhost:8502

**Backend API Docs:** http://localhost:8000/docs

**Health Check:** http://localhost:8000/health

---

## ✅ What to Test

### 1. Test Footer Cleanup
- ✅ Footer should only show "Backend Connected" status
- ❌ No "Privacy Policy" or "Terms of Enterprise" text

### 2. Test Confidence Display (Major Fix!)
**Before:** All queries showed 1-3% confidence ❌  
**After:** Should show 20-95% confidence ✅

**Test Queries:**
```
1. "What is AtlasIQ about?"
   Expected: High confidence (75-95%)
   Expected: Only AtlasIQ documents

2. "What is the audit engagement letter about?"
   Expected: High confidence (75-95%)
   Expected: Only audit documents
```

### 3. Test Enhanced Citations (New Feature!)

**Check for:**
- ✅ Citation cards are displayed
- ✅ Click citation → Expands to show full chunk content
- ✅ Shows metadata: Page, Chunk Index, RRF Score
- ✅ Copy button (📋 icon) present
- ✅ Click copy → Shows checkmark feedback
- ✅ Paste → Citation formatted correctly

**Expected Citation Format:**
```
"Quote text from the document..."

Source: document.pdf
Page: 5
```

### 4. Test Retrieval Details (New Feature!)

**Scroll down below citations to find:**
- ✅ "RETRIEVAL DETAILS" section
- ✅ Method badge showing "Hybrid"
- ✅ Statistics: Total Candidates, Final Retrieved, Filtered Out
- ✅ Chunk table with columns:
  - Rank (#)
  - Document name
  - Chunk index
  - Page
  - RRF Score
  - Content preview

**This is the differentiator!** Shows technical sophistication.

---

## 🐛 Debug Logging (If Enabled)

With `DEBUG` logging, you'll see detailed retrieval information:

```
[DEBUG] Hybrid retrieval query: What is AtlasIQ about?
[DEBUG] DenseRetriever returned 20 chunks (top scores: [0.8523, 0.7841, ...])
[DEBUG] BM25Retriever returned 20 chunks (top scores: [15.23, 12.45, ...])
[DEBUG] RRF fusion: 35 unique chunks, top scores: [0.0164, 0.0158, ...]
[DEBUG] Filtered 5 weak chunks (score < 0.011), 30 remaining
[DEBUG] Top retrieved chunks:
[DEBUG]   [1] AtlasIQ_Project_Guide.pdf (chunk 2, score 0.0164)
[DEBUG]   [2] AtlasIQ_Project_Guide.pdf (chunk 5, score 0.0158)
[INFO] Guardrail passed: top RRF score 0.0164 >= threshold 0.01, confidence=0.85
```

This helps verify the fixes are working correctly!

---

## 📊 Test the API Directly (Optional)

```bash
# Test query endpoint
curl -X POST http://localhost:8000/query ^
  -H "Content-Type: application/json" ^
  -d "{\"question\": \"What is AtlasIQ about?\"}"
```

**Look for in response:**
- `"confidence"`: Should be 0.20-0.95 (not 0.01-0.03!)
- `"citations"`: Should have `chunk_index` and `score` fields
- `"retrieval_details"`: Should be present with chunk table

---

## 🎨 UI Features to Showcase

### Citation Panel
```
┌─────────────────────────────────────┐
│ [1] 📄 document.pdf       [📋] [▼] │ ← Click to expand
│     Page: 5 • Chunk: 2 • RRF: 1.64 │
├─────────────────────────────────────┤
│ [Expanded Content]                  │
│ "Full chunk text showing complete   │
│  context around the citation..."    │
└─────────────────────────────────────┘
```

### Retrieval Details
```
┌─ RETRIEVAL DETAILS ─────────────────┐
│ Method: HYBRID                       │
│ [Total: 35] [Final: 20] [Filtered:5]│
│                                      │
│ ┌──┬──────────┬───────┬──────┬─────┐│
│ │# │ Document │ Chunk │ Page │ RRF ││
│ ├──┼──────────┼───────┼──────┼─────┤│
│ │1 │ doc.pdf  │   2   │  5   │0.016││
│ └──┴──────────┴───────┴──────┴─────┘│
└──────────────────────────────────────┘
```

---

## ⚠️ Troubleshooting

### "Backend Unreachable" Error

**Symptom:** Frontend shows "Backend Offline" or "Backend Unreachable"

**Solution:**
1. **Check if backend is running:**
   - Look for a terminal/command window with backend output
   - Should show: "Uvicorn running on http://0.0.0.0:8000"

2. **If backend is NOT running:**
   - Double-click `start_backend.bat` (easiest)
   - OR manually run: `python -m atlasiq.backend.main`

3. **Wait for startup:**
   - Backend takes 5-10 seconds to start
   - Wait for "Application startup complete"

4. **Refresh browser:**
   - After backend starts, refresh http://localhost:8502
   - Status should change to "Optimal"

5. **Check for port conflicts:**
   ```bash
   netstat -ano | findstr :8000
   ```
   - If port is in use, kill the process or use a different port

**Common Mistake:** Starting only the frontend without the backend!

---

### Backend Won't Start
```bash
# Check if port 8000 is already in use
netstat -ano | findstr :8000

# Kill existing process if needed
taskkill /PID <PID> /F
```

### Frontend Won't Start
```bash
# Check if port 8502 is already in use
netstat -ano | findstr :8502

# Kill existing process if needed
taskkill /PID <PID> /F
```

### PostgreSQL Not Running
```bash
# Start PostgreSQL service
net start postgresql-x64-15
```

### Qdrant Not Running
```bash
# If using Docker
docker start qdrant

# Or check documentation for your Qdrant setup
```

### No Documents in Database
```bash
# Upload test documents via API
curl -X POST http://localhost:8000/ingest ^
  -F "file=@document.pdf"
```

Or use the Upload button in the UI (sidebar).

---

## 📁 Recent Changes Summary

### 1. Confidence Fix
- **Before:** 1-3% for all queries (broken)
- **After:** 20-95% based on retrieval quality
- **Why:** Uses heuristics (document diversity, coverage, score concentration)

### 2. Enhanced Citations
- Expandable cards
- Full chunk content
- Metadata display (page, chunk, score)
- Copy functionality

### 3. Retrieval Details
- Method badge (Hybrid)
- Statistics dashboard
- Chunk breakdown table
- Technical transparency

### 4. Relevance Filtering
- New `hybrid_min_score` parameter (0.011)
- Filters weak chunks
- Better retrieval quality

### 5. Debug Logging
- Comprehensive retrieval logs
- Individual retriever results
- RRF fusion details
- Filtering statistics

---

## 📚 Documentation

**Read these for details:**
1. `docs/LATEST_CHANGES.md` - Quick summary
2. `docs/RETRIEVAL_CONFIDENCE_FIX.md` - Confidence fix details
3. `docs/CITATION_RETRIEVAL_ENHANCEMENTS.md` - Citation features
4. `docs/RETRIEVAL_CONFIDENCE_INVESTIGATION.md` - Problem investigation

---

## 🎯 Success Criteria

After starting, verify:

- [x] Backend running on port 8000
- [x] Frontend running on port 8502
- [x] Can submit queries
- [x] Confidence shows 20-95% (not 1-3%)
- [x] Citations expand/collapse
- [x] Copy button works
- [x] Retrieval details display
- [x] Footer is clean (no policy text)
- [x] Debug logs show retrieval breakdown (if enabled)

---

## 🚦 Quick Command Reference

```bash
# Single command (starts both):
cd C:\Users\yashv\Desktop\AtlasIQ
.venv\Scripts\python.exe start_atlasiq.py

# Or manually with two terminals:
# Terminal 1 - Backend:
cd C:\Users\yashv\Desktop\AtlasIQ
.venv\Scripts\activate
.venv\Scripts\uvicorn.exe atlasiq.backend.main:app --host 0.0.0.0 --port 8000

# Terminal 2 - Frontend:
cd C:\Users\yashv\Desktop\AtlasIQ
.venv\Scripts\activate
python -m atlasiq.frontend.serve

# Browser:
http://localhost:8502
```

---

## 💡 Tips

1. **Keep both terminals running** while testing
2. **Use DEBUG logging** to see retrieval details
3. **Test multiple queries** to verify confidence ranges
4. **Expand citations** to see full content
5. **Scroll to retrieval details** to showcase technical depth
6. **Use copy button** to test clipboard functionality

---

## 🎉 Ready!

You're all set! Tomorrow, just run the commands in "Quick Command Reference" and start testing.

**Questions?** Check the documentation in `docs/` folder.

**Happy testing!** 🚀

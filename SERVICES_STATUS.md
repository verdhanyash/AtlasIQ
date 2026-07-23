# ✅ AtlasIQ Services Status

**Started:** $(Get-Date)  
**GPU Acceleration:** ENABLED

## Running Services

### 🐳 Docker Services
- **PostgreSQL:** ✅ Running (Port 5433, Healthy)
- **Qdrant:** ✅ Running (Port 6333, Healthy)

### 🚀 Application Services
- **Backend API:** ✅ Running on http://localhost:8000
- **Frontend UI:** ✅ Running on http://localhost:8502

### 🎮 GPU Configuration
- **PyTorch CUDA:** ✅ Available
- **GPU:** NVIDIA GeForce RTX 3050 6GB Laptop GPU
- **CUDA Version:** 11.8
- **Embedding Device:** cuda
- **Reranker Device:** cuda

## Configuration Active

```yaml
LLM Provider: nvidia
Model: deepseek-ai/deepseek-v4-pro
Embedding Model: nomic-ai/nomic-embed-text-v1.5 (GPU)
Reranker Model: BAAI/bge-reranker-v2-m3 (GPU)
```

## Access URLs

- **Frontend:** http://localhost:8502
- **Backend API:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs
- **Health Check:** http://localhost:8000/health

## Expected Performance

With GPU acceleration enabled:
- Upload processing: **3-4x faster** than CPU
- Embedding 180 chunks: ~2-5 seconds (was ~60 seconds)
- Total upload (7.8MB): ~30-60 seconds (was 2-3 minutes)

## Test Your Setup

1. Open http://localhost:8502 in your browser
2. Upload a document (try a 5-10MB PDF)
3. Watch the progress bar - should complete much faster
4. Check timing metadata in response for GPU speedup confirmation

## Monitor GPU Usage

Open a new terminal and run:
```bash
nvidia-smi
```

During upload, you should see:
- Python process using ~4-5GB GPU memory
- GPU utilization spiking to 50-100%

## Stop Services

To stop all services:
```bash
# Stop Python processes
Get-Process | Where-Object {$_.ProcessName -eq "python" -and $_.Path -like "*AtlasIQ*"} | Stop-Process

# Stop Docker (if needed)
docker-compose down
```

## Restart Services

To restart everything:
```bash
python start_atlasiq.py
```

Or manually:
```bash
# Backend
.venv\Scripts\python.exe -m uvicorn atlasiq.backend.main:app --host 0.0.0.0 --port 8000

# Frontend (in another terminal)
.venv\Scripts\python.exe atlasiq\frontend\serve.py
```

## Logs Location

- Backend logs: Terminal output where backend was started
- Frontend logs: Terminal output where frontend was started
- Watcher logs: `watcher.log`

---

**Status:** All services operational with GPU acceleration! 🚀

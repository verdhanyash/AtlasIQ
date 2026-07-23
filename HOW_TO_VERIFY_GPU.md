# How to Verify GPU Acceleration is Working

## Quick Verification

### Method 1: Check Backend Logs After Upload

1. **Upload a document** through the UI (http://localhost:8502)
2. **Check the backend logs** for the device configuration message

Look for this line in the backend terminal or `backend.log`:
```json
{"timestamp": "...", "level": "INFO", "logger": "atlasiq.ingestion.embedder", 
 "message": "Embedder configured: model=nomic-ai/nomic-embed-text-v1.5, batch_size=32, device=cuda"}
```

**KEY:** The message should say `device=cuda` NOT `device=cpu`

### Method 2: Check Upload Performance

Upload a document and check the timing metadata in the response:

**CPU (Before):**
```json
"timings": {
  "parse_time_ms": 45000,
  "chunk_time_ms": 100,
  "embed_time_ms": 60000,    ← 60 seconds!
  "store_time_ms": 200,
  "total_time_ms": 105000
}
```

**GPU (After - Expected):**
```json
"timings": {
  "parse_time_ms": 45000,
  "chunk_time_ms": 100,
  "embed_time_ms": 2000,     ← 2 seconds! (30x faster)
  "store_time_ms": 200,
  "total_time_ms": 47000
}
```

### Method 3: Monitor GPU Usage in Real-Time

Open a **new terminal** and run:
```bash
nvidia-smi -l 1
```

This refreshes every second. During document upload, you should see:
- **GPU Utilization:** Spikes to 50-100%
- **GPU Memory:** ~4-5GB used by Python process
- **Power Usage:** Increases during processing

**Example Output During Upload:**
```
+-----------------------------------------------------------------------------+
| NVIDIA-SMI 535.XX       Driver Version: 535.XX       CUDA Version: 11.8  |
|-------------------------------+----------------------+----------------------+
| GPU  Name        Persistence-M| Bus-Id        Disp.A | Volatile Uncorr. ECC |
| Fan  Temp  Perf  Pwr:Usage/Cap|         Memory-Usage | GPU-Util  Compute M. |
|===============================+======================+======================|
|   0  NVIDIA GeForce ... Off  | 00000000:01:00.0 Off |                  N/A |
| N/A   65C    P0    25W /  N/A |   4512MiB /  6144MiB |     87%      Default |
+-------------------------------+----------------------+----------------------+
```

### Method 4: Check Configuration File

Verify `configs/default.yaml` has GPU enabled:

```bash
# Check embedding device
grep -A 3 "embedding:" configs/default.yaml

# Check reranker device  
grep -A 3 "reranker:" configs/default.yaml
```

**Should show:**
```yaml
embedding:
  model_name: "nomic-ai/nomic-embed-text-v1.5"
  batch_size: 32
  device: "cuda"  ← GPU enabled

reranker:
  model_name: "BAAI/bge-reranker-v2-m3"
  device: "cuda"  ← GPU enabled
```

### Method 5: Test PyTorch CUDA Directly

Run this in your terminal:
```bash
.venv\Scripts\python.exe -c "import torch; print('CUDA:', torch.cuda.is_available()); print('GPU:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'N/A')"
```

**Expected Output:**
```
CUDA: True
GPU: NVIDIA GeForce RTX 3050 6GB Laptop GPU
```

## What to Look For

### ✅ GPU is Working If You See:
- ` device=cuda` in embedder configuration logs
- Embedding time drops from ~60s to ~2-5s
- `nvidia-smi` shows GPU utilization spiking during upload
- GPU memory usage increases to 4-5GB during processing
- Overall upload time is 3-4x faster

### ❌ GPU is NOT Working If You See:
- `device=cpu` in embedder configuration logs
- Embedding time still ~60 seconds
- `nvidia-smi` shows 0% GPU utilization
- GPU memory stays at baseline
- Upload times unchanged

## Troubleshooting

### If GPU is Not Being Used

1. **Verify Configuration:**
   ```bash
   cat configs/default.yaml | grep -A 2 "device:"
   ```
   Should show `device: "cuda"` not `device: "cpu"`

2. **Restart Backend:**
   - Configuration is loaded at startup only
   - Stop backend process and restart
   ```bash
   python start_atlasiq.py
   ```

3. **Check PyTorch Installation:**
   ```bash
   .venv\Scripts\python.exe -c "import torch; print(torch.__version__)"
   ```
   Should show `2.7.1+cu118` NOT `2.12.1+cpu`

4. **Check for Errors:**
   Look in backend logs for CUDA errors:
   ```bash
   cat backend.log | grep -i "cuda\|gpu\|error"
   ```

### If You Get CUDA Out of Memory

Reduce batch size in `configs/default.yaml`:
```yaml
embedding:
  batch_size: 16  # or even 8
```

Then restart backend.

## Test Upload

To trigger GPU usage immediately:

1. Go to http://localhost:8502
2. Click "Upload Documents"
3. Select any PDF or DOCX file
4. Watch:
   - Progress bar should complete quickly
   - `nvidia-smi` in another terminal
   - Backend logs for `device=cuda`

---

**Current Status:** Services restarted with GPU config, waiting for first upload to verify

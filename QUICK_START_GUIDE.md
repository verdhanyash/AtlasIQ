# AtlasIQ - Quick Start Guide

## 🚀 Services Running

- **Frontend:** http://localhost:8502 ✅
- **Backend:** http://localhost:8000 ✅
- **API Docs:** http://localhost:8000/docs ✅

## 🎯 New Features - Model Settings

### Access the Model Settings
1. Open http://localhost:8502 in your browser
2. Click **"Model Settings"** (⚙️ icon) in the left sidebar

### What You'll See

#### For NVIDIA Provider:
- **Dropdown with 11 models** organized by category:
  - Latest Free (2026): DeepSeek V4 Pro, Kimi K2.6
  - Free: DeepSeek R1, GLM-4-Plus, Kimi K1.5
  - Premium: Llama 3.1 (8B, 70B, 405B, Nemotron)

- **Smart API Key Detection:**
  - Green status if configured in `.env`
  - Optional field with helper text
  - Leave empty to use `.env` configuration

### Quick Test Steps

1. **Open the UI:** http://localhost:8502
2. **Click:** "Model Settings" in sidebar
3. **Select:** Provider = "NVIDIA Build API"
4. **See:** Dropdown with model options (not a text field!)
5. **Notice:** API key shows status and helper text

## 📝 Configuration Options

### Option 1: Use .env (Recommended for Production)

Create `.env` file:
```bash
copy .env.example .env
```

Add your API key:
```env
ATLASIQ_LLM__PROVIDER=nvidia
ATLASIQ_LLM__MODEL=deepseek-ai/deepseek-v4-pro
ATLASIQ_NVIDIA__API_KEY=nvapi-your-key-here
```

Restart backend:
```bash
# Stop: Ctrl+C or Stop-Process -Id <PID>
# Start: python start_atlasiq.py
```

### Option 2: Configure in UI (Quick Testing)

1. Open Model Settings
2. Select provider and model from dropdowns
3. Enter API key (or leave empty if in `.env`)
4. Click "Save Settings"

## 🔑 Get NVIDIA API Key

1. Visit: https://build.nvidia.com/
2. Sign in / Create account
3. Click "Get API Key" on any model page
4. Copy key (starts with `nvapi-`)

## 🎨 Available Models

### DeepSeek V4 Pro (Latest, Free)
- ID: `deepseek-ai/deepseek-v4-pro`
- Params: MoE 1.6T
- Best for: Complex reasoning, code generation

### Moonshot Kimi K2.6 (Latest, Free)
- ID: `moonshotai/kimi-k2.6`
- Params: MoE 1T
- Best for: Long context tasks

### DeepSeek R1 (Free)
- ID: `deepseek/deepseek-r1`
- Best for: General Q&A

### GLM-4-Plus (Free)
- ID: `zhipuai/glm-4-plus`
- Best for: Multilingual tasks

### Moonshot Kimi K1.5 (Free)
- ID: `moonshot/moonshot-v1-128k`
- Context: 128K tokens
- Best for: Long documents

## 🧪 Test Your Setup

Run test script:
```bash
python test_frontend_changes.py
```

Expected output:
```
✓ Health endpoint: PASS
✓ Config endpoint: PASS
✓ All tests passed!
```

## 📊 Current Status

Run this to check status:
```bash
python -c "import requests; r = requests.get('http://localhost:8000/config/check'); print(r.json())"
```

Output shows:
- Which API keys are configured
- Current provider and model
- Configuration status

## 🎯 Example Workflow

### 1. Test with Free Model
```
1. Open http://localhost:8502
2. Click "Model Settings"
3. Provider: NVIDIA Build API
4. Model: DeepSeek V4 Pro (dropdown)
5. API Key: (enter yours or use .env)
6. Click "Save Settings"
7. Try a query in the main interface
```

### 2. Switch Models Easily
```
1. Open "Model Settings" again
2. Select different model from dropdown
3. No need to type model IDs!
4. Click "Save Settings"
5. Test immediately
```

## 🔧 Troubleshooting

### "API key not detected"
- Check `.env` file exists
- Verify key format: `ATLASIQ_NVIDIA__API_KEY=nvapi-...`
- Restart backend after `.env` changes

### "Dropdown not showing"
- Hard refresh: Ctrl+F5
- Clear browser cache
- Check browser console for errors

### "Backend not responding"
```bash
# Check if running
netstat -ano | findstr ":8000"

# Restart if needed
python start_atlasiq.py
```

## 📚 Documentation

- **Full Summary:** `FRONTEND_IMPROVEMENTS_SUMMARY.md`
- **NVIDIA Guide:** `docs/NVIDIA_LATEST_MODELS_2026.md`
- **Model Reference:** `NVIDIA_MODELS_QUICK_REFERENCE.md`
- **API Docs:** http://localhost:8000/docs

## ✅ What's New

✨ **NVIDIA model selection is now a dropdown**
- No more typing complex model IDs
- Organized by category (Latest/Free/Premium)
- 11 models available

✨ **Smart API key handling**
- Detects if configured in `.env`
- Shows green status when found
- Optional UI override for testing

✨ **Better user experience**
- Clear visual feedback
- Helper text and tooltips
- Professional UI design

## 🎉 Ready to Use!

Your AtlasIQ instance is running and ready with the improved model selection interface. Open http://localhost:8502 and try it out!

**Questions?** Check the documentation files or API docs at http://localhost:8000/docs

# 🔑 How to Get Your NVIDIA API Key

## Quick Steps

### 1. Visit NVIDIA Build
Go to: **https://build.nvidia.com/**

### 2. Sign In
- Click "Sign In" or "Get Started"
- Use your NVIDIA account (or create one - it's free!)
- You can sign in with:
  - NVIDIA account
  - Google account
  - GitHub account

### 3. Get API Key
- Once signed in, click on any model (e.g., "DeepSeek R1" or "Llama")
- Look for **"Get API Key"** button (usually top right)
- Click it and copy your API key
- It will look like: `nvapi-xxxxxxxxxxxxxxxxxxxxxx`

### 4. Add to .env File
Open the `.env` file I just created and replace:
```env
ATLASIQ_NVIDIA__API_KEY=PUT_YOUR_NVIDIA_API_KEY_HERE
```

With your actual key:
```env
ATLASIQ_NVIDIA__API_KEY=nvapi-your-actual-key-here
```

### 5. Restart Backend
After adding your key, restart the backend:

```bash
# Stop the current backend (Ctrl+C or)
Stop-Process -Name python -Force

# Start it again
python start_atlasiq.py
```

Or manually:
```bash
.venv\Scripts\uvicorn.exe atlasiq.backend.main:app --host 0.0.0.0 --port 8000
```

## 📍 Your .env File Location

I've already created it here:
```
C:\Users\yashv\Desktop\AtlasIQ\.env
```

## ✅ What I've Set Up For You

In your `.env` file, I've configured:
- **Provider:** `nvidia` (instead of ollama)
- **Model:** `deepseek-ai/deepseek-v4-pro` (the latest free model)
- **API Key:** Placeholder that you need to replace

## 🎯 Current Configuration

```env
ATLASIQ_LLM__PROVIDER=nvidia
ATLASIQ_LLM__MODEL=deepseek-ai/deepseek-v4-pro
ATLASIQ_NVIDIA__API_KEY=PUT_YOUR_NVIDIA_API_KEY_HERE  ← Replace this!
```

## 🚀 After Getting Your API Key

1. **Edit .env:**
   ```bash
   notepad .env
   ```

2. **Replace the placeholder:**
   ```env
   ATLASIQ_NVIDIA__API_KEY=nvapi-your-actual-key-here
   ```

3. **Save the file** (Ctrl+S)

4. **Restart backend:**
   ```bash
   python start_atlasiq.py
   ```

5. **Test it:**
   - Open http://localhost:8502
   - Try asking a question
   - It should now use DeepSeek V4 Pro via NVIDIA Build!

## 🔍 Verify It's Working

After restarting, run:
```bash
python test_frontend_changes.py
```

Should show:
```
✓ NVIDIA API Key configured: True
✓ Current provider: nvidia
✓ Current model: deepseek-ai/deepseek-v4-pro
```

## 🆓 Free Models Available

All these models are **FREE** on NVIDIA Build:
- ✅ DeepSeek V4 Pro (1.6T params, latest)
- ✅ Moonshot Kimi K2.6 (1T params, latest)
- ✅ DeepSeek R1
- ✅ GLM-4-Plus
- ✅ Moonshot Kimi K1.5

## 💡 Pro Tips

1. **Keep your API key secret** - don't share it or commit `.env` to git
2. **The .env file is already in .gitignore** - safe!
3. **You can change models anytime** by editing `ATLASIQ_LLM__MODEL`
4. **Or use the UI** - the new dropdown makes it easy!

## ❓ Need Help?

If you have issues:
1. Make sure the API key starts with `nvapi-`
2. No spaces or quotes around the key
3. Restart backend after adding the key
4. Check http://localhost:8000/config/check to verify

## 📸 Visual Guide

```
NVIDIA Build Website
     ↓
Sign In / Create Account
     ↓
Click Any Model
     ↓
"Get API Key" Button
     ↓
Copy Key (nvapi-xxx...)
     ↓
Paste in .env file
     ↓
Restart Backend
     ↓
✅ Ready to Use!
```

---

**Next Step:** Get your API key from https://build.nvidia.com/ and add it to the `.env` file!

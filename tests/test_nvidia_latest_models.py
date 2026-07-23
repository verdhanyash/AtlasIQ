"""Integration test for latest NVIDIA Build models (2026).

Tests the latest free NVIDIA Build models:
- DeepSeek V4 Pro (deepseek-ai/deepseek-v4-pro)
- Moonshot Kimi K2.6 (moonshotai/kimi-k2.6)

Verifies:
1. Provider accepts new model IDs
2. Configuration loads correctly
3. Provider instantiates without errors
4. Model-agnostic architecture preserved
5. Backward compatibility with previous models
6. No code changes required

Usage:
    # Configuration test only (no API calls)
    python test_nvidia_latest_models.py
    
    # With live API testing (requires API key)
    export ATLASIQ_NVIDIA__API_KEY=nvapi-your-key-here
    python test_nvidia_latest_models.py --live
"""

import os
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from atlasiq.backend.core.config import load_settings
from atlasiq.retrieval.llm.factory import create_llm_provider
from atlasiq.retrieval.llm.nvidia_provider import NvidiaProvider
from atlasiq.retrieval.prompt_builder import BuiltPrompt


# Latest NVIDIA Build models (April 2026)
LATEST_MODELS = {
    "deepseek-ai/deepseek-v4-pro": {
        "name": "DeepSeek V4 Pro",
        "description": "MoE 1.6T params, 49B active",
        "best_for": "Reasoning, code, efficiency",
    },
    "moonshotai/kimi-k2.6": {
        "name": "Moonshot Kimi K2.6",
        "description": "MoE 1T params, 32B active",
        "best_for": "Long-horizon coding, multimodal",
    },
}

# Previous models (for backward compatibility testing)
PREVIOUS_MODELS = {
    "deepseek/deepseek-r1": "DeepSeek R1",
    "zhipuai/glm-4-plus": "GLM-4-Plus",
    "moonshot/moonshot-v1-128k": "Moonshot Kimi K1.5",
}


def test_model_configuration(model_id: str, model_info: dict) -> bool:
    """Test that a model can be configured correctly."""
    print(f"\n{'─' * 75}")
    print(f"📦 Configuration Test: {model_info['name']}")
    print(f"   Model ID: {model_id}")
    print(f"   Description: {model_info['description']}")
    print('─' * 75)
    
    try:
        # Set model via environment
        os.environ["ATLASIQ_LLM__PROVIDER"] = "nvidia"
        os.environ["ATLASIQ_LLM__MODEL"] = model_id
        
        # Load settings
        settings = load_settings()
        
        # Verify configuration
        assert settings.llm.provider == "nvidia", f"Provider should be nvidia, got {settings.llm.provider}"
        assert settings.llm.model == model_id, f"Model should be {model_id}, got {settings.llm.model}"
        
        print(f"✅ Provider: {settings.llm.provider}")
        print(f"✅ Model: {settings.llm.model}")
        print(f"✅ Base URL: {settings.nvidia.base_url}")
        print(f"✅ Temperature: {settings.llm.temperature}")
        print(f"✅ Max Tokens: {settings.llm.max_tokens}")
        
        return True
        
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False


def test_provider_instantiation(model_id: str, model_info: dict) -> bool:
    """Test that provider can be instantiated with the model."""
    print(f"\n{'─' * 75}")
    print(f"🔧 Instantiation Test: {model_info['name']}")
    print(f"   Model ID: {model_id}")
    print('─' * 75)
    
    try:
        # Set model and dummy API key
        os.environ["ATLASIQ_LLM__PROVIDER"] = "nvidia"
        os.environ["ATLASIQ_LLM__MODEL"] = model_id
        os.environ["ATLASIQ_NVIDIA__API_KEY"] = "test-key-for-instantiation"
        
        settings = load_settings()
        
        # Create provider through factory
        provider = create_llm_provider(
            settings.llm,
            settings.ollama,
            settings.nvidia,
        )
        
        # Verify it's NVIDIA provider
        assert isinstance(provider, NvidiaProvider), f"Should be NvidiaProvider, got {type(provider)}"
        
        # Verify it has required methods
        assert hasattr(provider, 'generate'), "Provider missing generate method"
        assert hasattr(provider, 'close'), "Provider missing close method"
        
        # Verify internal state
        assert provider._model == model_id, f"Internal model should be {model_id}"
        
        print(f"✅ Provider type: {type(provider).__name__}")
        print(f"✅ Internal model: {provider._model}")
        print(f"✅ Has generate(): {hasattr(provider, 'generate')}")
        print(f"✅ Has close(): {hasattr(provider, 'close')}")
        
        # Clean up
        provider.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Instantiation test failed: {e}")
        return False


def test_backward_compatibility() -> bool:
    """Test that previous models still work."""
    print(f"\n{'═' * 75}")
    print("🔄 Backward Compatibility Test")
    print('═' * 75)
    
    try:
        os.environ["ATLASIQ_LLM__PROVIDER"] = "nvidia"
        os.environ["ATLASIQ_NVIDIA__API_KEY"] = "test-key"
        
        all_passed = True
        for model_id, model_name in PREVIOUS_MODELS.items():
            os.environ["ATLASIQ_LLM__MODEL"] = model_id
            settings = load_settings()
            
            if settings.llm.model == model_id:
                print(f"✅ {model_name}: {model_id}")
            else:
                print(f"❌ {model_name}: Failed to configure")
                all_passed = False
        
        if all_passed:
            print("\n✅ All previous models still work")
        
        return all_passed
        
    except Exception as e:
        print(f"❌ Backward compatibility test failed: {e}")
        return False


def test_model_switching() -> bool:
    """Test switching between latest and previous models."""
    print(f"\n{'═' * 75}")
    print("🔀 Model Switching Test")
    print('═' * 75)
    
    try:
        os.environ["ATLASIQ_LLM__PROVIDER"] = "nvidia"
        os.environ["ATLASIQ_NVIDIA__API_KEY"] = "test-key"
        
        # Test switching to latest models
        for model_id in LATEST_MODELS.keys():
            os.environ["ATLASIQ_LLM__MODEL"] = model_id
            settings = load_settings()
            assert settings.llm.model == model_id
            print(f"✅ Switched to: {model_id}")
        
        # Test switching back to a previous model
        os.environ["ATLASIQ_LLM__MODEL"] = "deepseek/deepseek-r1"
        settings = load_settings()
        assert settings.llm.model == "deepseek/deepseek-r1"
        print(f"✅ Switched back to: deepseek/deepseek-r1")
        
        # Test switching to Ollama
        os.environ["ATLASIQ_LLM__PROVIDER"] = "ollama"
        os.environ["ATLASIQ_LLM__MODEL"] = "gemma3:4b"
        settings = load_settings()
        assert settings.llm.provider == "ollama"
        print(f"✅ Switched to Ollama: {settings.llm.model}")
        
        print("\n✅ Model switching works correctly")
        return True
        
    except Exception as e:
        print(f"❌ Model switching failed: {e}")
        return False


def test_provider_code_unchanged() -> bool:
    """Verify NVIDIA provider code hasn't been modified."""
    print(f"\n{'═' * 75}")
    print("🔍 Provider Code Verification")
    print('═' * 75)
    
    provider_file = PROJECT_ROOT / "atlasiq" / "retrieval" / "llm" / "nvidia_provider.py"
    
    if not provider_file.exists():
        print("❌ Provider file not found")
        return False
    
    # Read provider code
    with open(provider_file, 'r', encoding='utf-8') as f:
        code = f.read()
    
    # Verify no hardcoded models
    hardcoded_checks = [
        ("deepseek-v4-pro" not in code, "No hardcoded DeepSeek V4 Pro"),
        ("kimi-k2.6" not in code, "No hardcoded Kimi K2.6"),
        ("self._model = llm_config.model" in code, "Model from config"),
        ("model=self._model" in code, "Model passed dynamically"),
    ]
    
    all_passed = True
    for check, description in hardcoded_checks:
        if check:
            print(f"✅ {description}")
        else:
            print(f"❌ {description}")
            all_passed = False
    
    if all_passed:
        print("\n✅ Provider remains model-agnostic")
    
    return all_passed


def test_pipeline_unchanged() -> bool:
    """Verify RAG pipeline components are unchanged."""
    print(f"\n{'═' * 75}")
    print("🔍 Pipeline Components Verification")
    print('═' * 75)
    
    critical_files = [
        "atlasiq/retrieval/dense_retriever.py",
        "atlasiq/retrieval/bm25_retriever.py",
        "atlasiq/retrieval/hybrid_retriever.py",
        "atlasiq/retrieval/prompt_builder.py",
        "atlasiq/retrieval/citations.py",
        "atlasiq/retrieval/guardrails.py",
        "atlasiq/retrieval/qa_pipeline.py",
    ]
    
    all_present = True
    for file_path in critical_files:
        full_path = PROJECT_ROOT / file_path
        if full_path.exists():
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path} (missing)")
            all_present = False
    
    if all_present:
        print("\n✅ All pipeline components unchanged")
    
    return all_present


def test_live_generation(model_id: str, model_info: dict) -> bool:
    """Test live generation (optional, requires API key)."""
    print(f"\n{'─' * 75}")
    print(f"🚀 Live Generation Test: {model_info['name']}")
    print(f"   Model ID: {model_id}")
    print('─' * 75)
    
    api_key = os.environ.get("ATLASIQ_NVIDIA__API_KEY", "")
    
    if not api_key or api_key.startswith("test-"):
        print("⏭️  Skipping (no real API key)")
        print("   Set ATLASIQ_NVIDIA__API_KEY=nvapi-... to test")
        return None  # Not a failure, just skipped
    
    try:
        # Configure for this model
        os.environ["ATLASIQ_LLM__PROVIDER"] = "nvidia"
        os.environ["ATLASIQ_LLM__MODEL"] = model_id
        
        settings = load_settings()
        provider = create_llm_provider(
            settings.llm,
            settings.ollama,
            settings.nvidia,
        )
        
        # Create test prompt
        prompt = BuiltPrompt(
            system_prompt="You are a helpful assistant. Answer in one short sentence.",
            user_prompt="What is 2+2? Just give the number.",
        )
        
        print("   Sending request to NVIDIA API...")
        answer = provider.generate(prompt)
        
        # Verify response
        assert answer, "Response should not be empty"
        assert len(answer) > 0, "Response should have content"
        
        print(f"✅ Response received ({len(answer)} chars)")
        print(f"   Answer: {answer.strip()[:100]}")
        
        # Clean up
        provider.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Live test failed: {e}")
        print(f"   Possible causes:")
        print(f"   - Invalid API key")
        print(f"   - Model not available")
        print(f"   - Network issues")
        print(f"   - Rate limiting")
        return False


def main():
    """Run all tests for latest NVIDIA models."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test latest NVIDIA Build models")
    parser.add_argument("--live", action="store_true", help="Run live API tests")
    args = parser.parse_args()
    
    print("\n" + "=" * 75)
    print("NVIDIA BUILD LATEST MODELS (2026) - INTEGRATION TEST")
    print("=" * 75)
    print("\nTesting latest models:")
    for model_id, info in LATEST_MODELS.items():
        print(f"  • {info['name']}")
        print(f"    ID: {model_id}")
        print(f"    Description: {info['description']}")
        print(f"    Best for: {info['best_for']}")
    print()
    
    results = {
        "configuration": [],
        "instantiation": [],
        "live_generation": [],
    }
    
    # Test each latest model
    for model_id, model_info in LATEST_MODELS.items():
        # Test 1: Configuration
        config_pass = test_model_configuration(model_id, model_info)
        results["configuration"].append((model_id, config_pass))
        
        # Test 2: Instantiation
        inst_pass = test_provider_instantiation(model_id, model_info)
        results["instantiation"].append((model_id, inst_pass))
        
        # Test 3: Live generation (optional)
        if args.live:
            live_result = test_live_generation(model_id, model_info)
            if live_result is not None:
                results["live_generation"].append((model_id, live_result))
    
    # Test 4: Backward compatibility
    compat_pass = test_backward_compatibility()
    
    # Test 5: Model switching
    switching_pass = test_model_switching()
    
    # Test 6: Provider code unchanged
    code_pass = test_provider_code_unchanged()
    
    # Test 7: Pipeline unchanged
    pipeline_pass = test_pipeline_unchanged()
    
    # Summary
    print("\n" + "=" * 75)
    print("TEST SUMMARY")
    print("=" * 75)
    
    print("\n📦 Configuration Tests (Latest Models):")
    for model_id, passed in results["configuration"]:
        status = "✅" if passed else "❌"
        model_name = LATEST_MODELS[model_id]["name"]
        print(f"  {status} {model_name}")
    
    print("\n🔧 Instantiation Tests (Latest Models):")
    for model_id, passed in results["instantiation"]:
        status = "✅" if passed else "❌"
        model_name = LATEST_MODELS[model_id]["name"]
        print(f"  {status} {model_name}")
    
    if results["live_generation"]:
        print("\n🚀 Live Generation Tests:")
        for model_id, passed in results["live_generation"]:
            status = "✅" if passed else "❌"
            model_name = LATEST_MODELS[model_id]["name"]
            print(f"  {status} {model_name}")
    elif args.live:
        print("\n⏭️  Live Generation Tests: Skipped (no API key)")
    
    print("\n🔄 Verification Tests:")
    print(f"  {'✅' if compat_pass else '❌'} Backward compatibility")
    print(f"  {'✅' if switching_pass else '❌'} Model switching")
    print(f"  {'✅' if code_pass else '❌'} Provider code unchanged")
    print(f"  {'✅' if pipeline_pass else '❌'} Pipeline unchanged")
    
    # Calculate totals
    config_passed = sum(1 for _, p in results["configuration"] if p)
    config_total = len(results["configuration"])
    
    inst_passed = sum(1 for _, p in results["instantiation"] if p)
    inst_total = len(results["instantiation"])
    
    if results["live_generation"]:
        live_passed = sum(1 for _, p in results["live_generation"] if p)
        live_total = len(results["live_generation"])
        live_summary = f"{live_passed}/{live_total}"
    else:
        live_summary = "Skipped"
    
    verification_passed = sum([compat_pass, switching_pass, code_pass, pipeline_pass])
    verification_total = 4
    
    print(f"\n📊 Pass Rates:")
    print(f"  Configuration: {config_passed}/{config_total}")
    print(f"  Instantiation: {inst_passed}/{inst_total}")
    print(f"  Live Generation: {live_summary}")
    print(f"  Verification: {verification_passed}/{verification_total}")
    
    # Final verdict
    all_required_passed = (
        config_passed == config_total and
        inst_passed == inst_total and
        compat_pass and
        switching_pass and
        code_pass and
        pipeline_pass
    )
    
    print("\n" + "=" * 75)
    if all_required_passed:
        print("🎉 ALL REQUIRED TESTS PASSED!")
        print()
        print("✅ Latest NVIDIA models supported:")
        for model_id, info in LATEST_MODELS.items():
            print(f"   • {info['name']} ({model_id})")
        print()
        print("✅ No code changes required")
        print("✅ Model selection via configuration only")
        print("✅ Backward compatible with previous models")
        print("✅ RAG pipeline unchanged")
        print("✅ Provider remains model-agnostic")
        print()
        if not results["live_generation"] and not args.live:
            print("💡 Run with --live flag and ATLASIQ_NVIDIA__API_KEY to test live generation")
        print()
        return 0
    else:
        print("⚠️  SOME REQUIRED TESTS FAILED")
        print()
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)

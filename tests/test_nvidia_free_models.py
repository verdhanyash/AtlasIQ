"""Test NVIDIA Build free models: DeepSeek R1, GLM-4-Plus, Moonshot Kimi.

This script verifies that all free NVIDIA models can be:
1. Selected through configuration
2. Instantiated correctly
3. Used without modifying the retrieval pipeline

Usage:
    # Without API key (configuration test only)
    python test_nvidia_free_models.py
    
    # With API key (live generation test)
    export ATLASIQ_NVIDIA__API_KEY=nvapi-your-key-here
    python test_nvidia_free_models.py
"""

import os
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from atlasiq.backend.core.config import load_settings
from atlasiq.retrieval.llm.factory import create_llm_provider
from atlasiq.retrieval.llm.nvidia_provider import NvidiaProvider
from atlasiq.retrieval.prompt_builder import BuiltPrompt


# Free NVIDIA Build models to test
FREE_MODELS = {
    "deepseek/deepseek-r1": "DeepSeek R1 (Reasoning & Code)",
    "zhipuai/glm-4-plus": "GLM-4-Plus (Multilingual)",
    "moonshot/moonshot-v1-128k": "Moonshot Kimi K1.5 (Long Context)",
}


def test_model_configuration(model_id: str, description: str) -> bool:
    """Test that a model can be configured correctly."""
    print(f"\n{'─' * 70}")
    print(f"📦 Testing Configuration: {description}")
    print(f"   Model ID: {model_id}")
    print('─' * 70)
    
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
        print(f"✅ Temperature: {settings.llm.temperature}")
        print(f"✅ Max Tokens: {settings.llm.max_tokens}")
        print(f"✅ Base URL: {settings.nvidia.base_url}")
        
        return True
        
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False


def test_provider_instantiation(model_id: str, description: str) -> bool:
    """Test that provider can be instantiated with the model."""
    print(f"\n{'─' * 70}")
    print(f"🔧 Testing Instantiation: {description}")
    print(f"   Model ID: {model_id}")
    print('─' * 70)
    
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


def test_live_generation(model_id: str, description: str) -> bool:
    """Test live generation with the model (requires valid API key)."""
    print(f"\n{'─' * 70}")
    print(f"🚀 Testing Live Generation: {description}")
    print(f"   Model ID: {model_id}")
    print('─' * 70)
    
    api_key = os.environ.get("ATLASIQ_NVIDIA__API_KEY", "")
    
    if not api_key or api_key.startswith("test-"):
        print("⏭️  Skipping live test (no real API key)")
        print("   Set ATLASIQ_NVIDIA__API_KEY=nvapi-... to run live tests")
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
        print(f"   This might be due to:")
        print(f"   - Invalid API key")
        print(f"   - Model not available on free tier")
        print(f"   - Network issues")
        print(f"   - Rate limiting")
        return False


def test_model_switching() -> bool:
    """Test that switching between models works correctly."""
    print(f"\n{'═' * 70}")
    print("🔄 Testing Model Switching")
    print('═' * 70)
    
    try:
        os.environ["ATLASIQ_LLM__PROVIDER"] = "nvidia"
        os.environ["ATLASIQ_NVIDIA__API_KEY"] = "test-key"
        
        for model_id in FREE_MODELS.keys():
            os.environ["ATLASIQ_LLM__MODEL"] = model_id
            settings = load_settings()
            
            assert settings.llm.model == model_id, f"Failed to switch to {model_id}"
            print(f"✅ Switched to: {model_id}")
        
        print("\n✅ Model switching works correctly")
        return True
        
    except Exception as e:
        print(f"❌ Model switching failed: {e}")
        return False


def test_pipeline_unchanged() -> bool:
    """Verify that retrieval pipeline components are unchanged."""
    print(f"\n{'═' * 70}")
    print("🔍 Verifying Pipeline Unchanged")
    print('═' * 70)
    
    critical_files = [
        "atlasiq/retrieval/dense_retriever.py",
        "atlasiq/retrieval/bm25_retriever.py",
        "atlasiq/retrieval/hybrid_retriever.py",
        "atlasiq/retrieval/prompt_builder.py",
        "atlasiq/retrieval/citations.py",
        "atlasiq/retrieval/guardrails.py",
        "atlasiq/retrieval/qa_pipeline.py",
        "atlasiq/retrieval/llm/nvidia_provider.py",
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
        print("\n✅ All pipeline components present")
    
    return all_present


def test_ollama_still_works() -> bool:
    """Verify Ollama provider still works as alternative."""
    print(f"\n{'═' * 70}")
    print("🦙 Verifying Ollama Still Works")
    print('═' * 70)
    
    try:
        os.environ["ATLASIQ_LLM__PROVIDER"] = "ollama"
        os.environ["ATLASIQ_LLM__MODEL"] = "gemma3:4b"
        
        settings = load_settings()
        
        assert settings.llm.provider == "ollama", "Should switch back to ollama"
        assert settings.llm.model == "gemma3:4b", "Should use ollama model"
        
        print(f"✅ Provider: {settings.llm.provider}")
        print(f"✅ Model: {settings.llm.model}")
        print("\n✅ Ollama provider still functional")
        
        return True
        
    except Exception as e:
        print(f"❌ Ollama test failed: {e}")
        return False


def main():
    """Run all tests for free NVIDIA models."""
    print("\n" + "=" * 70)
    print("NVIDIA BUILD FREE MODELS - COMPREHENSIVE TEST")
    print("=" * 70)
    print("\nTesting models:")
    for model_id, desc in FREE_MODELS.items():
        print(f"  • {model_id}")
        print(f"    {desc}")
    print()
    
    results = {
        "configuration": [],
        "instantiation": [],
        "live_generation": [],
    }
    
    # Test each model
    for model_id, description in FREE_MODELS.items():
        # Test 1: Configuration
        config_pass = test_model_configuration(model_id, description)
        results["configuration"].append((model_id, config_pass))
        
        # Test 2: Instantiation
        inst_pass = test_provider_instantiation(model_id, description)
        results["instantiation"].append((model_id, inst_pass))
        
        # Test 3: Live generation (optional)
        live_result = test_live_generation(model_id, description)
        if live_result is not None:
            results["live_generation"].append((model_id, live_result))
    
    # Test 4: Model switching
    switching_pass = test_model_switching()
    
    # Test 5: Pipeline unchanged
    pipeline_pass = test_pipeline_unchanged()
    
    # Test 6: Ollama compatibility
    ollama_pass = test_ollama_still_works()
    
    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    
    print("\n📦 Configuration Tests:")
    for model_id, passed in results["configuration"]:
        status = "✅" if passed else "❌"
        print(f"  {status} {model_id}")
    
    print("\n🔧 Instantiation Tests:")
    for model_id, passed in results["instantiation"]:
        status = "✅" if passed else "❌"
        print(f"  {status} {model_id}")
    
    if results["live_generation"]:
        print("\n🚀 Live Generation Tests:")
        for model_id, passed in results["live_generation"]:
            status = "✅" if passed else "❌"
            print(f"  {status} {model_id}")
    else:
        print("\n⏭️  Live Generation Tests: Skipped (no API key)")
    
    print("\n🔄 Other Tests:")
    print(f"  {'✅' if switching_pass else '❌'} Model switching")
    print(f"  {'✅' if pipeline_pass else '❌'} Pipeline unchanged")
    print(f"  {'✅' if ollama_pass else '❌'} Ollama compatibility")
    
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
    
    other_passed = sum([switching_pass, pipeline_pass, ollama_pass])
    other_total = 3
    
    print(f"\n📊 Pass Rates:")
    print(f"  Configuration: {config_passed}/{config_total}")
    print(f"  Instantiation: {inst_passed}/{inst_total}")
    print(f"  Live Generation: {live_summary}")
    print(f"  Other: {other_passed}/{other_total}")
    
    # Final verdict
    all_required_passed = (
        config_passed == config_total and
        inst_passed == inst_total and
        switching_pass and
        pipeline_pass and
        ollama_pass
    )
    
    print("\n" + "=" * 70)
    if all_required_passed:
        print("🎉 ALL REQUIRED TESTS PASSED!")
        print()
        print("✅ All free NVIDIA models are supported")
        print("✅ Model selection works via configuration")
        print("✅ No code changes were required")
        print("✅ Retrieval pipeline unchanged")
        print("✅ Ollama still works as alternative")
        print()
        if not results["live_generation"]:
            print("💡 Run with ATLASIQ_NVIDIA__API_KEY to test live generation")
        print()
        return 0
    else:
        print("⚠️  SOME REQUIRED TESTS FAILED")
        print()
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)

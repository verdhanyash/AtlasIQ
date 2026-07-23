"""Test script for frontend model selection improvements."""

import requests


def test_config_endpoint():
    """Test the new /config/check endpoint."""
    print("Testing /config/check endpoint...")
    
    try:
        response = requests.get("http://localhost:8000/config/check", timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Config check successful!")
            print(f"  - NVIDIA API Key configured: {data.get('nvidia_api_key_configured', False)}")
            print(f"  - OpenAI API Key configured: {data.get('openai_api_key_configured', False)}")
            print(f"  - Current provider: {data.get('current_provider', 'N/A')}")
            print(f"  - Current model: {data.get('current_model', 'N/A')}")
            return True
        else:
            print(f"✗ Config check failed with status: {response.status_code}")
            print(f"  Response: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"✗ Failed to connect to backend: {e}")
        print("  Make sure the backend is running on http://localhost:8000")
        return False


def test_health_endpoint():
    """Test the health endpoint."""
    print("\nTesting /health endpoint...")
    
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Health check successful!")
            print(f"  - Status: {data.get('status', 'N/A')}")
            print(f"  - LLM Provider: {data.get('checks', {}).get('llm_provider', 'N/A')}")
            print(f"  - LLM Model: {data.get('checks', {}).get('llm_model', 'N/A')}")
            return True
        else:
            print(f"✗ Health check failed with status: {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"✗ Failed to connect to backend: {e}")
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("Frontend Model Selection Improvements - Test Suite")
    print("=" * 60)
    
    health_ok = test_health_endpoint()
    config_ok = test_config_endpoint()
    
    print("\n" + "=" * 60)
    print("Test Results:")
    print(f"  Health endpoint: {'✓ PASS' if health_ok else '✗ FAIL'}")
    print(f"  Config endpoint: {'✓ PASS' if config_ok else '✗ FAIL'}")
    print("=" * 60)
    
    if health_ok and config_ok:
        print("\n✓ All tests passed!")
        print("\nFrontend changes:")
        print("  1. NVIDIA model selection is now a dropdown")
        print("  2. API key field shows if .env is configured")
        print("  3. API key is optional (uses .env if not provided)")
        print("\nNext steps:")
        print("  - Open http://localhost:8502 in your browser")
        print("  - Click 'Model Settings' in the sidebar")
        print("  - Select 'NVIDIA Build API' from the provider dropdown")
        print("  - You should see:")
        print("    * A dropdown with available models (DeepSeek, Kimi, etc.)")
        print("    * A green status message if NVIDIA_API_KEY is in .env")
        print("    * Optional API key field with helper text")
        return 0
    else:
        print("\n✗ Some tests failed!")
        print("  Make sure the backend is running: python -m atlasiq.backend.main")
        return 1


if __name__ == "__main__":
    exit(main())

"""Quick test to start the backend and check for errors."""
import sys
import traceback

if __name__ == "__main__":
    try:
        print("Importing backend modules...")
        import uvicorn

        from atlasiq.backend.main import app

        print("✓ Imports successful!")
        print("Starting backend on http://localhost:8000...")
        print("-" * 50)

        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8000,
            log_level="debug"
        )

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        print("\nFull traceback:")
        traceback.print_exc()
        sys.exit(1)


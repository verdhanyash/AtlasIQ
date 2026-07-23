"""Start both AtlasIQ backend and frontend servers.

This script launches:
- Backend (FastAPI/Uvicorn) on port 8000
- Frontend (HTTP server) on port 8502

Press Ctrl+C to stop both servers.
"""

import os
import subprocess
import sys
import time
from pathlib import Path

# Fix Windows console encoding for emojis
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

# Colors for terminal output
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
RESET = "\033[0m"
BOLD = "\033[1m"

def print_header(text: str) -> None:
    """Print a formatted header."""
    print(f"\n{BOLD}{'='*60}{RESET}")
    print(f"{BOLD}{GREEN}{text:^60}{RESET}")
    print(f"{BOLD}{'='*60}{RESET}\n")

def check_port(port: int) -> bool:
    """Check if a port is already in use."""
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

def main() -> None:
    """Start both backend and frontend servers."""
    print_header("🚀 Starting AtlasIQ Services")
    
    # Get project root
    project_root = Path(__file__).parent
    os.chdir(project_root)
    
    # Check if ports are available
    if check_port(8000):
        print(f"{RED}✗ Port 8000 is already in use!{RESET}")
        print(f"{YELLOW}  Stop the existing process or use a different port.{RESET}")
        sys.exit(1)
    
    if check_port(8502):
        print(f"{RED}✗ Port 8502 is already in use!{RESET}")
        print(f"{YELLOW}  Stop the existing process or use a different port.{RESET}")
        sys.exit(1)
    
    # Get Python executable from virtual environment
    if sys.platform == "win32":
        python_exe = project_root / ".venv" / "Scripts" / "python.exe"
        uvicorn_exe = project_root / ".venv" / "Scripts" / "uvicorn.exe"
    else:
        python_exe = project_root / ".venv" / "bin" / "python"
        uvicorn_exe = project_root / ".venv" / "bin" / "uvicorn"
    
    if not python_exe.exists():
        print(f"{RED}✗ Virtual environment not found at: {python_exe}{RESET}")
        print(f"{YELLOW}  Run: python -m venv .venv{RESET}")
        sys.exit(1)
    
    # Set environment variables
    env = os.environ.copy()
    env["ATLASIQ_LOGGING__LEVEL"] = "INFO"
    env["PYTHONIOENCODING"] = "utf-8"
    
    print(f"{GREEN}✓ Project root: {project_root}{RESET}")
    print(f"{GREEN}✓ Python: {python_exe}{RESET}")
    print(f"{GREEN}✓ Ports checked: 8000 and 8502 available{RESET}\n")
    
    # Start backend
    print(f"{BOLD}Starting Backend (FastAPI)...{RESET}")
    backend_cmd = [
        str(uvicorn_exe),
        "atlasiq.backend.main:app",
        "--host", "0.0.0.0",
        "--port", "8000",
    ]
    
    try:
        backend_process = subprocess.Popen(
            backend_cmd,
            env=env,
            cwd=project_root,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
        )
        print(f"{GREEN}✓ Backend starting (PID: {backend_process.pid})...{RESET}")
    except Exception as e:
        print(f"{RED}✗ Failed to start backend: {e}{RESET}")
        sys.exit(1)
    
    # Wait a moment for backend to start
    time.sleep(2)
    
    # Check if backend is still running
    if backend_process.poll() is not None:
        print(f"{RED}✗ Backend exited unexpectedly!{RESET}")
        sys.exit(1)
    
    # Start frontend
    print(f"\n{BOLD}Starting Frontend (HTTP Server)...{RESET}")
    frontend_cmd = [
        str(python_exe),
        "-m", "atlasiq.frontend.serve"
    ]
    
    try:
        frontend_process = subprocess.Popen(
            frontend_cmd,
            cwd=project_root,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
        )
        print(f"{GREEN}✓ Frontend starting (PID: {frontend_process.pid})...{RESET}")
    except Exception as e:
        print(f"{RED}✗ Failed to start frontend: {e}{RESET}")
        backend_process.terminate()
        sys.exit(1)
    
    # Wait for services to initialize
    time.sleep(3)
    
    # Check if both are still running
    if backend_process.poll() is not None:
        print(f"{RED}✗ Backend exited unexpectedly!{RESET}")
        frontend_process.terminate()
        sys.exit(1)
    
    if frontend_process.poll() is not None:
        print(f"{RED}✗ Frontend exited unexpectedly!{RESET}")
        backend_process.terminate()
        sys.exit(1)
    
    # Success!
    print_header("✅ AtlasIQ is Ready!")
    print(f"{BOLD}{GREEN}Frontend:{RESET}  http://localhost:8502")
    print(f"{BOLD}{GREEN}Backend:{RESET}   http://localhost:8000")
    print(f"{BOLD}{GREEN}API Docs:{RESET}  http://localhost:8000/docs")
    print(f"\n{YELLOW}Press Ctrl+C to stop both services{RESET}\n")
    
    # Wait for Ctrl+C
    try:
        while True:
            time.sleep(1)
            # Check if processes are still alive
            if backend_process.poll() is not None:
                print(f"\n{RED}✗ Backend stopped unexpectedly!{RESET}")
                frontend_process.terminate()
                sys.exit(1)
            if frontend_process.poll() is not None:
                print(f"\n{RED}✗ Frontend stopped unexpectedly!{RESET}")
                backend_process.terminate()
                sys.exit(1)
    except KeyboardInterrupt:
        print(f"\n\n{YELLOW}Shutting down services...{RESET}")
        backend_process.terminate()
        frontend_process.terminate()
        
        # Wait for graceful shutdown
        backend_process.wait(timeout=5)
        frontend_process.wait(timeout=5)
        
        print(f"{GREEN}✓ Services stopped{RESET}")
        print(f"{GREEN}✓ AtlasIQ shutdown complete{RESET}\n")

if __name__ == "__main__":
    main()

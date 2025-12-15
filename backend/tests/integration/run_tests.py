"""
Test runner for integration tests using pytest
"""
import sys
import os
import subprocess


def pick_python():
    """Find Python executable with pytest installed"""
    python_paths = [
        "E:/Python/python.exe",  # From .bazelrc
        os.environ.get("PYTHON_PATH"),
        sys.executable,
        "python",
        "python3",
    ]
    
    for path in python_paths:
        if not path:
            continue
        try:
            # Check Python is available
            subprocess.run(
                [path, "--version"],
                capture_output=True,
                check=True,
                timeout=2
            )
            # Check pytest is installed
            subprocess.run(
                [path, "-c", "import pytest; print(pytest.__version__)"],
                capture_output=True,
                check=True,
                timeout=2
            )
            return path
        except Exception:
            continue
    return None


if __name__ == "__main__":
    # Get the directory containing this script
    test_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Find Python with pytest
    python_exe = pick_python()
    if not python_exe:
        print("ERROR: Could not find Python with pytest installed")
        sys.exit(1)
    
    # Calculate repo root (where backend package is located)
    # In Bazel runfiles: runfiles/_main/backend/tests/integration
    # We need _main (workspace root) so that "from backend.xxx import ..." works
    current = test_dir
    repo_root = None
    
    # Try to find _main directory (Bazel runfiles root)
    # Path structure: .../_main/backend/tests/integration
    for _ in range(6):
        basename = os.path.basename(current)
        if basename == "_main":
            repo_root = current
            break
        parent = os.path.dirname(current)
        if parent == current:
            break
        current = parent
    
    # Fallback: calculate from test_dir
    # backend/tests/integration -> backend -> repo root (project root)
    if not repo_root:
        # Go up from integration -> tests -> backend -> project root
        repo_root = os.path.abspath(os.path.join(test_dir, "..", "..", ".."))
        # But if that doesn't contain backend, try one less level
        if not os.path.exists(os.path.join(repo_root, "backend", "__init__.py")):
            repo_root = os.path.abspath(os.path.join(test_dir, "..", ".."))
    
    # Set PYTHONPATH to include repo root (where backend package is)
    # This ensures "from backend.xxx import ..." works, including backend.utils
    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH", "")
    
    # Ensure repo_root is in PYTHONPATH (prepend to have priority)
    if existing_pythonpath:
        # Avoid duplicates
        paths = [repo_root]
        for path in existing_pythonpath.split(os.pathsep):
            if path and path != repo_root:
                paths.append(path)
        env["PYTHONPATH"] = os.pathsep.join(paths)
    else:
        env["PYTHONPATH"] = repo_root
    
    # Set UTF-8 encoding for Windows console to handle emoji in print statements
    env["PYTHONIOENCODING"] = "utf-8"
    
    # Debug: print PYTHONPATH for troubleshooting
    if os.environ.get("DEBUG_PYTHONPATH"):
        print(f"[run_tests] test_dir: {test_dir}")
        print(f"[run_tests] repo_root: {repo_root}")
        backend_init = os.path.join(repo_root, "backend", "__init__.py")
        utils_init = os.path.join(repo_root, "backend", "utils", "__init__.py")
        print(f"[run_tests] backend/__init__.py exists: {os.path.exists(backend_init)}")
        print(f"[run_tests] backend/utils/__init__.py exists: {os.path.exists(utils_init)}")
        print(f"[run_tests] PYTHONPATH: {env['PYTHONPATH']}")
    
    # Build pytest command with support for extra arguments
    cmd = [
        python_exe, "-m", "pytest",
        test_dir,
        "-v",
        "-s",  # Show print statements
        "--tb=short",
    ] + sys.argv[1:]  # Allow passing additional pytest arguments
    
    sys.exit(subprocess.run(cmd, env=env).returncode)


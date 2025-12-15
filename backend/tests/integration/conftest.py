"""
Integration test fixtures for Bazel
Handles docker compose lifecycle and environment setup
"""
import os
import sys
import time
import subprocess
import pytest
import importlib
import shutil


def _get_runfiles_path(filename):
    """
    Resolve path to a file in Bazel runfiles environment.
    
    In Bazel, test files are in a runfiles directory structure.
    This function tries to find the file in the runfiles tree.
    """
    # Try runfiles path first (Bazel environment)
    # Bazel creates a runfiles directory with _main/ prefix
    runfiles_dir = os.environ.get("RUNFILES_DIR")
    if runfiles_dir:
        # Try _main/ prefix (main workspace)
        path = os.path.join(runfiles_dir, "_main", filename)
        if os.path.exists(path):
            return path
        # Try without _main/ prefix
        path = os.path.join(runfiles_dir, filename)
        if os.path.exists(path):
            return path
    
    # Try MANIFEST file location (Bazel runfiles manifest)
    # Bazel also creates a .runfiles directory next to the binary
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Look for .runfiles directory in parent directories
    current = script_dir
    for _ in range(5):  # Search up to 5 levels
        runfiles_manifest = os.path.join(current, filename + ".runfiles", "_main", filename)
        if os.path.exists(runfiles_manifest):
            return runfiles_manifest
        runfiles_manifest = os.path.join(current, filename + ".runfiles", filename)
        if os.path.exists(runfiles_manifest):
            return runfiles_manifest
        current = os.path.dirname(current)
        if not current or current == os.path.dirname(current):
            break
    
    # Try current directory (local development)
    cwd_path = os.path.join(os.getcwd(), filename)
    if os.path.exists(cwd_path):
        return cwd_path
    
    # Try project root (3 levels up from backend/tests/integration)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(script_dir)))
    root_path = os.path.join(project_root, filename)
    if os.path.exists(root_path):
        return root_path
    
    return None


def _compose_cmd():
    """Detect available docker compose command"""
    import shutil
    
    # Try common Docker Desktop paths on Windows first (most reliable in Bazel)
    docker_paths = [
        "C:\\Program Files\\Docker\\Docker\\resources\\bin\\docker.exe",
        "C:\\Program Files\\Docker\\Docker\\resources\\com.docker.cli\\docker.exe",
    ]
    
    # Also try to find docker in PATH
    docker_exe_path = shutil.which("docker")
    if docker_exe_path:
        docker_paths.insert(0, docker_exe_path)
    
    for docker_exe in docker_paths:
        if docker_exe and os.path.exists(docker_exe):
            # Try "docker compose" (newer syntax, Docker Desktop v2+)
            try:
                result = subprocess.run(
                    [docker_exe, "compose", "version"],
                    check=True,
                    capture_output=True,
                    timeout=10,
                    text=True
                )
                return [docker_exe, "compose"]
            except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired) as e:
                # Try "docker-compose" (older syntax)
                docker_compose_exe = shutil.which("docker-compose")
                if docker_compose_exe and os.path.exists(docker_compose_exe):
                    try:
                        result = subprocess.run(
                            [docker_compose_exe, "version"],
                            check=True,
                            capture_output=True,
                            timeout=10,
                            text=True
                        )
                        return [docker_compose_exe]
                    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
                        continue
                continue
    
    raise RuntimeError(
        "Need `docker compose` or `docker-compose` installed. "
        "Docker Desktop should be running. "
        f"Checked paths: {docker_paths}"
    )


@pytest.fixture(scope="session", autouse=True)
def local_stack():
    """
    Start docker compose stack before tests, stop after.
    
    This fixture is session-scoped and autouse=True, so it runs once
    for all tests in the session.
    """
    try:
        compose = _compose_cmd()
        sys.stderr.write(f"[conftest] Found docker compose command: {compose}\n")
        sys.stderr.flush()
    except RuntimeError as e:
        skip_reason = f"Docker compose not available: {e}"
        sys.stderr.write(f"[conftest] SKIP: {skip_reason}\n")
        sys.stderr.flush()
        pytest.skip(skip_reason)
    
    # Resolve docker-compose.test.yml path (works in Bazel runfiles)
    compose_file = _get_runfiles_path("docker-compose.test.yml")
    sys.stderr.write(f"[conftest] Trying runfiles path: {compose_file}\n")
    sys.stderr.flush()
    
    if not compose_file or not os.path.exists(compose_file):
        # Fallback to current directory
        compose_file = os.path.join(os.getcwd(), "docker-compose.test.yml")
        sys.stderr.write(f"[conftest] Trying current directory: {compose_file} (exists: {os.path.exists(compose_file)})\n")
        sys.stderr.flush()
        if not os.path.exists(compose_file):
            # Try project root (3 levels up)
            script_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(script_dir)))
            compose_file = os.path.join(project_root, "docker-compose.test.yml")
            sys.stderr.write(f"[conftest] Trying project root: {compose_file} (exists: {os.path.exists(compose_file)})\n")
            sys.stderr.flush()
            if not os.path.exists(compose_file):
                skip_reason = f"docker-compose.test.yml not found. Checked multiple locations."
                sys.stderr.write(f"[conftest] SKIP: {skip_reason}\n")
                sys.stderr.flush()
                pytest.skip(skip_reason)
    
    sys.stderr.write(f"[conftest] Using docker-compose file: {compose_file}\n")
    sys.stderr.flush()
    
    # Start services
    sys.stderr.write(f"[conftest] Starting docker compose with file: {compose_file}\n")
    sys.stderr.write(f"[conftest] Docker compose command: {' '.join(compose)}\n")
    sys.stderr.flush()
    try:
        result = subprocess.run(
            compose + ["-f", compose_file, "up", "-d"],
            check=True,
            capture_output=True,
            text=True,
            timeout=60
        )
        sys.stderr.write("[conftest] Docker compose started successfully\n")
        if result.stdout:
            sys.stderr.write(f"[conftest] stdout: {result.stdout}\n")
        if result.stderr:
            sys.stderr.write(f"[conftest] stderr: {result.stderr}\n")
        sys.stderr.flush()
    except subprocess.CalledProcessError as e:
        error_msg = f"Failed to start docker compose: {e}"
        sys.stderr.write(f"[conftest] ERROR: {error_msg}\n")
        if e.stdout:
            sys.stderr.write(f"[conftest] stdout: {e.stdout}\n")
        if e.stderr:
            sys.stderr.write(f"[conftest] stderr: {e.stderr}\n")
        sys.stderr.flush()
        pytest.skip(error_msg)
    except FileNotFoundError as e:
        error_msg = f"docker command not found. Is Docker installed? {e}"
        sys.stderr.write(f"[conftest] ERROR: {error_msg}\n")
        sys.stderr.flush()
        pytest.skip(error_msg)
    except subprocess.TimeoutExpired as e:
        error_msg = f"Docker compose start timed out: {e}"
        sys.stderr.write(f"[conftest] ERROR: {error_msg}\n")
        sys.stderr.flush()
        pytest.skip(error_msg)
    
    # Wait for services to be ready
    sys.stderr.write("[conftest] Waiting for services to be ready...\n")
    sys.stderr.flush()
    time.sleep(5)
    
    yield
    
    # Cleanup: stop and remove volumes
    sys.stderr.write("[conftest] Stopping docker compose...\n")
    sys.stderr.flush()
    try:
        subprocess.run(
            compose + ["-f", compose_file, "down", "-v"],
            check=False,
            capture_output=True,
            timeout=30
        )
    except Exception as e:
        sys.stderr.write(f"[conftest] Warning: Failed to stop docker compose: {e}\n")
        sys.stderr.flush()


@pytest.fixture(autouse=True)
def test_env(monkeypatch):
    """
    Set test environment variables (must be before importing backend modules)
    
    This fixture is autouse=True, so it runs for every test.
    """
    # Critical: Set environment variables before importing backend modules
    # Note: We don't modify sys.stdout/sys.stderr here because it can cause "I/O operation on closed file" errors
    # Emoji encoding issues will be handled by pytest's error handling or ignored
    
    # Generate a valid JWT token for PostgREST
    # PostgREST JWT_SECRET is "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa" (32 bytes)
    # JWT format: header.payload.signature
    import base64
    import json
    import hmac
    import hashlib
    
    jwt_secret = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    
    # Create JWT header
    header = {"alg": "HS256", "typ": "JWT"}
    header_b64 = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip("=")
    
    # Create JWT payload with postgres role (matches PGRST_DB_ANON_ROLE in docker-compose)
    # In test environment, we use postgres role which has full access
    payload = {
        "role": "postgres",  # Matches PGRST_DB_ANON_ROLE in docker-compose.test.yml
        "iss": "postgrest",
        "iat": int(time.time()),
        "exp": int(time.time()) + 3600,  # 1 hour expiry
    }
    payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    
    # Create signature
    message = f"{header_b64}.{payload_b64}"
    signature = hmac.new(
        jwt_secret.encode(),
        message.encode(),
        hashlib.sha256
    ).digest()
    signature_b64 = base64.urlsafe_b64encode(signature).decode().rstrip("=")
    
    # Full JWT token
    service_role_jwt = f"{header_b64}.{payload_b64}.{signature_b64}"
    
    # Also create anon key (same format but with role=postgres for test env)
    payload_anon = payload.copy()
    payload_anon["role"] = "postgres"  # Use postgres for test environment
    payload_anon_b64 = base64.urlsafe_b64encode(json.dumps(payload_anon).encode()).decode().rstrip("=")
    message_anon = f"{header_b64}.{payload_anon_b64}"
    signature_anon = hmac.new(
        jwt_secret.encode(),
        message_anon.encode(),
        hashlib.sha256
    ).digest()
    signature_anon_b64 = base64.urlsafe_b64encode(signature_anon).decode().rstrip("=")
    anon_jwt = f"{header_b64}.{payload_anon_b64}.{signature_anon_b64}"
    
    monkeypatch.setenv("SUPABASE_URL", "http://localhost:54321")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", service_role_jwt)
    monkeypatch.setenv("SUPABASE_ANON_KEY", anon_jwt)
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_mock_key")
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_test_mock_secret")
    monkeypatch.setenv("TEST_MODE", "true")
    
    # Reload modules to use new environment variables
    # Because db_supabase.py creates client at module level
    modules_to_reload = [
        "backend.db_supabase",
        "backend.payment_stripe",
    ]
    
    for module_name in modules_to_reload:
        if module_name in sys.modules:
            importlib.reload(sys.modules[module_name])
            print(f"Reloaded {module_name} with test environment")


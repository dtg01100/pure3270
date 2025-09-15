import os
from pathlib import Path

def load_dotenv(path=None, **kwargs):
    """
    Minimal load_dotenv shim for tests.
    If a .env file exists at the given path (or ./ .env if not),
    parse simple KEY=VALUE lines and set environment variables.
    This keeps tests working without adding external dependencies.
    """
    try:
        env_path = Path(path) if path else Path(".env")
        if not env_path.exists():
            return False
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip().strip('"').strip("'")
                os.environ.setdefault(k, v)
        return True
    except Exception:
        return False
"""Read ORS credentials only from the process environment."""
import os


def require_ors_api_key():
    key = os.environ.get("ORS_API_KEY", "").strip()
    if not key:
        raise RuntimeError("Set ORS_API_KEY in your environment before running this generator.")
    return key

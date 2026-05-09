"""Command classification, execution, and approval flow."""
import re
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path

import redis.asyncio as aioredis

from config import settings

# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------

_SAFE_PATTERNS = [
    r"^(ls|pwd|cat|echo|touch|mkdir -p)\b",
    r"^npm (install|ci|run (dev|build|preview|lint|format|check))\b",
    r"^npx astro\b",
    r"^node\b",
]

_BLOCKED_PATTERNS = [
    r"\bsudo\b",
    r"\.\./",                  # path traversal
    r"(>|>>)\s*\.env\b",       # writing to .env
    r"\b(curl|wget)\b.*(\||\`|;)",  # pipe to shell
    r"\beval\b",
    r"\b(systemctl|service|crontab)\b",
]

_APPROVAL_PATTERNS = [
    r"^(rm|rmdir)\b",
    r"\brm\s+-",
    r"^mv\b",
    r"^git (push|reset|clean|checkout)\b",
    r"^npm install\s+\S",       # install a specific package
    r"^npx (?!astro)\S",        # npx with non-astro command
    r"changes to \.env",
    r"^(deploy|publish)\b",
]


def classify(command: str) -> str:
    """Return 'safe', 'approval_required', or 'blocked'."""
    cmd = command.strip()
    for pat in _BLOCKED_PATTERNS:
        if re.search(pat, cmd, re.IGNORECASE):
            return "blocked"
    for pat in _APPROVAL_PATTERNS:
        if re.search(pat, cmd, re.IGNORECASE):
            return "approval_required"
    for pat in _SAFE_PATTERNS:
        if re.search(pat, cmd, re.IGNORECASE):
            return "safe"
    # Unknown command: require approval
    return "approval_required"


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------

def run_subprocess(command: str, cwd: str, timeout: int = 300) -> tuple[str, str, int]:
    """Run command synchronously. Returns (stdout, stderr, exit_code)."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.stdout, result.stderr, result.returncode
    except subprocess.TimeoutExpired:
        return "", "Command timed out", 1
    except Exception as exc:
        return "", str(exc), 1


# ---------------------------------------------------------------------------
# Approval wait (async, uses Redis BRPOP)
# ---------------------------------------------------------------------------

SIGNAL_KEY_PREFIX = "cmd:signal:"


async def wait_for_approval(command_id: str, timeout: int = 300) -> str:
    """Block until user approves/rejects. Returns 'approved' or 'rejected'/'timeout'."""
    r = aioredis.from_url(settings.redis_url, decode_responses=True)
    try:
        result = await r.brpop(f"{SIGNAL_KEY_PREFIX}{command_id}", timeout=timeout)
        if result is None:
            return "timeout"
        _, signal = result
        return signal
    finally:
        await r.aclose()


async def send_approval_signal(command_id: str, signal: str) -> None:
    """Called by approve/reject API endpoints to unblock waiting agent."""
    r = aioredis.from_url(settings.redis_url, decode_responses=True)
    try:
        await r.rpush(f"{SIGNAL_KEY_PREFIX}{command_id}", signal)
    finally:
        await r.aclose()


# ---------------------------------------------------------------------------
# Safe path validation
# ---------------------------------------------------------------------------

def safe_path(workspace_root: str, relative_path: str) -> Path:
    """Resolve path and raise if it escapes workspace_root."""
    root = Path(workspace_root).resolve()
    target = (root / relative_path.lstrip("/")).resolve()
    if not str(target).startswith(str(root)):
        raise ValueError(f"Path traversal blocked: {relative_path}")
    return target

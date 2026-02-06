from __future__ import annotations

from pathlib import Path
import subprocess


def apply_migrations(base_dir: Path, dsn: str | None = None) -> None:
    command = ["pgmigrate", "-t", "latest", "migrate", "-d", str(base_dir)]
    if dsn:
        command.extend(["-c", dsn])
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        stderr = result.stderr.strip() or "pgmigrate failed without stderr"
        raise RuntimeError(stderr)

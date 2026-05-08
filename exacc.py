#!/usr/bin/env python3
"""Convenience entry point for running the app from this checkout."""

import os
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parent
VENV_PYTHON = ROOT / ".venv" / "bin" / "python"

if VENV_PYTHON.exists() and Path(sys.executable).resolve() != VENV_PYTHON.resolve():
    os.execv(str(VENV_PYTHON), [str(VENV_PYTHON), str(Path(__file__).resolve()), *sys.argv[1:]])

sys.path.insert(0, str(ROOT / "src"))

from exacc_app.cli import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())

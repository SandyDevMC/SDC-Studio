#!/usr/bin/env python3
"""Точка входа SDC-Studio."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from sdc_studio.app import main  # noqa: E402

if __name__ == "__main__":
    main()
